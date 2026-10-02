from flask import Flask, request, jsonify, session, redirect, url_for
import os

app = Flask(__name__)

# Use the password from Render as the session secret
app.secret_key = os.environ.get("ADMIN_PASSWORD", "temporary-secret")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

pending_requests = []


@app.route("/")
def home():
    return "TankTrouble Leaderboard backend is running!"


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    username = data.get("username", "").strip()

    if not username:
        return jsonify({
            "success": False,
            "message": "Username is required."
        }), 400

    for player in pending_requests:
        if player["username"].lower() == username.lower():
            return jsonify({
                "success": False,
                "message": "This username is already waiting for approval."
            }), 400

    pending_requests.append({
        "username": username
    })

    return jsonify({
        "success": True,
        "message": "Submission received and is waiting for approval!"
    })


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Login
    if request.method == "POST":
        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        return """
        <h2>Wrong password ❌</h2>
        <a href="/admin">Try again</a>
        """

    # Require login
    if not session.get("admin_logged_in"):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>TankTrouble Admin</title>
        </head>
        <body>
            <h1>TankTrouble Leaderboard Admin</h1>

            <form method="POST">
                <input
                    type="password"
                    name="password"
                    placeholder="Admin password"
                    required
                >
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """

    # Admin panel
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>TankTrouble Admin</title>
        <style>
            body {
                background: #111;
                color: white;
                font-family: Arial, sans-serif;
                padding: 30px;
            }

            h1 {
                color: gold;
            }

            .request {
                background: #222;
                border: 1px solid #444;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
            }
        </style>
    </head>

    <body>
        <h1>TankTrouble Admin Panel</h1>

        <h2>Pending Submissions</h2>
    """

    if not pending_requests:
        html += "<p>No pending submissions.</p>"

    for player in pending_requests:
        html += f"""
        <div class="request">
            <strong>{player["username"]}</strong>
            <p>Waiting for approval.</p>
        </div>
        """

    html += """
    </body>
    </html>
    """

    return html


@app.route("/pending")
def pending():
    # Protect pending requests
    if not session.get("admin_logged_in"):
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    return jsonify(pending_requests)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
