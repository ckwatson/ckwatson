# <img width="20" alt="logo" src="web/static/favicon/favicon-96x96.png" /> CKWatson
[![JavaScript Style Guide](https://img.shields.io/badge/code_style-standard-brightgreen.svg)](https://standardjs.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
![Coverage Status](coverage.svg)
![License](https://img.shields.io/github/license/ckwatson/web_gui)

CKWatson is an educational game about [chemical kinetics][ck]. The game is organized in "puzzles". Each puzzle starts off with a few reactants.
Within a given set of all substances possibly present, the player's goal is to figure out all [elementary reactions][er] involved with the chemical process when the reactants are mixed together.

> Elementary [reactions], my dear Watson!

<img width="1000" alt="image" src="https://github.com/user-attachments/assets/35aef8ab-2a1e-4661-8677-9112d2142b6f" />

[ck]: https://chem.libretexts.org/Bookshelves/General_Chemistry/Map%3A_Chemistry_-_The_Central_Science_(Brown_et_al.)/14%3A_Chemical_Kinetics
[er]: https://chem.libretexts.org/Bookshelves/Physical_and_Theoretical_Chemistry_Textbook_Maps/Supplemental_Modules_(Physical_and_Theoretical_Chemistry)/Kinetics/03%3A_Rate_Laws/3.02%3A_Reaction_Mechanisms/3.2.01%3A_Elementary_Reactions

([live demo](https://ckwatson.onrender.com/))

## Installation

**Binary dependencies.** This project uses [`uv`](https://docs.astral.sh/uv/) as the package manager and [`just`](https://github.com/casey/just) for convenience. Optionally, [Redis](https://redis.io/) enables [server-sent events (SSEs)][sse] and more production-ready rate-limiting & caching. If you don't have them available yet, are on macOS, and have installed [Homebrew](https://brew.sh/), you can install both binaries in one go this this command:

```shell
brew install just uv redis
```

To clone the repository and initialize the virtual environment, run these commands:

```shell
git clone --recurse-submodules https://github.com/ckwatson/ckwatson.git
cd ckwatson
uv sync
```

[sse]: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

## Setup

It's recommended (but not strictly necessary) to start a Redis server first: `redis-server`.

To run CKWatson, just run `just run`. The terminal should say:

```
[INFO] Listening at: http://127.0.0.1:8000 (30996)
```

Start playing by navigating to that URL.


## Deployment

The easiest way to run CKWatson, without even cloning this repo, is to hit this button and deploy to [render.com](http://render.com/):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Where's the [Procfile](https://devcenter.heroku.com/articles/procfile)?** Back in 2016, I used Heroku for deploying CKWatson. When I looked again in mid-2025, but I had the easiest experience with Render (and they have a free tier), so I switched. This means the Procfile has been replaced with the `render.yaml`.

<details>

<summary>You can still self-host CKWatson. Read on.</summary>

### Via Docker

You can either run CKWatson as a single container or with Redis using Docker Compose.

To run CKWatson as a single container:
1. Build the image: `docker build -t ckw .`
2. Start a container: `docker run -p 80:80 --rm --name ckwatson ckw`

To run CKWatson with Redis, simply use `docker-compose up`.

### Via Kubernetes

I will be using [minikube](https://minikube.sigs.k8s.io/) in this walkthrough. I will be using the local Docker Registry as the source of the Kubernetes image.

> **Note:** For production or remote clusters, push your image to a container registry and set `imagePullPolicy: IfNotPresent` or `Always` in the deployment YAML.
> The provided YAMLs now include resource requests/limits and health checks for better stability.

```shell
# Start the cluster:
minikube start
# Register the Docker Registry to minikube -- This is because we will be building the image from the Dockerfile for Kubernetes:
eval $(minikube docker-env)
# Build the Docker image for Kubernetes:
docker build -t ckw .
# Apply the Deployment and Service manifests:
kubectl apply -f ./k8s
# Access the web app:
minikube service web
```

#### Troubleshooting

- If you see `ImagePullBackOff`, ensure you ran `eval $(minikube docker-env)` before building.
- For production, set up resource limits and health checks (already included in the YAMLs).
- For Redis security in production, set a password and update the deployment and app config accordingly.

</details>

## Architecture

Here's the folder structure:

- `kernel` does the chemistry.
- `puzzles` stores definitions of puzzles. Admin can add puzzles to the game using the `create` page.
- `web` powers the web app.


### About the web app

CKWatson follows the [WSGI convention](https://wsgi.readthedocs.io/en/latest/what.html), a Python standard ([PEP-3333](https://peps.python.org/pep-3333/)) for building web servers. We achieve this by using the [Flask framework](https://flask.palletsprojects.com/en/stable/).

Since a plotting job can take a while, we allow users to see status updates in the "messages" view of each job. These messages are streamed as [server-sent events (SSEs)][sse] via the [Flask-SSE](https://flask-sse.readthedocs.io/en/latest/quickstart.html) extension.

Other significant extensions to Flask that CKWatson employs include:

- [Flask-Caching](https://flask-caching.readthedocs.io/en/latest/) for caching computation results.
- [Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/) for rate-limiting. This is more of a security measure than it is a feature.
- [Flask-Compress](https://github.com/shengulong/flask-compress) for gzipping responses. This significantly reduces the bandwidth usage of our job results, which contains many SVG plots.

On the frontend side, CKWatson uses [Bootstrap 5](https://getbootstrap.com/docs/5.3/getting-started/introduction/) for styling.
