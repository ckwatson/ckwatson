#!/usr/local/bin/python3.5
# , redirect, url_for, send_from_directory
# from .crossdomain import crossdomain

import datetime as dt
import json
import logging
import os
import sys
import traceback
from pprint import pprint

import colorlog
import humanize
import jsonschema
import numpy as np
from flask import Flask, jsonify, render_template, request
from flask_compress import Compress
from flask_sse import sse

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


# For Server-Sent-Event support:


class ListStream:
    """One ListStream corresponds to one unique computation job.
    c.f.: http://stackoverflow.com/questions/21341096/redirect-print-to-string-list"""

    def __init__(self, jobID):
        self.jobID = jobID

    def write(self, *args):
        s = ""
        for arg in args:
            s += " " + str(arg)
        with app.app_context():
            try:
                sse.publish({"data": s}, channel=self.jobID)
            except AttributeError:
                sys.__stdout__.write(" * Orphaned Message: " + s)

    def flush(self):
        pass


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


AUTH_CODE = "123"
# ongoingJobs = []

app = Flask(__name__)
# Flask-compress is a Flask extension that provides gzip compression for the web app.
# It is used to reduce the size of the response data sent from the server to the client,
# which is helpful for us, because we are going to send tons of SVGs per job.
# https://github.com/colour-science/flask-compress
Compress(app)

# redis configuation, for SSE support:
# 'os.environ.get("REDIS_URL")' is for Heroku and "redis://localhost" is meant for localhost.
app.config["REDIS_URL"] = os.environ.get("REDIS_URL") or "redis://localhost"
app.register_blueprint(sse, url_prefix="/stream")

# load JSON schema for Puz file for validation:
with open("puzzles/schema.js") as f:
    schema = f.read()
schema = json.loads(schema)


@app.route("/plot", methods=["POST", "OPTIONS"])
def handle_plot_request():
    start_time = dt.datetime.now()  # start timer
    data = request.get_json()  # receive JSON data
    # initialize logger for this particular job:
    # create a log_handler that streams messages to the web UI specifically for this job.
    logging_handler = logging.StreamHandler(stream=ListStream(data["jobID"]))
    job_logger = logging.getLogger(data["jobID"])
    job_logger.addHandler(logging_handler)  # redirect the logs since NOW
    # All functions should have their own logger that is a child of the job_logger.
    logger = job_logger.getChild("handle_plot_request")
    # now the serious part:
    try:
        temperature = data["temperature"]  # just a shorthand

        with open(f"puzzles/{data['puzzle']}.puz") as json_file:
            puzzle_definition = json.load(json_file)
            logger.info("    Successfully loaded Puzzle Data from file!")
        plot_combined, plot_individual, score = simulate_experiments_and_plot(
            data,
            puzzle_definition,
            temperature,
            diag=False,
        )
        logger.info(
            f"Executed for {humanize.precisedelta(dt.datetime.now() - start_time)}."
        )
        return jsonify(
            jobID=data["jobID"],
            status="success",
            plot_individual=plot_individual,
            plot_combined=plot_combined,
            temperature=temperature,
            score=score,
        )  # serving result figure files via "return", so as to save server calls
    except Exception as error:
        # print out last words:
        logger.error(traceback.format_exc())
        logger.info(
            f"Executed for {humanize.precisedelta(dt.datetime.now() - start_time)}."
        )
        return jsonify(jobID=data["jobID"], status="error")


@app.route("/save", methods=["POST", "OPTIONS"])
def handle_save_request():
    data = request.get_json()  # receive JSON data
    print("Data received:")
    pprint(data)
    if not request.remote_addr == "127.0.0.1":
        if not data["auth_code"] == AUTH_CODE:
            return jsonify(
                status="danger", message="Authentication failed. Check your password."
            )
    # Else, validate with jsonschema:
    existing_puzzles = all_files_in("puzzles")
    if data["puzzleName"] in existing_puzzles:
        return jsonify(
            status="danger", message="Puzzle already exists. Try another name."
        )
    try:
        jsonschema.validate(data, schema)
    except jsonschema.exceptions.ValidationError as e:
        return jsonify(status="danger", message=e.message)
    else:
        return save_a_puzzle(data)


@app.route("/create")
def serve_page_create():
    return render_template(
        "main.html", mode="create", ip=request.remote_addr.replace(".", "_")
    )


@app.route("/play/<puzzleName>")
def serve_page_play(puzzleName):
    with open("puzzles/" + puzzleName + ".puz") as json_file:
        puzzleData = json_file.read()
    return render_template(
        "main.html",
        mode="play",
        puzzleName=puzzleName,
        puzzleData=puzzleData,
        ip=request.remote_addr.replace(".", "_"),
    )


@app.route("/")
def serve_page_index():
    puzzleList = all_files_in("puzzles", end=".puz")
    return render_template("index.html", puzzleList=puzzleList)
