from flask import Flask, request, jsonify, session, redirect, url_for
import os
import html
import requests
import json
import base64

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# ============================================================
# SETTINGS
# ============================================================

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

app.secret_key = os.environ.get(
    "SESSION_SECRET",
    os.environ.get("ADMIN_PASSWORD", "temporary-secret")
)

TANK_TROUBLE_API = "https://tanktrouble.com/ajax/"

GITHUB_REPO = "corderox1/tanktrouble-leaderboard"

GITHUB_PLAYERS_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/contents/players.txt"
)

GITHUB_PENDING_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/contents/pending.json"
)

PENDING_FILE = "pending.json"


# ============================================================
# GITHUB HELPERS
# ============================================================

def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }


def get_github_file(url):
    """
    Get a file from GitHub.
    Returns the GitHub response JSON or None on failure.
    """

    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN is not configured.")
        return None

    try:

        response = requests.get(
            url,
            headers=github_headers(),
            timeout=10
        )

        print("GitHub GET STATUS:", response.status_code)

        if response.status_code != 200:
            print("GitHub GET ERROR:", response.text)
            return None

        return response.json()

    except Exception as e:

        print("GitHub GET ERROR:", repr(e))

        return None


# ============================================================
# PENDING REQUESTS
# ============================================================

def load_pending_requests():

    # Try GitHub first.
    # This makes pending submissions survive Render restarts.

    github_data = get_github_file(GITHUB_PENDING_URL)

    if github_data:

        try:

            content = base64.b64decode(
                github_data["content"]
            ).decode("utf-8")

            pending = json.loads(content)

            if isinstance(pending, list):

                print(
                    "Loaded",
                    len(pending),
                    "pending submissions from GitHub."
                )

                # Also save a local copy.
                with open(
                    PENDING_FILE,
                    "w",
                    encoding="utf-8"
                ) as file:

                    json.dump(
                        pending,
                        file,
                        indent=4
                    )

                return pending

        except Exception as e:

            print(
                "Could not load pending.json from GitHub:",
                repr(e)
            )

    # Fallback to local file.
    try:

        with open(
            PENDING_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            pending = json.load(file)

            if isinstance(pending, list):

                print(
                    "Loaded",
                    len(pending),
                    "pending submissions locally."
                )

                return pending

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):

        pass

    print("No pending submissions found.")

    return []


def save_pending_requests():

    # Always save a local copy first.

    try:

        with open(
            PENDING_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                pending_requests,
                file,
                indent=4
            )

    except Exception as e:

        print(
            "Could not save local pending.json:",
            repr(e)
        )


    # Make sure GitHub token exists.

    if not GITHUB_TOKEN:

        print(
            "GITHUB_TOKEN is not configured."
        )

        return False


    try:

        # Get the current GitHub file so we have its SHA.

        github_data = get_github_file(
            GITHUB_PENDING_URL
        )

        if not github_data:

            print(
                "Could not get pending.json from GitHub."
            )

            return False


        # Convert pending requests to JSON.

        new_content = json.dumps(
            pending_requests,
            indent=4
        ) + "\n"


        # Encode for GitHub.

        encoded_content = base64.b64encode(
            new_content.encode("utf-8")
        ).decode("utf-8")


        update_data = {
            "message": "Update pending leaderboard submissions",
            "content": encoded_content,
            "sha": github_data["sha"],
            "branch": "main"
        }


        response = requests.put(
            GITHUB_PENDING_URL,
            headers=github_headers(),
            json=update_data,
            timeout=10
        )


        print(
            "GitHub pending.json UPDATE STATUS:",
            response.status_code
        )


        if response.status_code not in (200, 201):

            print(
                "GitHub pending.json UPDATE ERROR:",
                response.text
            )

            return False


        print(
            "GitHub pending.json updated successfully."
        )

        return True


    except Exception as e:

        print(
            "GitHub pending.json ERROR:",
            repr(e)
        )

        return False


# Load pending requests when the server starts.

pending_requests = load_pending_requests()


