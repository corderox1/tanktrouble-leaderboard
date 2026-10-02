from flask import Flask, request, jsonify, session, redirect, url_for
import os
import html
import requests

app = Flask(__name__)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
app.secret_key = os.environ.get("ADMIN_PASSWORD", "temporary-secret")

pending_requests = []

TANK_TROUBLE_API = "https://tanktrouble.com/ajax/"


def get_player_by_username(username):
    payload = {
        "jsonrpc": "2.0",
        "method": "tanktrouble.getPlayerDetailsByUsername",
        "id": 1,
        "params": [username]
    }

    try:
        response = requests.post(
            TANK_TROUBLE_API,
            json=payload,
            timeout=10
        )

        print("TankTrouble API STATUS:", response.status_code)
        print("TankTrouble API RESPONSE:", response.text)

        data = response.json()

        if not data.get("result"):
            print("TankTrouble API did not return a successful result.")
            return None

        player = data.get("data")

        print("FULL PLAYER DATA:", player)

        return player

    except Exception as e:
        print("TankTrouble API ERROR:", repr(e))
        return None

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

    # Look up username on TankTrouble
    player = get_player_by_username(username)

    if not player:
        return jsonify({
            "success": False,
            "message": "That TankTrouble username could not be found."
        }), 404

    # Get Player ID
    player_id = str(player.get("playerId", ""))

    if not player_id:
        return jsonify({
            "success": False,
            "message": "Could not determine the player's ID."
        }), 500

    # Check if already on leaderboard
    leaderboard_players = get_leaderboard_player_ids()

    if player_id in leaderboard_players:
        return jsonify({
            "success": False,
            "message": "This player is already on the leaderboard."
        }), 400

    # Check if already pending
    for pending in pending_requests:
        if pending["playerId"] == player_id:
            return jsonify({
                "success": False,
                "message": "This player is already waiting for approval."
            }), 400

    # Add to pending list
    pending_requests.append({
        "username": player.get("username", username),
        "playerId": player_id
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
        <!DOCTYPE html>
        <html>
        <body style="background:#111;color:white;font-family:Arial;padding:30px;">
            <h2>Wrong password ❌</h2>
            <a href="/admin" style="color:gold;">Try again</a>
        </body>
        </html>
        """

    # Require login
    if not session.get("admin_logged_in"):

        return """
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

                input {
                    padding: 10px;
                    font-size: 16px;
                }

                button {
                    padding: 10px 18px;
                    font-size: 16px;
                    cursor: pointer;
                }
            </style>
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

                <button type="submit">
                    Login
                </button>

            </form>

        </body>
        </html>
        """

    # Admin panel
    page = """
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
                margin-bottom: 8px;
            }

            .player-id {
                color: #aaa;
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

        page += """
        <p>No pending submissions.</p>
        """

    for index, player in enumerate(pending_requests):

        safe_username = html.escape(player["username"])
        safe_player_id = html.escape(player["playerId"])

        page += f"""
        <div class="request">

            <div class="username">
                {safe_username}
            </div>

            <div class="player-id">
                Player ID: {safe_player_id}
            </div>

            <p>
                Waiting for approval.
            </p>

            <form
                method="POST"
                action="/verify"
                style="display:inline;"
            >

                <input
                    type="hidden"
                    name="index"
                    value="{index}"
                >

                <button
                    class="verify"
                    type="submit"
                >
                    ✅ Verify
                </button>

            </form>

            <form
                method="POST"
                action="/reject"
                style="display:inline;"
            >

                <input
                    type="hidden"
                    name="index"
                    value="{index}"
                >

                <button
                    class="reject"
                    type="submit"
                >
                    ❌ Reject
                </button>

            </form>

        </div>
        """

    page += """
    </body>
    </html>
    """

    return page


@app.route("/verify", methods=["POST"])
def verify():

    if not session.get("admin_logged_in"):
        return "Unauthorized", 401

    try:
        index = int(request.form.get("index", ""))

    except ValueError:
        return "Invalid request", 400

    if index < 0 or index >= len(pending_requests):
        return "Request not found", 404

    player = pending_requests.pop(index)

    print("Verified player:", player)

    return redirect(url_for("admin"))


@app.route("/reject", methods=["POST"])
def reject():

    if not session.get("admin_logged_in"):
        return "Unauthorized", 401

    try:
        index = int(request.form.get("index", ""))

    except ValueError:
        return "Invalid request", 400

    if index < 0 or index >= len(pending_requests):
        return "Request not found", 404

    player = pending_requests.pop(index)

    print("Rejected player:", player)

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
    app.run(
        host="0.0.0.0",
        port=10000
    )
