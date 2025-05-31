#!/usr/local/bin/python3.5

import datetime as dt
import hashlib
import json
import logging
import os
import re
import traceback
from pprint import pprint

import colorlog
import humanize
import jsonschema
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sse import sse
from jsonschema.exceptions import ValidationError

from web.redis_utils import RedisJobStream, redis_available
from web.run_simulation import simulate_experiments_and_plot
from web.save_a_puzzle import save_a_puzzle

np.seterr(all="warn")

from pathlib import Path


def all_files_in(mypath, end=""):
    return [
        p.stem
        for p in Path(mypath).iterdir()
        if p.is_file() and not p.name.startswith(".") and p.name.endswith(end)
    ]


# Initialize logger:
rootLogger = logging.getLogger()  # access the root logger
rootLogger.removeHandler(logging.getLogger().handlers[0])
# create a handler for printing messages onto the console
handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)s%(reset)s:%(bold)s%(name)s%(reset)s:%(message)s"
    )
)
# attach the to-console handler to the root logger
rootLogger.addHandler(handler)


AUTH_CODE = os.environ.get("CKWATSON_PUZZLE_AUTH_CODE", "123")


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    # redis configuation, for SSE support:
    app.config["REDIS_URL"] = os.environ.get("REDIS_URL") or "redis://localhost"
    is_redis_available = redis_available(app.config["REDIS_URL"])
    # Limiter setup
    if is_redis_available:
        limiter = Limiter(
            get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=app.config["REDIS_URL"],
        )
    else:
        limiter = Limiter(
            get_remote_address, app=app, default_limits=["200 per day", "50 per hour"]
        )
    # Flask-compress is a Flask extension that provides gzip compression for the web app.
    # It is used to reduce the size of the response data sent from the server to the client,
    # which is helpful for us, because we are going to send tons of SVGs per job.
    # https://github.com/colour-science/flask-compress
    Compress(app)
    # Flask-Caching setup (use Redis if available, else simple cache)
    if is_redis_available:
        cache_config = {
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_URL": app.config["REDIS_URL"],
            "CACHE_DEFAULT_TIMEOUT": 3600,
        }
    else:
        cache_config = {"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": 3600}
    cache = Cache(app, config=cache_config)
    app.register_blueprint(sse, url_prefix="/stream")
    return app, is_redis_available, limiter, cache


# Create the Flask app and check Redis availability
app, is_redis_available, limiter, cache = create_app()

# load JSON schema for Puz file for validation:
with open("puzzles/schema.js") as f:
    schema = f.read()
schema = json.loads(schema)


def make_plot_cache_key(data):
    key_data = json.dumps(
        {
            "puzzle": data["puzzle"],
            "reactions": data["reactions"],
            "temperature": data["temperature"],
            "conditions": data["conditions"],
        },
        sort_keys=True,
    )
    return "plot_result:" + hashlib.sha256(key_data.encode()).hexdigest()


@app.route("/plot", methods=["POST", "OPTIONS"])
def handle_plot_request():
    start_time = dt.datetime.now()
    data = request.get_json()
    job_logger = logging.getLogger(data["jobID"])
    logger = job_logger.getChild("handle_plot_request")
    cache_key = make_plot_cache_key(data)
    cached_result = cache.get(cache_key)
    if cached_result:
        # Attach the jobID to the cached result for this request
        logger.info(f"Cache hit for jobID {data['jobID']} with cache key {cache_key}.")
        return jsonify({**cached_result, "jobID": data["jobID"]})

    logging_handler = None
    if is_redis_available:
        logger.info(
            f"Redis is available. Will stream logs to frontend via Redis channel {data['jobID']}."
        )
        logging_handler = logging.StreamHandler(stream=RedisJobStream(data["jobID"]))
        job_logger.addHandler(logging_handler)

    try:
        temperature = data["temperature"]
        with open(f"puzzles/{data['puzzle']}.puz") as json_file:
            puzzle_definition = json.load(json_file)
            logger.info("    Successfully loaded Puzzle Data from file!")
        plot_combined, plot_individual, score = simulate_experiments_and_plot(
            data, puzzle_definition, temperature, diag=False
        )
        logger.info(
            f"Executed for {humanize.precisedelta(dt.datetime.now() - start_time)}."
        )
        result = {
            "status": "success",
            "plot_individual": plot_individual,
            "plot_combined": plot_combined,
            "temperature": temperature,
            "score": score,
        }
        cache.set(
            cache_key,
            result,
        )
        result["jobID"] = data["jobID"]
        return jsonify(result)
    except Exception:
        logger.error(traceback.format_exc())
        logger.info(
            f"Executed for {humanize.precisedelta(dt.datetime.now() - start_time)}."
        )
        return jsonify(jobID=data["jobID"], status="error")


@app.route("/save", methods=["POST", "OPTIONS"])
@limiter.limit("5 per minute")
def handle_save_request():
    data = request.get_json()  # receive JSON data
    print("Data received:")
    pprint(data)
    # Validate puzzleName for safe filename (alphanumeric, dash, underscore, space)
    puzzle_name = data.get("puzzleName", "")
    if not re.match(r"^[\w\- ]+$", puzzle_name):
        return jsonify(
            status="danger",
            message="Invalid puzzle name. Use only letters, numbers, spaces, dashes, and underscores.",
        )
    if data["auth_code"] != AUTH_CODE:
        return jsonify(
            status="danger", message="Authentication failed. Check your password."
        )
    # Else, validate with jsonschema:
    existing_puzzles = all_files_in("puzzles")
    if puzzle_name in existing_puzzles:
        return jsonify(
            status="danger", message="Puzzle already exists. Try another name."
        )
    try:
        jsonschema.validate(data, schema)
    except ValidationError as e:
        return jsonify(status="danger", message=e.message)
    else:
        return save_a_puzzle(data)


@app.route("/create")
def serve_page_create():
    ip = request.remote_addr.replace(".", "_") if request.remote_addr else "unknown_ip"
    return render_template("create.html", ip=ip)


@app.route("/play/<puzzle_name>")
def serve_page_play(puzzle_name):
    with open(f"puzzles/{puzzle_name}.puz") as json_file:
        puzzle_data = json_file.read()
    return render_template(
        "play.html",
        puzzle_name=puzzle_name,
        puzzle_data=puzzle_data,
        REDIS_OK=is_redis_available,  # Pass Redis status to template
    )


@app.route("/")
def serve_page_index():
    puzzle_list = all_files_in("puzzles", end=".puz")
    return render_template("index.html", puzzle_list=puzzle_list)
