import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Store player information for profiles
ALL_PLAYERS = []
API_URL = "https://tanktrouble.com/ajax/"

# Tank Trouble players to track
# Load Tank Trouble players from players.txt
with open("players.txt", "r") as f:
    PLAYER_IDS = [
        line.strip()
        for line in f
        if line.strip()
    ]


def get_player(player_id):
    if player_id == "Laika":
        method = "tanktrouble.getPlayerDetailsByUsername"
        params = ["Laika"]
    else:
        method = "tanktrouble.getPlayerDetails"
        params = [player_id]

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1,
        "params": params
    }

    response = requests.post(API_URL, json=payload, timeout=30)
    data = response.json()

    if data.get("result", {}).get("data"):
        player_data = data["result"]["data"]
        ALL_PLAYERS.append(player_data)
    return player_data

    return None


def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r") as f:
            return json.load(f)

    return []


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def make_leaderboard(history, start_date, stat):
    players = {}

    for snapshot in history:
        if snapshot["date"] < start_date:
            continue

        player_id = snapshot["playerId"]

        if player_id not in players:
            players[player_id] = []

        players[player_id].append(snapshot)

    leaderboard = []

    for player_id, snapshots in players.items():
        snapshots.sort(key=lambda x: x["date"])

        if len(snapshots) < 2:
            continue

        first = snapshots[0]
        latest = snapshots[-1]

        amount = latest[stat] - first[stat]

        if latest["username"] in ["Corderox1", "Laika"]:
    print(
        "DEBUG:",
        latest["username"],
        "first =", first[stat],
        "latest =", latest[stat],
        "amount =", amount
    )

        leaderboard.append({
            "playerId": player_id,
            "username": latest["username"],
            "kills": amount
        })

    leaderboard.sort(key=lambda x: x["kills"], reverse=True)

    return leaderboard

# Get current time/date
now = datetime.now(ZoneInfo("America/Chicago"))
today = now.strftime("%Y-%m-%d")

# Load previous history
history = load_history()

print("Checking players...")

for player_id in PLAYER_IDS:
    try:
        player = get_player(player_id)

        if player:
            snapshot = {
                "date": today + " " + now.strftime("%H:%M:%S"),
                "playerId": player["playerId"],
                "username": player["username"],
                "kills": player["kills"],
                "deaths": player["deaths"],
                "victories": player["victories"],
                "suicides": player["suicides"],
                "xp": player["xp"]
            }

            history.append(snapshot)

            print(
                player["username"],
                "- Kills:",
                player["kills"]
            )

        else:
            print("Could not find player:", player_id)

    except Exception as e:
        print("Error checking", player_id, ":", e)


# Save history
save_json("history.json", history)


# Beginning of today
day_start = now.strftime("%Y-%m-%d")

# Find the beginning of the current week (Monday)
week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")

# Beginning of current month
month_start = now.strftime("%Y-%m-01")

# Beginning of current year
year_start = now.strftime("%Y-01-01")


# Create kill leaderboards
daily = make_leaderboard(history, day_start, "kills")
weekly = make_leaderboard(history, week_start, "kills")
monthly = make_leaderboard(history, month_start, "kills")
yearly = make_leaderboard(history, year_start, "kills")

# Create win leaderboards
daily_wins = make_leaderboard(history, day_start, "victories")
weekly_wins = make_leaderboard(history, week_start, "victories")
monthly_wins = make_leaderboard(history, month_start, "victories")
yearly_wins = make_leaderboard(history, year_start, "victories")

# Save kill leaderboards
save_json("daily.json", daily)
save_json("weekly.json", weekly)
save_json("monthly.json", monthly)
save_json("yearly.json", yearly)

# Save win leaderboards
save_json("daily_wins.json", daily_wins)
save_json("weekly_wins.json", weekly_wins)
save_json("monthly_wins.json", monthly_wins)
save_json("yearly_wins.json", yearly_wins)

print("--------------------")
print("Leaderboards updated!")


# Save player profiles
save_json("stats.json", ALL_PLAYERS)
