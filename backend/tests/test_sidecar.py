from app.main import app
from sidecar import parse_args, run_server


def test_sidecar_defaults_to_loopback_port_8000():
    args = parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_sidecar_passes_explicit_host_and_port_to_uvicorn():
    calls = []

    def fake_runner(application, **kwargs):
        calls.append((application, kwargs))

    run_server(["--host", "127.0.0.1", "--port", "8011"], fake_runner)

    assert calls[0][0] is app
    assert calls[0][1] == {
        "host": "127.0.0.1",
        "port": 8011,
        "log_level": "warning",
    }
