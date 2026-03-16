"""Flask web UI for withings-sync."""
import json
import os
import sys
import subprocess

import requests as http_requests
from dotenv import dotenv_values, set_key
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
WITHINGS_CONFIG_FILE = os.path.expanduser("~/.withings_user.json")
WITHINGS_TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
WITHINGS_AUTH_URL = "https://account.withings.com/oauth2_user/authorize2"


def get_withings_app_config():
    try:
        import importlib_resources
        ref = importlib_resources.files("withings_sync") / "config/withings_app.json"
        with ref.open() as f:
            return json.load(f)
    except Exception:
        path = os.path.join(BASE_DIR, "withings_sync", "config", "withings_app.json")
        with open(path) as f:
            return json.load(f)


WITHINGS_APP = get_withings_app_config()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    env = dotenv_values(ENV_FILE) if os.path.exists(ENV_FILE) else {}
    garmin_configured = bool(env.get("GARMIN_USERNAME") and env.get("GARMIN_PASSWORD"))
    withings_authed = os.path.exists(WITHINGS_CONFIG_FILE)

    last_sync = None
    if withings_authed:
        try:
            with open(WITHINGS_CONFIG_FILE) as f:
                data = json.load(f)
            last_sync = data.get("last_sync")
        except Exception:
            pass

    return jsonify(
        {
            "garmin_configured": garmin_configured,
            "garmin_username": env.get("GARMIN_USERNAME", ""),
            "withings_authed": withings_authed,
            "last_sync": last_sync,
        }
    )


@app.route("/api/credentials", methods=["POST"])
def save_credentials():
    data = request.json
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400

    if not os.path.exists(ENV_FILE):
        open(ENV_FILE, "w").close()

    set_key(ENV_FILE, "GARMIN_USERNAME", username)
    set_key(ENV_FILE, "GARMIN_PASSWORD", password)
    return jsonify({"success": True})


@app.route("/api/withings/auth-url")
def withings_auth_url():
    url = (
        WITHINGS_AUTH_URL
        + "?response_type=code"
        + "&client_id=" + WITHINGS_APP["client_id"]
        + "&state=OK"
        + "&scope=user.metrics"
        + "&redirect_uri=" + WITHINGS_APP["callback_url"]
    )
    return jsonify({"url": url})


@app.route("/api/withings/exchange", methods=["POST"])
def withings_exchange():
    auth_code = (request.json.get("code") or "").strip()
    if not auth_code:
        return jsonify({"success": False, "error": "Authorization code is required"}), 400

    try:
        params = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": WITHINGS_APP["client_id"],
            "client_secret": WITHINGS_APP["consumer_secret"],
            "code": auth_code,
            "redirect_uri": WITHINGS_APP["callback_url"],
        }
        resp = http_requests.post(WITHINGS_TOKEN_URL, data=params, timeout=15)
        data = resp.json()

        if data.get("status") == 0:
            body = data["body"]
            config = {
                "authentification_code": auth_code,
                "access_token": body["access_token"],
                "refresh_token": body["refresh_token"],
                "userid": str(body["userid"]),
            }
            with open(WITHINGS_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return jsonify({"success": True})
        else:
            error = data.get("error") or f"Withings API error (status {data.get('status')})"
            return jsonify({"success": False, "error": error}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/withings/disconnect", methods=["POST"])
def withings_disconnect():
    if os.path.exists(WITHINGS_CONFIG_FILE):
        os.remove(WITHINGS_CONFIG_FILE)
    return jsonify({"success": True})


@app.route("/api/sync/stream")
def sync_stream():
    env = dotenv_values(ENV_FILE) if os.path.exists(ENV_FILE) else {}
    username = (env.get("GARMIN_USERNAME") or "").strip()
    password = (env.get("GARMIN_PASSWORD") or "").strip()
    from_date = request.args.get("fromdate", "")
    to_date = request.args.get("todate", "")

    def generate():
        if not username or not password:
            yield _event("error", "Garmin credentials not configured")
            return

        if not os.path.exists(WITHINGS_CONFIG_FILE):
            yield _event("error", "Withings not authorized — please connect Withings first")
            return

        cmd = [
            sys.executable, "-u", "-m", "withings_sync.sync",
            "--garmin-username", username,
            "--garmin-password", password,
            "--verbose",
        ]
        if from_date:
            cmd += ["--fromdate", from_date]
        if to_date:
            cmd += ["--todate", to_date]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=BASE_DIR,
            )
            for line in iter(process.stdout.readline, ""):
                msg = line.rstrip()
                if msg:
                    yield _event("log", msg)

            process.wait()
            if process.returncode == 0:
                yield _event("done", "Sync completed successfully", success=True)
            else:
                yield _event("done", f"Sync failed (exit code {process.returncode})", success=False)

        except Exception as e:
            yield _event("error", str(e))

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _event(event_type, message, **extra):
    payload = {"type": event_type, "message": message, **extra}
    return f"data: {json.dumps(payload)}\n\n"


if __name__ == "__main__":
    print("Starting Withings → Garmin Sync UI at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
