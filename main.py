from fastapi import FastAPI
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

app = FastAPI()


def get_player_id(player_name: str):
    matches = players.find_players_by_full_name(player_name)
    if not matches:
        return None
    return matches[0]["id"]


def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0


def avg(values):
    return round(sum(values) / len(values), 2) if values else 0


@app.get("/")
def home():
    return {"message": "NBA Betting API is running"}


@app.get("/player-last-5-detail")
def player_last_5_detail(
    player_name: str,
    stat: str = "REB",
    line: float = 4.5,
    season: str = "2025-26"
):
    player_id = get_player_id(player_name)

    if not player_id:
        return {"error": "Player not found"}

    gamelog = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season
    )

    raw_games = gamelog.get_normalized_dict()["PlayerGameLog"][:5]

    detailed_games = []

    for game in raw_games:
        pts = safe_float(game.get("PTS"))
        reb = safe_float(game.get("REB"))
        ast = safe_float(game.get("AST"))
        stl = safe_float(game.get("STL"))
        blk = safe_float(game.get("BLK"))
        tov = safe_float(game.get("TOV"))
        fg3m = safe_float(game.get("FG3M"))

        detailed_games.append({
            "game_id": game.get("Game_ID"),
            "date": game.get("GAME_DATE"),
            "matchup": game.get("MATCHUP"),
            "win_loss": game.get("WL"),
            "minutes": safe_float(game.get("MIN")),

            "points": pts,
            "rebounds": reb,
            "assists": ast,
            "steals": stl,
            "blocks": blk,
            "turnovers": tov,
            "personal_fouls": safe_float(game.get("PF")),
            "plus_minus": safe_float(game.get("PLUS_MINUS")),

            "offensive_rebounds": safe_float(game.get("OREB")),
            "defensive_rebounds": safe_float(game.get("DREB")),

            "field_goals_made": safe_float(game.get("FGM")),
            "field_goals_attempted": safe_float(game.get("FGA")),
            "field_goal_percentage": safe_float(game.get("FG_PCT")),

            "three_pointers_made": fg3m,
            "three_pointers_attempted": safe_float(game.get("FG3A")),
            "three_point_percentage": safe_float(game.get("FG3_PCT")),

            "free_throws_made": safe_float(game.get("FTM")),
            "free_throws_attempted": safe_float(game.get("FTA")),
            "free_throw_percentage": safe_float(game.get("FT_PCT")),

            "pra": pts + reb + ast,
            "points_rebounds": pts + reb,
            "points_assists": pts + ast,
            "rebounds_assists": reb + ast,
            "stocks": stl + blk,
            "fantasy_simple": pts + reb + ast + stl + blk - tov
        })

    stat_map = {
        "PTS": "points",
        "REB": "rebounds",
        "AST": "assists",
        "STL": "steals",
        "BLK": "blocks",
        "TOV": "turnovers",
        "3PM": "three_pointers_made",
        "FG3M": "three_pointers_made",
        "PRA": "pra",
        "PR": "points_rebounds",
        "PA": "points_assists",
        "RA": "rebounds_assists",
        "STOCKS": "stocks"
    }

    stat_key = stat_map.get(stat.upper(), stat.lower())

    values = [safe_float(game.get(stat_key, 0)) for game in detailed_games]
    minutes = [safe_float(game.get("minutes", 0)) for game in detailed_games]

    hit_count = sum(1 for value in values if value > line)

    return {
        "player": player_name,
        "season": season,
        "sample": "last_5_games",
        "requested_stat": stat.upper(),
        "line": line,

        "summary": {
            "values": values,
            "average": avg(values),
            "minimum": min(values) if values else 0,
            "maximum": max(values) if values else 0,
            "hit_rate": f"{hit_count}/5",
            "average_minutes": avg(minutes),
            "minimum_minutes": min(minutes) if minutes else 0,
            "maximum_minutes": max(minutes) if minutes else 0
        },

        "last_5_games": detailed_games
    }