from fastapi import FastAPI
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

app = FastAPI()

def get_player_id(name):
    result = players.find_players_by_full_name(name)
    if not result:
        return None
    return result[0]["id"]

@app.get("/")
def home():
    return {"message": "NBA API is running"}

@app.get("/player-last-5")
def player_last_5(player_name: str):
    player_id = get_player_id(player_name)

    if not player_id:
        return {"error": "Player not found"}

    gamelog = playergamelog.PlayerGameLog(
        player_id=player_id,
        season="2025-26"
    )

    games = gamelog.get_normalized_dict()["PlayerGameLog"][:5]
    return {"player": player_name, "last_5_games": games}