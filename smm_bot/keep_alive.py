import threading
import socket
import os
import time
import psutil
from flask import Flask, jsonify
from loguru import logger

app = Flask(__name__)
_start_time = time.time()


def _get_memory_mb() -> float:
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


@app.route("/")
def home():
    uptime_s = int(time.time() - _start_time)
    h, rem = divmod(uptime_s, 3600)
    m, s = divmod(rem, 60)
    return (
        f"<html><head><title>Sultan SMM Bot</title>"
        f"<meta http-equiv='refresh' content='30'></head><body>"
        f"<h1>🏛️ SULTAN SMM BOT — ACTIVE ✅</h1>"
        f"<p><b>Status:</b> Online</p>"
        f"<p><b>Uptime:</b> {h}h {m}m {s}s</p>"
        f"<p><b>RAM:</b> {_get_memory_mb():.1f} MB</p>"
        f"<p><i>Ping /health for machine-readable status.</i></p>"
        f"</body></html>"
    )


@app.route("/health")
def health():
    uptime_s = int(time.time() - _start_time)
    return jsonify({
        "status": "ok",
        "bot": "Sultan SMM Master System",
        "uptime_seconds": uptime_s,
        "ram_mb": round(_get_memory_mb(), 1),
    }), 200


@app.route("/ping")
def ping():
    return "Bot is Active", 200


def _find_free_port(preferred: int) -> int:
    for port in [preferred, 5001, 5002, 5003, 6001, 6800, 9000]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return preferred


def _run_server(port: int):
    try:
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )
    except Exception as e:
        logger.error(f"Keep-alive server error: {e}")


def keep_alive():
    # Use BOT_KEEP_ALIVE_PORT if set, else try 6000 (Replit proxy-supported port)
    preferred = int(os.environ.get("BOT_KEEP_ALIVE_PORT", os.environ.get("PORT", 6000)))
    port = _find_free_port(preferred)
    logger.info(f"🌐 Keep-alive server starting on port {port}")
    t = threading.Thread(target=_run_server, args=(port,), daemon=True)
    t.start()
    return port
