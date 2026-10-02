from flask import Flask, request, jsonify

app = Flask(__name__)

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

    return jsonify({
        "success": True,
        "message": f"Submission received for {username}!"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
