from flask import Flask, request, jsonify

app = Flask(__name__)

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

    # Check if this username is already waiting
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


@app.route("/pending")
def pending():
    return jsonify(pending_requests)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
