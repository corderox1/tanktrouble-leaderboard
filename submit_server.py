from flask import Flask, request, jsonify, session, redirect, url_for
import os
import html

app = Flask(__name__)

app.secret_key = os.environ.get("ADMIN_PASSWORD", "temporary-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

pending_requests = []


def get_leaderboard_players():
    """Read usernames from players.txt."""
    players = set()

    try:
        with open("players.txt", "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if line:
                    players.add(line.lower())

    except FileNotFoundError:
        pass

    return players


@app.route("/")
def home():
    return "TankTrouble Leaderboard backend is running!"


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "Invalid submission."
        }), 400

    username = data.get("username", "").strip()

    if not username:
        return jsonify({
            "success": False,
            "message": "Username is required."
        }), 400

    # Check if already on the leaderboard
    leaderboard_players = get_leaderboard_players()

    if username.lower() in leaderboard_players:
        return jsonify({
            "success": False,
            "message": "This player is already on the leaderboard."
        }), 400

    # Check if already waiting for approval
    for player in pending_requests:
        if player["username"].lower() == username.lower():
            return jsonify({
                "success": False,
                "message": "This username is already waiting for approval."
            }), 400

    # Add to pending submissions
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
    html_page = """
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
                padding: 20px;
                margin: 15px 0;
                border-radius: 8px;
            }

            .username {
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 12px;
            }

            button {
                border: none;
                padding: 10px 18px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 15px;
                margin-right: 8px;
            }

            .verify {
                background: #20a040;
                color: white;
            }

            .reject {
                background: #c62828;
                color: white;
            }

            button:hover {
                opacity: 0.8;
            }
        </style>
    </head>

    <body>

        <h1>TankTrouble Admin Panel</h1>

        <h2>Pending Submissions</h2>
    """

    if not pending_requests:
        html_page += "<p>No pending submissions.</p>"

    for index, player in enumerate(pending_requests):

        safe_username = html.escape(player["username"])

        html_page += f"""
        <div class="request">

            <div class="username">
                {safe_username}
            </div>

            <p>Waiting for approval.</p>

            <form method="POST" action="/verify" style="display:inline;">
                <input type="hidden" name="index" value="{index}">
                <button class="verify" type="submit">
                    ✅ Verify
                </button>
            </form>

            <form method="POST" action="/reject" style="display:inline;">
                <input type="hidden" name="index" value="{index}">
                <button class="reject" type="submit">
                    ❌ Reject
                </button>
            </form>

        </div>
        """

    html_page += """
    </body>
    </html>
    """

    return html_page


@app.route("/verify", methods=["POST"])
def verify():

    if not session.get("admin_logged_in"):
        return "Unauthorized", 401

    try:
        index = int(request.form.get("index"))
    except:
        return "Invalid request", 400

    if index < 0 or index >= len(pending_requests):
        return "Request not found", 404

    player = pending_requests.pop(index)

    return redirect(url_for("admin"))


@app.route("/reject", methods=["POST"])
def reject():

    if not session.get("admin_logged_in"):
        return "Unauthorized", 401

    try:
        index = int(request.form.get("index"))
    except:
        return "Invalid request", 400

    if index < 0 or index >= len(pending_requests):
        return "Request not found", 404

    player = pending_requests.pop(index)

    return redirect(url_for("admin"))


@app.route("/pending")
def pending():

    if not session.get("admin_logged_in"):
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401

    return jsonify(pending_requests)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
