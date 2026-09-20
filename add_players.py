import requests

API_URL = "https://tanktrouble.com/ajax/"

# Load usernames
with open("usernames.txt", "r", encoding="utf-8") as f:
    usernames = [
        line.strip()
        for line in f
        if line.strip()
    ]

# Load players already on the leaderboard
with open("players.txt", "r", encoding="utf-8") as f:
    existing_ids = {
        line.strip()
        for line in f
        if line.strip()
    }


def find_player(username):

    payload = {
        "jsonrpc": "2.0",
        "method": "tanktrouble.getPlayerDetailsByUsername",
        "id": 1,
        "params": [username]
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=30
        )

        data = response.json()

        if data.get("result", {}).get("data"):
            return data["result"]["data"]

    except Exception as e:
        print(f"ERROR looking up {username}: {e}")

    return None


new_players = []
already_added = []
not_found = []


print("Checking players...")
print()


for username in usernames:

    print(f"Looking up: {username}")

    player = find_player(username)

    if not player:
        print("  ❌ Not found")
        not_found.append(username)
        continue

    player_id = str(player["playerId"])
    actual_username = player["username"]

    if player_id in existing_ids:
        print(f"  ✅ Already added ({player_id})")
        already_added.append(actual_username)
        continue

    print(f"  🆕 Found! {actual_username} → {player_id}")

    new_players.append(player_id)
    existing_ids.add(player_id)


# Add new IDs to players.txt
if new_players:

    with open("players.txt", "a", encoding="utf-8") as f:

        for player_id in new_players:
            f.write(player_id + "\n")


print()
print("==============================")
print("RESULTS")
print("==============================")

print(f"🆕 New players added: {len(new_players)}")
print(f"✅ Already on leaderboard: {len(already_added)}")
print(f"❌ Not found: {len(not_found)}")

if new_players:
    print()
    print("New Player IDs:")
    for player_id in new_players:
        print(player_id)

if not_found:
    print()
    print("Not Found:")
    for username in not_found:
        print(username)

print()
print("Done!")
