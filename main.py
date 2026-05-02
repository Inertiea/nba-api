from fastapi import FastAPI
from nba_api.stats.endpoints import playergamelog, leaguegamefinder, boxscoretraditionalv2
from nba_api.stats.static import players, teams
from datetime import datetime
import time

app = FastAPI()


# -----------------------
# HELPERS
# -----------------------

def get_current_season():
    year = datetime.now().year
    month = datetime.now().month

    if month >= 10:
        return f"{year}-{str(year + 1)[-2:]}"
    return f"{year - 1}-{str(year)[-2:]}"


def get_player_id(name):
    result = players.find_players_by_full_name(name)
    return result[0]["id"] if result else None


def get_team_id(team_abbrev):
    for team in teams.get_teams():
        if team["abbreviation"] == team_abbrev.upper():
            return team["id"]
    return None


def safe_float(value):
    try:
        if isinstance(value, str) and ":" in value:
            minutes, seconds = value.split(":")
            return round(float(minutes) + float(seconds) / 60, 1)
        return round(float(value), 1)
    except:
        return 0.0


def avg(values):
    return round(sum(values) / len(values), 2) if values else 0


def sort_games_newest_first(games):
    def parse_date(game):
        date_value = game.get("GAME_DATE", "")

        for date_format in ("%b %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_value, date_format)
            except:
                pass

        return datetime.min

    return sorted(games, key=parse_date, reverse=True)


# -----------------------
# ROOT
# -----------------------

@app.get("/")
def home():
    return {"message": "NBA API is running"}


# -----------------------
# PLAYER LAST 5
# -----------------------

@app.get("/player-last-5")
def player_last_5(player_name: str, season: str = None, season_type: str = "Playoffs"):

    if not season:
        season = get_current_season()

    player_id = get_player_id(player_name)
    if not player_id:
        return {"error": "Player not found"}

    try:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star=season_type
        )

        games = gamelog.get_normalized_dict()["PlayerGameLog"]
        games = sort_games_newest_first(games)[:5]

        return {
            "player": player_name,
            "season": season,
            "season_type": season_type,
            "last_5_games": games
        }

    except Exception as e:
        return {"error": str(e)}


# -----------------------
# PLAYER DETAIL (BETTING)
# -----------------------

@app.get("/player-last-5-detail")
def player_last_5_detail(
    player_name: str,
    stat: str = "REB",
    line: float = 4.5,
    season: str = None,
    season_type: str = "Playoffs"
):

    if not season:
        season = get_current_season()

    player_id = get_player_id(player_name)
    if not player_id:
        return {"error": "Player not found"}

    try:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star=season_type
        )

        raw_games = gamelog.get_normalized_dict()["PlayerGameLog"]
        raw_games = sort_games_newest_first(raw_games)[:5]

        values = []
        minutes_values = []
        quick_table = []

        for game in raw_games:
            val = safe_float(game.get(stat.upper(), 0))
            minutes = safe_float(game.get("MIN"))

            values.append(val)
            minutes_values.append(minutes)

            quick_table.append({
                "date": game["GAME_DATE"],
                "matchup": game["MATCHUP"],
                "minutes": minutes,
                "points": safe_float(game.get("PTS")),
                "rebounds": safe_float(game.get("REB")),
                "assists": safe_float(game.get("AST"))
            })

        hit_count = sum(1 for v in values if v > line)

        return {
            "player": player_name,
            "season": season,
            "season_type": season_type,
            "betting_summary": {
                "requested_stat": stat,
                "line": line,
                "last_5_values": values,
                "average": avg(values),
                "minimum": min(values),
                "maximum": max(values),
                "hit_rate": f"{hit_count}/5",
                "hit_percentage": f"{round((hit_count/5)*100)}%",
                "minutes_average": avg(minutes_values),
                "minutes_range": f"{min(minutes_values)}-{max(minutes_values)}"
            },
            "quick_table_last_5": quick_table
        }

    except Exception as e:
        return {"error": str(e)}


# -----------------------
# TEAM LAST GAME LINEUP (FIXED)
# -----------------------

@app.get("/team-last-game-lineup")
def team_last_game_lineup(team: str, season: str = None, season_type: str = "Playoffs"):

    if not season:
        season = get_current_season()

    team_id = get_team_id(team)
    if not team_id:
        return {"error": "Team not found"}

    try:
        finder = leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable=season_type
        )

        games = finder.get_normalized_dict()["LeagueGameFinderResults"]

        if not games:
            return {"error": "No games found"}

        games = sort_games_newest_first(games)
        last_game = games[0]

        game_id = last_game["GAME_ID"]

        time.sleep(0.6)  # prevent rate limit crash

        boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id)
        players_stats = boxscore.get_normalized_dict()["PlayerStats"]

        lineup = []

        for p in players_stats:
            if p["TEAM_ID"] == team_id:
                lineup.append({
                    "player": p["PLAYER_NAME"],
                    "minutes": safe_float(p.get("MIN")),
                    "points": safe_float(p.get("PTS")),
                    "rebounds": safe_float(p.get("REB")),
                    "assists": safe_float(p.get("AST"))
                })

        lineup = sorted(lineup, key=lambda x: x["minutes"], reverse=True)

        return {
            "team": team.upper(),
            "last_game": {
                "date": last_game["GAME_DATE"],
                "matchup": last_game["MATCHUP"]
            },
            "players": lineup
        }

    except Exception as e:
        return {"error": str(e)}