FROM ghcr.io/astral-sh/uv:0.7.5-python3.10-bookworm
MAINTAINER tslmy
WORKDIR /app
COPY . .
RUN uv sync --compile-bytecode --no-cache --locked
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1
CMD ["uv", "run", "gunicorn", "run:app", "--worker-class", "gevent", "--bind", "0.0.0.0:80"]
