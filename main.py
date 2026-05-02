from fastapi import FastAPI
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

app = FastAPI()


def get_player_id(name):
    result = players.find_players_by_full_name(name)
    if not result:
        return None
    return result[0]["id"]


def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0


def avg(values):
    return round(sum(values) / len(values), 2) if values else 0


@app.get("/")
def home():
    return {"message": "NBA API is running"}


@app.get("/player-last-5")
def player_last_5(player_name: str, season: str = "2025-26"):
    player_id = get_player_id(player_name)

    if not player_id:
        return {"error": "Player not found"}

    gamelog = playergamelog.PlayerGameLog(
        player_id=player_id,
        season=season
    )

    games = gamelog.get_normalized_dict()["PlayerGameLog"][:5]

    return {
        "player": player_name,
        "season": season,
        "last_5_games": games
    }


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

    quick_table = []
    full_game_logs = []

    for game in raw_games:
        pts = safe_float(game.get("PTS"))
        reb = safe_float(game.get("REB"))
        ast = safe_float(game.get("AST"))
        stl = safe_float(game.get("STL"))
        blk = safe_float(game.get("BLK"))
        tov = safe_float(game.get("TOV"))
        minutes = safe_float(game.get("MIN"))

        pra = pts + reb + ast
        pr = pts + reb
        pa = pts + ast
        ra = reb + ast
        stocks = stl + blk

        quick_table.append({
            "date": game.get("GAME_DATE"),
            "matchup": game.get("MATCHUP"),
            "result": game.get("WL"),
            "minutes": minutes,
            "points": pts,
            "rebounds": reb,
            "assists": ast,
            "pra": pra,
            "points_rebounds": pr,
            "points_assists": pa,
            "rebounds_assists": ra,
            "steals": stl,
            "blocks": blk,
            "turnovers": tov
        })

        full_game_logs.append({
            "game_info": {
                "game_id": game.get("Game_ID"),
                "date": game.get("GAME_DATE"),
                "matchup": game.get("MATCHUP"),
                "result": game.get("WL"),
                "minutes": minutes,
                "plus_minus": safe_float(game.get("PLUS_MINUS"))
            },
            "main_stats": {
                "points": pts,
                "rebounds": reb,
                "assists": ast,
                "pra": pra,
                "points_rebounds": pr,
                "points_assists": pa,
                "rebounds_assists": ra
            },
            "defense_and_misc": {
                "steals": stl,
                "blocks": blk,
                "stocks": stocks,
                "turnovers": tov,
                "personal_fouls": safe_float(game.get("PF"))
            },
            "rebounds_split": {
                "offensive_rebounds": safe_float(game.get("OREB")),
                "defensive_rebounds": safe_float(game.get("DREB"))
            },
            "shooting": {
                "field_goals_made": safe_float(game.get("FGM")),
                "field_goals_attempted": safe_float(game.get("FGA")),
                "field_goal_percentage": safe_float(game.get("FG_PCT")),
                "three_pointers_made": safe_float(game.get("FG3M")),
                "three_pointers_attempted": safe_float(game.get("FG3A")),
                "three_point_percentage": safe_float(game.get("FG3_PCT")),
                "free_throws_made": safe_float(game.get("FTM")),
                "free_throws_attempted": safe_float(game.get("FTA")),
                "free_throw_percentage": safe_float(game.get("FT_PCT"))
            }
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

    stat_key = stat_map.get(stat.upper(), "rebounds")

    values = []
    for game in quick_table:
        if stat_key in game:
            values.append(safe_float(game.get(stat_key)))
        else:
            for full_game in full_game_logs:
                shooting = full_game.get("shooting", {})
                misc = full_game.get("defense_and_misc", {})
                if stat_key in shooting:
                    values.append(safe_float(shooting.get(stat_key)))
                    break
                if stat_key in misc:
                    values.append(safe_float(misc.get(stat_key)))
                    break

    minutes_values = [safe_float(game.get("minutes")) for game in quick_table]
    hit_count = sum(1 for value in values if value > line)

    betting_summary = {
        "requested_stat": stat.upper(),
        "line": line,
        "last_5_values": values,
        "average": avg(values),
        "minimum": min(values) if values else 0,
        "maximum": max(values) if values else 0,
        "hit_rate": f"{hit_count}/5",
        "hit_percentage": f"{round((hit_count / 5) * 100)}%",
        "minutes_average": avg(minutes_values),
        "minutes_range": f"{min(minutes_values) if minutes_values else 0}-{max(minutes_values) if minutes_values else 0}",
        "minutes_values": minutes_values
    }

    return {
        "player": player_name,
        "season": season,
        "sample": "last_5_games",
        "betting_summary": betting_summary,
        "quick_table_last_5": quick_table,
        "full_game_logs": full_game_logs
    }