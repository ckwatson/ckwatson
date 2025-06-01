run:
    uv run gunicorn web.main:app --worker-class gevent --bind 127.0.0.1:8000 --reload --timeout 6000

test:
    PYTHONPATH=. uv run pytest --cov=web/ --cov=kernel/engine/
    uv run coverage-badge -f -o coverage.svg