# ============================================================
# TANK TROUBLE API
# ============================================================

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

        print(
            "TankTrouble API STATUS:",
            response.status_code
        )

        print(
            "TankTrouble API RESPONSE:",
            response.text
        )

        api_response = response.json()

        api_result = api_response.get("result")

        if not api_result or not api_result.get("result"):

            print(
                "TankTrouble API did not return a successful result."
            )

            return None

        player = api_result.get("data")

        print(
            "FULL PLAYER DATA:",
            player
        )

        return player

    except Exception as e:

        print(
            "TankTrouble API ERROR:",
            repr(e)
        )

        return None


# ============================================================
# LEADERBOARD
# ============================================================

def get_leaderboard_player_ids():

    players = set()

    try:

        with open(
            "players.txt",
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                line = line.strip()

                if line:

                    players.add(line)

    except FileNotFoundError:

        print(
            "players.txt was not found locally."
        )


    return players


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return "TankTrouble Leaderboard backend is running!"


# ============================================================
# SUBMIT PLAYER
# ============================================================

@app.route("/submit", methods=["POST", "OPTIONS"])
def submit():

    if request.method == "OPTIONS":
        return "", 204

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message": "Invalid submission."
            }), 400


        username = data.get(
            "username",
            ""
        ).strip()


        if not username:

            return jsonify({
                "success": False,
                "message": "Username is required."
            }), 400


        print(
            "SUBMISSION:",
            username
        )


        # Look up player on TankTrouble.

        player = get_player_by_username(
            username
        )


        print(
            "PLAYER FROM API:",
            player
        )


        if not player:

            return jsonify({
                "success": False,
                "message":
                    "That TankTrouble username could not be found."
            }), 404


        # Get Player ID.

        player_id = str(
            player.get(
                "playerId",
                ""
            )
        )


        print(
            "PLAYER ID:",
            player_id
        )


        if not player_id:

            return jsonify({
                "success": False,
                "message":
                    "Could not determine the player's ID."
            }), 500


        # Check current leaderboard.

        leaderboard_players = (
            get_leaderboard_player_ids()
        )


        print(
            "LEADERBOARD IDS LOADED:",
            len(leaderboard_players)
        )


        if player_id in leaderboard_players:

            return jsonify({
                "success": False,
                "message":
                    "This player is already on the leaderboard."
            }), 400


        # Check pending requests.

        for pending in pending_requests:

            if pending["playerId"] == player_id:

                return jsonify({
                    "success": False,
                    "message":
                        "This player is already waiting for approval."
                }), 400


        # Add to pending.

        new_request = {
            "username":
                player.get(
                    "username",
                    username
                ),

            "playerId":
                player_id
        }


        pending_requests.append(
            new_request
        )


        # Save it permanently.

        saved = save_pending_requests()


        if not saved:

            # Remove it again if GitHub failed.

            pending_requests.pop()

            save_pending_requests()

            return jsonify({
                "success": False,
                "message":
                    "The submission could not be saved. Please try again."
            }), 500


        print(
            "Submission saved:",
            new_request
        )


        return jsonify({
            "success": True,
            "message":
                "Submission received and is waiting for approval!"
        })


    except Exception as e:

        print(
            "SUBMIT ERROR:",
            repr(e)
        )


        return jsonify({
            "success": False,
            "message":
                "SUBMIT ERROR: " + str(e)
        }), 500


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin():

    # Login.

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
        <!DOCTYPE html>
        <html>

        <body style="
            background:#111;
            color:white;
            font-family:Arial;
            padding:30px;
        ">

            <h2>Wrong password ❌</h2>

            <a
                href="/admin"
                style="color:gold;"
            >
                Try again
            </a>

        </body>

        </html>
        """


    # Require login.

    if not session.get(
        "admin_logged_in"
    ):

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

            <h1>
                TankTrouble Leaderboard Admin
            </h1>

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


    # Admin panel.

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

        <h1>
            TankTrouble Admin Panel
        </h1>

        <h2>
            Pending Submissions
        </h2>
    """


    if not pending_requests:

        page += """
        <p>
            No pending submissions.
        </p>
        """


    for index, player in enumerate(
        pending_requests
    ):

        safe_username = html.escape(
            player["username"]
        )

        safe_player_id = html.escape(
            player["playerId"]
        )


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


