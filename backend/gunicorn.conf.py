"""Production defaults for the TENeT Gunicorn server."""
import os


def _positive_int(name, default):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


port = _positive_int("PORT", _positive_int("FLASK_PORT", 5001))
bind = f"0.0.0.0:{port}"
workers = _positive_int("WEB_CONCURRENCY", 2)
threads = _positive_int("GUNICORN_THREADS", 4)
timeout = _positive_int("GUNICORN_TIMEOUT", 60)
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
