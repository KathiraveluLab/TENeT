import importlib.util
from pathlib import Path


CONFIG_PATH = Path(__file__).parents[1] / "gunicorn.conf.py"


def load_config():
    spec = importlib.util.spec_from_file_location("tenet_gunicorn_config", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gunicorn_defaults_are_production_safe(monkeypatch):
    for name in ("PORT", "FLASK_PORT", "WEB_CONCURRENCY", "GUNICORN_THREADS"):
        monkeypatch.delenv(name, raising=False)

    config = load_config()

    assert config.bind == "0.0.0.0:5001"
    assert config.workers == 2
    assert config.threads == 4
    assert config.timeout == 60


def test_invalid_process_counts_fall_back_safely(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-port")
    monkeypatch.delenv("FLASK_PORT", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", "not-a-number")
    monkeypatch.setenv("GUNICORN_THREADS", "0")

    config = load_config()

    assert config.workers == 2
    assert config.threads == 4
    assert config.bind == "0.0.0.0:5001"