# ============================================================
# VERIFY PLAYER
# ============================================================

@app.route(
    "/verify",
    methods=["POST"]
)
def verify():

    if not session.get(
        "admin_logged_in"
    ):

        return "Unauthorized", 401


    try:

        index = int(
            request.form.get(
                "index",
                ""
            )
        )

    except ValueError:

        return "Invalid request", 400


    if (
        index < 0
        or index >= len(pending_requests)
    ):

        return "Request not found", 404


    player = pending_requests[index]

    username = player["username"]
    player_id = player["playerId"]


    print(
        "Verifying player:",
        player
    )


    if not GITHUB_TOKEN:

        return (
            "GitHub token is not configured.",
            500
        )


    try:

        # ====================================================
        # GET players.txt
        # ====================================================

        file_data = get_github_file(
            GITHUB_PLAYERS_URL
        )


        if not file_data:

            return (
                "Could not read players.txt from GitHub.",
                500
            )


        current_content = base64.b64decode(
            file_data["content"]
        ).decode("utf-8")


        current_players = (
            current_content.splitlines()
        )


        # ====================================================
        # PLAYER ALREADY EXISTS
        # ====================================================

        if player_id in current_players:

            pending_requests.pop(index)

            save_pending_requests()

            print(
                "Player was already on GitHub:",
                player
            )

            return redirect(
                url_for("admin")
            )


        # ====================================================
        # ADD PLAYER ID
        # ====================================================

        new_content = (
            current_content.rstrip()
            + "\n"
            + player_id
            + "\n"
        )


        encoded_content = base64.b64encode(
            new_content.encode("utf-8")
        ).decode("utf-8")


        update_data = {

            "message":
                f"Add approved player {username}",

            "content":
                encoded_content,

            "sha":
                file_data["sha"],

            "branch":
                "main"
        }


        update_response = requests.put(

            GITHUB_PLAYERS_URL,

            headers=github_headers(),

            json=update_data,

            timeout=10
        )


        print(
            "GitHub players.txt UPDATE STATUS:",
            update_response.status_code
        )


        if update_response.status_code not in (
            200,
            201
        ):

            print(
                "GitHub UPDATE ERROR:",
                update_response.text
            )

            return (
                "GitHub rejected the update. "
                "Player was NOT approved.",
                500
            )


        print(
            "GitHub players.txt updated successfully."
        )


        # ====================================================
        # REMOVE FROM PENDING
        # ====================================================

        pending_requests.pop(index)


        saved = save_pending_requests()


        if not saved:

            print(
                "WARNING: Player was added to "
                "players.txt but pending.json "
                "could not be updated."
            )


        print(
            "Approved player:",
            player
        )


        return redirect(
            url_for("admin")
        )


    except Exception as e:

        print(
            "VERIFY ERROR:",
            repr(e)
        )


        return (
            "Verification failed: " + str(e),
            500
        )


# ============================================================
# REJECT PLAYER
# ============================================================

@app.route(
    "/reject",
    methods=["POST"]
)
def reject():

    if not session.get(
        "admin_logged_in"
    ):

        return "Unauthorized", 401


    try:

        index = int(
            request.form.get(
                "index",
                ""
            )
        )

    except ValueError:

        return "Invalid request", 400


    if (
        index < 0
        or index >= len(pending_requests)
    ):

        return "Request not found", 404


    player = pending_requests.pop(index)


    saved = save_pending_requests()


    if not saved:

        print(
            "WARNING: Rejected player was removed "
            "locally but pending.json could not "
            "be updated on GitHub."
        )


    print(
        "Rejected player:",
        player
    )


    return redirect(
        url_for("admin")
    )


# ============================================================
# PENDING API
# ============================================================

@app.route("/pending")
def pending():

    if not session.get(
        "admin_logged_in"
    ):

        return jsonify({
            "success": False,
            "message": "Unauthorized"
        }), 401


    return jsonify(
        pending_requests
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
