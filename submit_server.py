from flask import Flask, request, jsonify, session, redirect, url_for
import os
import html
import requests

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

app.secret_key = os.environ.get("ADMIN_PASSWORD", "temporary-secret")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

TANK_TROUBLE_API = "https://tanktrouble.com/ajax/"

# Pending submissions
pending_requests = []


# ============================================================
# TANKTROUBLE API
# ============================================================

def get_player_by_username(username):
    """Look up a TankTrouble player by username."""

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

    if "result" not in data:
        return None

    print("FULL PLAYER DATA:", data["result"])

    return data["result"]

   except Exception as e:
       return {
          "error": str(e)
    }


# ============================================================
# LEADERBOARD PLAYER CHECK
# ============================================================

def get_leaderboard_player_ids():
    """
    Get the Player IDs of players currently listed in players.txt.
    """

    player_ids = set()

    try:

        if not os.path.exists("players.txt"):
            return player_ids

        with open("players.txt", "r", encoding="utf-8") as f:

            usernames = [
                line.strip()
                for line in f
                if line.strip()
            ]

        for username in usernames:

            player = get_player_by_username(username)

            if player:

                player_id = player.get("playerId")

                if player_id:
                    player_ids.add(str(player_id))

    except Exception as e:

        print(
            "Leaderboard player lookup error:",
            repr(e)
        )

    return player_ids


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return "TankTrouble Leaderboard backend is running!"


# ============================================================
# PLAYER SUBMISSION
# ============================================================

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

    # --------------------------------------------------------
    # Look up player on TankTrouble
    # --------------------------------------------------------

    player = get_player_by_username(username)

if not player:
    return jsonify({
        "success": False,
        "message": "The TankTrouble API lookup failed."
    }), 500

if "error" in player:
    return jsonify({
        "success": False,
        "message": "TankTrouble API error: " + player["error"]
    }), 500

    # --------------------------------------------------------
    # Check if already on leaderboard
    # --------------------------------------------------------

    leaderboard_players = get_leaderboard_player_ids()

    if player_id in leaderboard_players:

        return jsonify({
            "success": False,
            "message": "This player is already on the leaderboard."
        }), 400

    # --------------------------------------------------------
    # Check if already pending
    # --------------------------------------------------------

    for pending in pending_requests:

        if pending["playerId"] == player_id:

            return jsonify({
                "success": False,
                "message": "This player is already waiting for approval."
            }), 400

    # --------------------------------------------------------
    # Add to pending submissions
    # --------------------------------------------------------

    pending_requests.append({

        "username": player.get(
            "username",
            username
        ),

        "playerId": player_id
    })

    print(
        "NEW SUBMISSION:",
        player.get("username", username),
        player_id
    )

    return jsonify({

        "success": True,

        "message":
            "Submission received and is waiting for approval!"
    })


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if request.method == "POST":

        password = request.form.get(
            "password",
            ""
        )

        if password == ADMIN_PASSWORD:

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin")
            )

        return """
        <h2>Wrong password ❌</h2>
        <a href="/admin">Try again</a>
        """

    # --------------------------------------------------------
    # REQUIRE LOGIN
    # --------------------------------------------------------

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
                    margin-right: 5px;
                }

                button {
                    padding: 10px 18px;
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

    # --------------------------------------------------------
    # ADMIN PANEL
    # --------------------------------------------------------

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

            h2 {

                color: white;

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

        <h1>
            TankTrouble Leaderboard Admin
        </h1>

        <h2>
            Pending Submissions
        </h2>

    """

    # --------------------------------------------------------
    # NO REQUESTS
    # --------------------------------------------------------

    if not pending_requests:

        html_page += """

        <p>
            No pending submissions.
        </p>

        """

    # --------------------------------------------------------
    # DISPLAY REQUESTS
    # --------------------------------------------------------

    for index, player in enumerate(
        pending_requests
    ):

        safe_username = html.escape(
            player["username"]
        )

        safe_player_id = html.escape(
            player["playerId"]
        )

        html_page += f"""

        <div class="request">

            <div class="username">

                {safe_username}

            </div>

            <div class="player-id">

                Player ID:
                {safe_player_id}

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

    html_page += """

    </body>

    </html>

    """

    return html_page


# ============================================================
# VERIFY SUBMISSION
# ============================================================

@app.route("/verify", methods=["POST"])
def verify():

    if not session.get("admin_logged_in"):

        return "Unauthorized", 401

    try:

        index = int(
            request.form.get("index")
        )

    except:

        return "Invalid request", 400

    if (
        index < 0
        or index >= len(pending_requests)
    ):

        return "Request not found", 404

    # Remove from pending
    player = pending_requests.pop(index)

    username = player["username"]

    # --------------------------------------------------------
    # Add approved player to players.txt
    # --------------------------------------------------------

    try:

        # Make sure players.txt exists
        if not os.path.exists("players.txt"):

            open(
                "players.txt",
                "w",
                encoding="utf-8"
            ).close()

        # Check for duplicate username
        with open(
            "players.txt",
            "r",
            encoding="utf-8"
        ) as f:

            existing_players = [
                line.strip().lower()
                for line in f
                if line.strip()
            ]

        if username.lower() not in existing_players:

            with open(
                "players.txt",
                "a",
                encoding="utf-8"
            ) as f:

                f.write(
                    username + "\n"
                )

        print(
            "PLAYER VERIFIED:",
            username,
            player["playerId"]
        )

    except Exception as e:

        print(
            "COULD NOT ADD PLAYER:",
            repr(e)
        )

        return (
            "Could not add player to leaderboard",
            500
        )

    return redirect(
        url_for("admin")
    )


# ============================================================
# REJECT SUBMISSION
# ============================================================

@app.route("/reject", methods=["POST"])
def reject():

    if not session.get("admin_logged_in"):

        return "Unauthorized", 401

    try:

        index = int(
            request.form.get("index")
        )

    except:

        return "Invalid request", 400

    if (
        index < 0
        or index >= len(pending_requests)
    ):

        return "Request not found", 404

    player = pending_requests.pop(index)

    print(
        "PLAYER REJECTED:",
        player["username"],
        player["playerId"]
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# PENDING API
# ============================================================

@app.route("/pending")
def pending():

    if not session.get("admin_logged_in"):

        return jsonify({

            "success": False,

            "message": "Unauthorized"

        }), 401

    return jsonify(
        pending_requests
    )


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=10000

    )
