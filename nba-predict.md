Complete Technical Guide: From Data Collection to a Working Model
Every night the NBA generates a data stream no human analyst can process manually: ~100 possessions per team, tracking of 10 players 25 times per second, hundreds of micro-decisions per game. The human brain perceives games through narrative - "LeBron was on fire," "the team fell apart in the fourth quarter." A machine sees field goal percentage, defensive rebounds, turnovers - and finds patterns hidden behind the noise. In this article we build a full prediction system combining three probability layers: sportsbook lines (DraftKings/FanDuel), Polymarket prediction market data (crowd intelligence on the blockchain), and a custom ML model with Claude API as the interpreter. The entire pipeline is in Python: nba_api, pandas, scikit-learn, XGBoost, matplotlib.
System Architecture
The system consists of several layers, each serving its own role:
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│  nba_api │ Basketball-Reference │ balldontlie │ Kaggle       │
│                                                              │
│  ┌──────────────────────────────────────────────────┐        │
│  │    Polymarket Gamma API (prediction market)     │        │
│  │  Crowd-sourced probabilities on Polygon blockchain  │        │
│  └──────────────────────────────────────────────────┘        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                           │
│  pandas │ numpy │ data cleaning │ feature engineering        │
│                                                              │
│  ┌──────────────────────────────────────────────────┐        │
│  │  Claude API: feature generation,                    │        │
│  │  context analysis, stats interpretation             │        │
│  └──────────────────────────────────────────────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────┐        │
│  │  Merging 3 probability layers:                      │        │
│  │  Sportsbook lines + Polymarket prices + ML model  │        │
│  └──────────────────────────────────────────────────┘        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     MODEL LAYER                              │
│  Logistic Regression │ Random Forest │ XGBoost               │
│  Ensemble (Voting / Stacking)                                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 INTERPRETATION LAYER                          │
│  Claude API: natural language prediction explanation          │
│  + confidence assessment + divergence analysis                │
│    between sportsbook / Polymarket / ML                       │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                               │
│  matplotlib visualizations │ JSON reports │ Telegram bot       │
└─────────────────────────────────────────────────────────────┘

Why the NBA Is the Best Playground for Predictive ML
82 regular season games for each of 30 teams - that's 1,230 games, each with detailed statistics. A binary outcome (Win/Loss, no draws) simplifies the task to pure classification. The best team wins 68–72% of games - patterns are stable and modelable. And the free nba_api provides access to box scores, play-by-play, and shot charts without spending a dollar.
| Parameter | NBA |
|---|---|
| Events per game | ~200 possessions, 80+ shots |
| Typical score | 105–115 |
| Outcomes | 2 (W/L) - pure binary classification |
| Predictability | ~68–72% top team wins |
| API data | Free (nba_api, balldontlie) |
| Tracking data | Second Spectrum (for teams), basic tracking via NBA.com |
| Games/season | 82 (sufficient for rolling averages) |

Required Dependencies
python
# requirements.txt
anthropic>=0.40.0
nba_api>=1.4.1
pandas>=2.1.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
matplotlib>=3.8.0
seaborn>=0.13.0
requests>=2.31.0
python-dotenv>=1.0.0
schedule>=1.2.0           # pipeline automation
Installation:
bash
pip install anthropic nba_api pandas numpy scikit-learn xgboost matplotlib seaborn requests python-dotenv schedule
nba_api is a free open-source client for the NBA . com API that requires no authentication. The Polymarket Gamma API is also public.
Data Collection & Preparation
The primary data source is nba_api, which provides access to NBA . com data: box scores, play-by-play, player tracking, shot charts spanning 40+ years. The data includes all standard and advanced statistics.
Data Loading
python
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import (
    LeagueGameFinder,
    TeamGameLog,
    BoxScoreTraditionalV2,
    LeagueStandings,
)
from nba_api.stats.static import teams
import time

class NBADataLoader:
    """
    Historical NBA game data loader.
    Source: nba_api (wrapper over NBA.com API)
    """

    # NBA.com API requires delays between requests
    REQUEST_DELAY = 0.6  # seconds

    def __init__(self, seasons: list[str]):
        """
        Args:
            seasons: list of seasons in format ["2025-26", "2024-25", ...]
        """
        self.seasons = seasons
        self.team_map = {
            t["id"]: t["abbreviation"]
            for t in teams.get_teams()
        }

    def load_season_games(self, season: str) -> pd.DataFrame:
        """
        Load all NBA regular season games.
        
        nba_api returns one row per
        team per game. We need to merge
        the home and away rows into a single record.
        """
        try:
            finder = LeagueGameFinder(
                season_nullable=season,
                league_id_nullable="00",  # NBA
                season_type_nullable="Regular Season",
            )
            time.sleep(self.REQUEST_DELAY)
            
            df = finder.get_data_frames()[0]
            
            if df.empty:
                print(f"  ⚠ No data for season {season}")
                return pd.DataFrame()

            # Split into home and away
            # MATCHUP contains "vs." for home and "@" for away
            df["IS_HOME"] = df["MATCHUP"].str.contains("vs.").astype(int)
            
            home = df[df["IS_HOME"] == 1].copy()
            away = df[df["IS_HOME"] == 0].copy()

            # Rename columns
            home_cols = {
                "TEAM_ID": "HOME_TEAM_ID",
                "TEAM_ABBREVIATION": "HOME_TEAM",
                "PTS": "HOME_PTS",
                "FGM": "HOME_FGM", "FGA": "HOME_FGA",
                "FG_PCT": "HOME_FG_PCT",
                "FG3M": "HOME_FG3M", "FG3A": "HOME_FG3A",
                "FG3_PCT": "HOME_FG3_PCT",
                "FTM": "HOME_FTM", "FTA": "HOME_FTA",
                "FT_PCT": "HOME_FT_PCT",
                "OREB": "HOME_OREB", "DREB": "HOME_DREB",
                "REB": "HOME_REB",
                "AST": "HOME_AST", "STL": "HOME_STL",
                "BLK": "HOME_BLK", "TOV": "HOME_TOV",
                "PF": "HOME_PF",
                "PLUS_MINUS": "HOME_PLUS_MINUS",
            }
            away_cols = {
                "TEAM_ID": "AWAY_TEAM_ID",
                "TEAM_ABBREVIATION": "AWAY_TEAM",
                "PTS": "AWAY_PTS",
                "FGM": "AWAY_FGM", "FGA": "AWAY_FGA",
                "FG_PCT": "AWAY_FG_PCT",
                "FG3M": "AWAY_FG3M", "FG3A": "AWAY_FG3A",
                "FG3_PCT": "AWAY_FG3_PCT",
                "FTM": "AWAY_FTM", "FTA": "AWAY_FTA",
                "FT_PCT": "AWAY_FT_PCT",
                "OREB": "AWAY_OREB", "DREB": "AWAY_DREB",
                "REB": "AWAY_REB",
                "AST": "AWAY_AST", "STL": "AWAY_STL",
                "BLK": "AWAY_BLK", "TOV": "AWAY_TOV",
                "PF": "AWAY_PF",
                "PLUS_MINUS": "AWAY_PLUS_MINUS",
            }

            home = home.rename(columns=home_cols)
            away = away.rename(columns=away_cols)

            # Merge by GAME_ID
            merged = home.merge(
                away[list(away_cols.values()) + ["GAME_ID"]],
                on="GAME_ID",
                how="inner",
            )

            # Result: 1 = home win, 0 = away win
            merged["HOME_WIN"] = (
                merged["HOME_PTS"] > merged["AWAY_PTS"]
            ).astype(int)
            
            merged["GAME_DATE"] = pd.to_datetime(
                merged["GAME_DATE"]
            )
            merged["Season"] = season
            
            return merged

        except Exception as e:
            print(f"  ⚠ Loading error {season}: {e}")
            return pd.DataFrame()

    def load_all(self) -> pd.DataFrame:
        """Load all seasons."""
        frames = []
        for season in self.seasons:
            df = self.load_season_games(season)
            if not df.empty:
                frames.append(df)
                print(f"  ✓ Season {season}: {len(df)} games")
        
        result = pd.concat(frames, ignore_index=True)
        print(f"\nTotal loaded: {len(result)} games")
        return result


# === Usage ===
loader = NBADataLoader(
    seasons=["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]
)
raw_data = loader.load_all()
Cleaning & Transformation
python
class DataCleaner:
    """NBA data cleaning and standardization."""

    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Sort by date
        df["GAME_DATE"] = pd.to_datetime(
            df["GAME_DATE"], errors="coerce"
        )
        df = df.dropna(subset=["GAME_DATE"])
        df = df.sort_values("GAME_DATE").reset_index(drop=True)

        # Numeric columns
        numeric_cols = [
            c for c in df.columns
            if c.startswith(("HOME_", "AWAY_"))
            and c not in ["HOME_TEAM", "AWAY_TEAM",
                          "HOME_TEAM_ID", "AWAY_TEAM_ID"]
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Remove games with no score
        df = df.dropna(subset=["HOME_PTS", "AWAY_PTS"])

        # Compute basic derived metrics
        # Pace proxy: sum of FGA + 0.44*FTA - OREB + TOV
        for prefix in ["HOME", "AWAY"]:
            df[f"{prefix}_POSS"] = (
                df[f"{prefix}_FGA"]
                + 0.44 * df[f"{prefix}_FTA"]
                - df[f"{prefix}_OREB"]
                + df[f"{prefix}_TOV"]
            )

        # Pace: average possessions for both teams
        df["PACE"] = (df["HOME_POSS"] + df["AWAY_POSS"]) / 2

        # Offensive / Defensive Rating (points per 100 possessions)
        for prefix, opp in [("HOME", "AWAY"), ("AWAY", "HOME")]:
            poss = df[f"{prefix}_POSS"].replace(0, np.nan)
            df[f"{prefix}_ORTG"] = df[f"{prefix}_PTS"] / poss * 100
            df[f"{prefix}_DRTG"] = df[f"{opp}_PTS"] / poss * 100
            df[f"{prefix}_NET_RTG"] = (
                df[f"{prefix}_ORTG"] - df[f"{prefix}_DRTG"]
            )

        return df


clean_data = DataCleaner.clean(raw_data)
print(f"After cleaning: {len(clean_data)} games")
print(f"Distribution: Home Win={clean_data['HOME_WIN'].mean():.1%}, "
      f"Away Win={1-clean_data['HOME_WIN'].mean():.1%}")
Feature Engineering with Claude
The key stage where we create features for the model. The NBA provides an extremely rich set of metrics - Four Factors, plus/minus, pace-adjusted stats, and more.
Statistical Features (Rolling Averages)
python
class NBAFeatureEngineer:
    """
    Feature generation based on historical team statistics.
    Key idea: for each game we use ONLY data
    available BEFORE that game starts.
    """

    def __init__(self, window: int = 10):
        self.window = window

    def compute_team_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute rolling averages for each team
        over the last N games.
        
        In the NBA we use window=10 — sufficient data
        because 82 games per season provide more data.
        """
        df = df.sort_values("GAME_DATE").copy()

        # Create separate records for each team
        home_records = []
        away_records = []

        stat_cols = [
            "PTS", "FG_PCT", "FG3_PCT", "FT_PCT",
            "OREB", "DREB", "REB", "AST", "STL",
            "BLK", "TOV", "PF", "POSS", "ORTG", "DRTG",
            "NET_RTG",
        ]

        for _, row in df.iterrows():
            home_row = {
                "Date": row["GAME_DATE"],
                "Team": row["HOME_TEAM"],
                "IsHome": 1,
                "Win": row["HOME_WIN"],
                "PointDiff": row["HOME_PTS"] - row["AWAY_PTS"],
            }
            away_row = {
                "Date": row["GAME_DATE"],
                "Team": row["AWAY_TEAM"],
                "IsHome": 0,
                "Win": 1 - row["HOME_WIN"],
                "PointDiff": row["AWAY_PTS"] - row["HOME_PTS"],
            }

            for col in stat_cols:
                home_row[col] = row.get(f"HOME_{col}", np.nan)
                away_row[col] = row.get(f"AWAY_{col}", np.nan)

            # Opponent stats (for defensive metrics)
            for col in stat_cols:
                home_row[f"OPP_{col}"] = row.get(f"AWAY_{col}", np.nan)
                away_row[f"OPP_{col}"] = row.get(f"HOME_{col}", np.nan)

            home_records.append(home_row)
            away_records.append(away_row)

        all_records = pd.DataFrame(home_records + away_records)
        all_records = all_records.sort_values("Date")

        # Compute rolling averages
        rolling_cols = stat_cols + [f"OPP_{c}" for c in stat_cols]
        rolling_cols += ["Win", "PointDiff"]

        rolling_stats = {}
        for team in all_records["Team"].unique():
            team_data = all_records[
                all_records["Team"] == team
            ].copy()

            for col in rolling_cols:
                # shift(1) — exclude current game
                team_data[f"avg_{col}"] = (
                    team_data[col]
                    .shift(1)
                    .rolling(window=self.window, min_periods=5)
                    .mean()
                )

            # Form: win percentage over last N games
            team_data["Form"] = (
                team_data["Win"]
                .shift(1)
                .rolling(window=self.window, min_periods=5)
                .mean()
            )

            # Streak: current win/loss streak
            team_data["Streak"] = self._compute_streak(
                team_data["Win"].shift(1)
            )

            rolling_stats[team] = team_data

        return pd.concat(rolling_stats.values())

    @staticmethod
    def _compute_streak(wins: pd.Series) -> pd.Series:
        """Compute current winning (+) / losing (-) streak."""
        streak = []
        current = 0
        for w in wins:
            if pd.isna(w):
                streak.append(0)
                continue
            if w == 1:
                current = max(1, current + 1)
            else:
                current = min(-1, current - 1)
            streak.append(current)
        return pd.Series(streak, index=wins.index)

    def build_match_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Join home and away team statistics
        for each game.
        """
        team_stats = self.compute_team_stats(df)

        stat_features = [
            c for c in team_stats.columns if c.startswith("avg_")
        ]
        stat_features += ["Form", "Streak"]

        features_list = []

        for idx, match in df.iterrows():
            home = match["HOME_TEAM"]
            away = match["AWAY_TEAM"]
            date = match["GAME_DATE"]

            home_stats = team_stats[
                (team_stats["Team"] == home)
                & (team_stats["Date"] == date)
                & (team_stats["IsHome"] == 1)
            ]
            away_stats = team_stats[
                (team_stats["Team"] == away)
                & (team_stats["Date"] == date)
                & (team_stats["IsHome"] == 0)
            ]

            if home_stats.empty or away_stats.empty:
                continue

            row = {"match_idx": idx}
            for feat in stat_features:
                h_val = home_stats[feat].values[0]
                a_val = away_stats[feat].values[0]
                row[f"home_{feat}"] = h_val
                row[f"away_{feat}"] = a_val
                # Difference — one of the strongest features
                row[f"diff_{feat}"] = h_val - a_val

            features_list.append(row)

        features_df = pd.DataFrame(features_list).set_index("match_idx")
        result = df.join(features_df, how="inner")
        return result.dropna(
            subset=[c for c in features_df.columns]
        )


# === Usage ===
engineer = NBAFeatureEngineer(window=10)
featured_data = engineer.build_match_features(clean_data)
print(f"Games with features: {len(featured_data)}")
print(f"Number of features: "
      f"{len([c for c in featured_data.columns if c.startswith(('home_', 'away_', 'diff_'))])}")
Claude for Contextual Feature Generation
python
import anthropic
import json
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()  # key from ANTHROPIC_API_KEY


def claude_analyze_nba_matchup(
    home_team: str,
    away_team: str,
    home_form: dict,
    away_form: dict,
) -> dict:
    """
    Claude evaluates contextual factors of an NBA game
    that are hard to extract from numerical data.
    """
    prompt = f"""You are an expert NBA analyst. Analyze the upcoming game
and return ONLY JSON (no markdown, no comments) with the following scores
on a scale from 0.0 to 1.0:

Game: {home_team} (home) vs {away_team} (away)

{home_team} stats over last 10 games:
- Avg points: {home_form.get('avg_PTS', 'N/A'):.1f}
- Avg points allowed: {home_form.get('avg_OPP_PTS', 'N/A'):.1f}
- Net Rating: {home_form.get('avg_NET_RTG', 'N/A'):.1f}
- FG%: {home_form.get('avg_FG_PCT', 'N/A'):.1%}
- 3PT%: {home_form.get('avg_FG3_PCT', 'N/A'):.1%}
- Form (Win%): {home_form.get('Form', 'N/A'):.1%}
- Streak: {home_form.get('Streak', 'N/A')}

{away_team} stats over last 10 games:
- Avg points: {away_form.get('avg_PTS', 'N/A'):.1f}
- Avg points allowed: {away_form.get('avg_OPP_PTS', 'N/A'):.1f}
- Net Rating: {away_form.get('avg_NET_RTG', 'N/A'):.1f}
- FG%: {away_form.get('avg_FG_PCT', 'N/A'):.1%}
- 3PT%: {away_form.get('avg_FG3_PCT', 'N/A'):.1%}
- Form (Win%): {away_form.get('Form', 'N/A'):.1%}
- Streak: {away_form.get('Streak', 'N/A')}

Return JSON strictly in this format:
{{
    "home_offense_strength": <float>,
    "home_defense_strength": <float>,
    "away_offense_strength": <float>,
    "away_defense_strength": <float>,
    "home_momentum": <float>,
    "away_momentum": <float>,
    "pace_mismatch": <float>,
    "upset_probability": <float>,
    "home_win_confidence": <float>,
    "blowout_likelihood": <float>,
    "reasoning": "<brief explanation in 1-2 sentences>"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])
        return {}


# === Example usage ===
home_form_example = {
    "avg_PTS": 115.2, "avg_OPP_PTS": 108.5,
    "avg_NET_RTG": 6.7, "avg_FG_PCT": 0.478,
    "avg_FG3_PCT": 0.372, "Form": 0.7, "Streak": 3,
}
away_form_example = {
    "avg_PTS": 108.8, "avg_OPP_PTS": 112.1,
    "avg_NET_RTG": -3.3, "avg_FG_PCT": 0.451,
    "avg_FG3_PCT": 0.341, "Form": 0.4, "Streak": -2,
}

analysis = claude_analyze_nba_matchup(
    home_team="BOS",
    away_team="MIA",
    home_form=home_form_example,
    away_form=away_form_example,
)
print(json.dumps(analysis, indent=2, ensure_ascii=False))
Adding Sportsbook Lines as Features
In the NBA sportsbooks set spread (handicap) and moneyline (winner). Spread  one of the strongest predictors. because он already содержит агрегированную expertизу рынка.
python
def add_spread_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert sportsbook lines to probabilities.
    
    In the NBA the line format is specific:
    - Spread: home team -5.5 means they 
      must win by more than 5.5 points
    - Moneyline: -200 (favorite), +170 (underdog)
    """
    df = df.copy()

    # If spread data is available (from external source)
    if "SPREAD" in df.columns:
        # Spread → implied win probability
        # Empirical formula: P(win) ≈ Φ(spread / 13.5)
        # where 13.5 is the standard deviation of margin of victory in the NBA
        from scipy.stats import norm
        df["spread_prob_home"] = norm.cdf(
            -df["SPREAD"] / 13.5
        )
        df["spread_prob_away"] = 1 - df["spread_prob_home"]

    # If moneyline is available
    if "ML_HOME" in df.columns and "ML_AWAY" in df.columns:
        def ml_to_prob(ml):
            """Convert American odds to probability."""
            if ml < 0:
                return abs(ml) / (abs(ml) + 100)
            else:
                return 100 / (ml + 100)

        df["ml_prob_home"] = df["ML_HOME"].apply(ml_to_prob)
        df["ml_prob_away"] = df["ML_AWAY"].apply(ml_to_prob)

        # Normalization (remove margin)
        total = df["ml_prob_home"] + df["ml_prob_away"]
        df["norm_prob_home"] = df["ml_prob_home"] / total
        df["norm_prob_away"] = df["ml_prob_away"] / total

        # Probability difference
        df["odds_spread"] = df["norm_prob_home"] - df["norm_prob_away"]

    return df


featured_data = add_spread_features(featured_data)
Advanced Feature Engineering: Four Factors, ELO & Fatigue
Dean Oliver's Four Factors
Four Factors are the foundation of basketball analytics. They explain ~95% of the variance in team outcomes.
python
def compute_four_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dean Oliver's Four Factors - key metrics
    of basketball team efficiency:
    
    1. eFG% (Effective FG%) = (FGM + 0.5 * FG3M) / FGA
       Accounts for three-pointers being worth more.
       
    2. TOV% (Turnover Rate) = TOV / (FGA + 0.44 * FTA + TOV)
       Share of possessions ending in turnovers.
       
    3. ORB% (Offensive Rebound Rate) = OREB / (OREB + OPP_DREB)
       Share of offensive rebounds.
       
    4. FT Rate = FTM / FGA
       Free throw rate efficiency.
    """
    df = df.copy()

    for prefix, opp_prefix in [("HOME", "AWAY"), ("AWAY", "HOME")]:
        # 1. eFG%
        df[f"{prefix}_eFG_PCT"] = (
            (df[f"{prefix}_FGM"] + 0.5 * df[f"{prefix}_FG3M"])
            / df[f"{prefix}_FGA"].replace(0, np.nan)
        )

        # 2. TOV%
        df[f"{prefix}_TOV_PCT"] = (
            df[f"{prefix}_TOV"]
            / (
                df[f"{prefix}_FGA"]
                + 0.44 * df[f"{prefix}_FTA"]
                + df[f"{prefix}_TOV"]
            ).replace(0, np.nan)
        )

        # 3. ORB%
        df[f"{prefix}_ORB_PCT"] = (
            df[f"{prefix}_OREB"]
            / (
                df[f"{prefix}_OREB"] + df[f"{opp_prefix}_DREB"]
            ).replace(0, np.nan)
        )

        # 4. FT Rate
        df[f"{prefix}_FT_RATE"] = (
            df[f"{prefix}_FTM"]
            / df[f"{prefix}_FGA"].replace(0, np.nan)
        )

        # True Shooting %
        df[f"{prefix}_TS_PCT"] = (
            df[f"{prefix}_PTS"]
            / (2 * (
                df[f"{prefix}_FGA"]
                + 0.44 * df[f"{prefix}_FTA"]
            )).replace(0, np.nan)
        )

        # Assist Ratio
        df[f"{prefix}_AST_RATIO"] = (
            df[f"{prefix}_AST"]
            / df[f"{prefix}_FGM"].replace(0, np.nan)
        )

    return df


featured_data = compute_four_factors(featured_data)
ELO Ratings for the NBA
python
class NBAELO:
    """
    ELO ratings for NBA teams.
    
    Adapted for basketball:
    - K=20 (basketball is more predictable,
      82 games per season → slower adaptation is needed)
    - Home advantage = 100 ELO points (~3.5 points on the court)
    - Margin of victory multiplier accounts for point differential
    - Regression to mean between seasons
    """

    def __init__(self, k: int = 20, home_advantage: int = 100):
        self.k = k
        self.home_advantage = home_advantage
        self.ratings: dict[str, float] = {}

    def get_rating(self, team: str) -> float:
        return self.ratings.setdefault(team, 1500.0)

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def margin_multiplier(self, point_diff: int,
                           elo_diff: float) -> float:
        """
        Multiplier for difference in points.
        FiveThirtyEight formula:
        M = ((abs(MOV) + 3)^0.8) / (7.5 + 0.006 * elo_diff)
        """
        mov = abs(point_diff)
        return ((mov + 3) ** 0.8) / (7.5 + 0.006 * abs(elo_diff))

    def update(self, home: str, away: str,
               home_pts: int, away_pts: int) -> tuple[float, float]:
        """Update ratings after a game."""
        r_home = self.get_rating(home) + self.home_advantage
        r_away = self.get_rating(away)

        e_home = self.expected_score(r_home, r_away)

        # Actual result
        s_home = 1.0 if home_pts > away_pts else 0.0

        # Multiplier for difference in points
        elo_diff = r_home - r_away
        m = self.margin_multiplier(home_pts - away_pts, elo_diff)

        self.ratings[home] += self.k * m * (s_home - e_home)
        self.ratings[away] += self.k * m * ((1 - s_home) - (1 - e_home))

        return self.ratings[home], self.ratings[away]

    def season_reset(self, regression_factor: float = 0.75):
        """
        Regression to mean between seasons.
        NBA: ~25% regression (factor=0.75).
        """
        mean_elo = np.mean(list(self.ratings.values()))
        for team in self.ratings:
            self.ratings[team] = (
                regression_factor * self.ratings[team]
                + (1 - regression_factor) * mean_elo
            )

    def compute_elo_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Iterate through all games chronologically,
        updating ELO after each one.
        """
        df = df.sort_values("GAME_DATE").copy()
        elo_features = []
        current_season = None

        for _, row in df.iterrows():
            # Regression between seasons
            season = row.get("Season", "")
            if current_season and season != current_season:
                self.season_reset()
            current_season = season

            home = row["HOME_TEAM"]
            away = row["AWAY_TEAM"]

            r_home = self.get_rating(home)
            r_away = self.get_rating(away)

            e_home = self.expected_score(
                r_home + self.home_advantage, r_away
            )

            elo_features.append({
                "elo_home": r_home,
                "elo_away": r_away,
                "elo_diff": r_home - r_away,
                "elo_expected_home": e_home,
                "elo_expected_away": 1 - e_home,
            })

            # Update AFTER saving pre-match ratings
            if (pd.notna(row.get("HOME_PTS"))
                    and pd.notna(row.get("AWAY_PTS"))):
                self.update(home, away,
                            int(row["HOME_PTS"]),
                            int(row["AWAY_PTS"]))

        return pd.concat(
            [df.reset_index(drop=True),
             pd.DataFrame(elo_features)],
            axis=1,
        )


# === Usage ===
elo_system = NBAELO(k=20, home_advantage=100)
featured_data = elo_system.compute_elo_features(featured_data)
print(f"Top 5 teams by ELO:")
top_teams = sorted(elo_system.ratings.items(),
                   key=lambda x: -x[1])[:5]
for team, rating in top_teams:
    print(f"  {team:5s}  {rating:.0f}")
Fatigue Factor & Back-to-Back
Back-to-back (two games in two days) - one of the most significant contextual factors in the NBA. Statistically, teams lose ~5% more often in the second game of a back-to-back.
python
def compute_nba_fatigue_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fatigue features for NBA:
    - Back-to-back (second game over 2 days)
    - 3-in-4 (three games over 4 days)
    - Days rest
    - Travel distance (proxy via time zones)
    """
    df = df.sort_values("GAME_DATE").copy()

    rest_days_home = []
    rest_days_away = []
    last_match: dict[str, pd.Timestamp] = {}

    for _, row in df.iterrows():
        home = row["HOME_TEAM"]
        away = row["AWAY_TEAM"]
        date = row["GAME_DATE"]

        for team, rest_list in [(home, rest_days_home),
                                 (away, rest_days_away)]:
            if team in last_match:
                delta = (date - last_match[team]).days
                rest_list.append(min(delta, 14))
            else:
                rest_list.append(3)  # default for first games

        last_match[home] = date
        last_match[away] = date

    df["home_rest_days"] = rest_days_home
    df["away_rest_days"] = rest_days_away
    df["rest_advantage"] = df["home_rest_days"] - df["away_rest_days"]

    # Back-to-back: 1 day rest
    df["home_b2b"] = (df["home_rest_days"] == 1).astype(int)
    df["away_b2b"] = (df["away_rest_days"] == 1).astype(int)

    # 3-in-4: ≤1 day rest with high load
    df["home_fatigued"] = (df["home_rest_days"] <= 1).astype(int)
    df["away_fatigued"] = (df["away_rest_days"] <= 1).astype(int)

    # B2B advantage: one team on B2B, the other — not
    df["b2b_advantage_home"] = (
        df["away_b2b"] - df["home_b2b"]
    )

    return df


featured_data = compute_nba_fatigue_features(featured_data)
 Head-to-Head 
python
def compute_h2h_features(df: pd.DataFrame,
                          n_last: int = 5) -> pd.DataFrame:
    """
    Head-to-head statistics between teams.
    In the NBA some matchups have persistent patterns
    (e.g., matchup advantages based on play style).
    """
    df = df.sort_values("GAME_DATE").copy()
    h2h_features = []

    for idx, row in df.iterrows():
        home = row["HOME_TEAM"]
        away = row["AWAY_TEAM"]
        date = row["GAME_DATE"]

        prev = df[
            (df["GAME_DATE"] < date)
            & (
                ((df["HOME_TEAM"] == home) & (df["AWAY_TEAM"] == away))
                | ((df["HOME_TEAM"] == away) & (df["AWAY_TEAM"] == home))
            )
        ].tail(n_last)

        if len(prev) < 2:
            h2h_features.append({
                "h2h_home_wins": np.nan,
                "h2h_avg_point_diff": np.nan,
                "h2h_avg_total_pts": np.nan,
            })
            continue

        home_wins = 0
        total_diff = 0
        total_pts = 0

        for _, p in prev.iterrows():
            game_total = p["HOME_PTS"] + p["AWAY_PTS"]
            total_pts += game_total

            if p["HOME_TEAM"] == home:
                if p["HOME_WIN"] == 1:
                    home_wins += 1
                total_diff += p["HOME_PTS"] - p["AWAY_PTS"]
            else:
                if p["HOME_WIN"] == 0:
                    home_wins += 1
                total_diff += p["AWAY_PTS"] - p["HOME_PTS"]

        n = len(prev)
        h2h_features.append({
            "h2h_home_wins": home_wins / n,
            "h2h_avg_point_diff": total_diff / n,
            "h2h_avg_total_pts": total_pts / n,
        })

    h2h_df = pd.DataFrame(h2h_features, index=df.index)
    return pd.concat([df, h2h_df], axis=1)


featured_data = compute_h2h_features(featured_data)
print(f"Total features: "
      f"{len([c for c in featured_data.columns if c not in ['GAME_DATE', 'HOME_TEAM', 'AWAY_TEAM', 'HOME_WIN', 'Season', 'GAME_ID']])}")
Polymarket Integration: Prediction Market as Signal Source
Polymarket is a decentralized prediction market on the Polygon blockchain. For the NBA, markets feature high liquidity and active trading volumes. Key differences from sportsbooks:
| Parameter | Sportsbook (DraftKings) | Polymarket |
|---|---|---|
| Pricing mechanism | Algorithm + traders | Free market (CLOB) |
| Margin | 4-8% vig/juice | ~1-2% (exchange spreads) |
| Participants | Mass audience | Crypto traders, quants |
| Reaction to news | Minutes | Seconds |
| Signal | Aggregated expertise + margin | Pure crowd intelligence |
When Polymarket and the sportsbook diverge - that's a potential edge. In the NBA this is especially valuable because lines move quickly due to injury reports (for example, a star player decides to rest an hour before the game).
Connecting to the Polymarket Gamma API
python
import requests
import json
import time
from dataclasses import dataclass

GAMMA_API = "https://gamma-api.polymarket.com"


@dataclass
class PolymarketOdds:
    """Structure for storing Polymarket probabilities."""
    home_win: float
    away_win: float
    liquidity: float
    volume_24h: float
    market_slug: str
    last_updated: str


class PolymarketClient:
    """
    Client for fetching NBA markets from Polymarket.
    Gamma API — public REST API, no auth required.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36"
        )
    }

    NBA_KEYWORDS = [
        "nba", "basketball", "lakers", "celtics", "warriors",
        "bucks", "nuggets", "76ers", "knicks", "heat",
        "cavaliers", "thunder", "timberwolves", "mavericks",
        "suns", "nets", "clippers", "hawks", "bulls",
        "nba finals", "nba playoffs", "nba champion",
    ]

    def search_nba_markets(self, limit: int = 200) -> list[dict]:
        """Search for NBA markets on Polymarket."""
        all_markets = []
        offset = 0

        while offset < limit:
            try:
                resp = requests.get(
                    f"{GAMMA_API}/markets",
                    params={
                        "active": "true",
                        "closed": "false",
                        "limit": 50,
                        "offset": offset,
                    },
                    headers=self.HEADERS,
                    timeout=15,
                )
                resp.raise_for_status()
                markets = resp.json()

                if not markets:
                    break

                for market in markets:
                    question = market.get("question", "").lower()
                    description = market.get("description", "").lower()
                    text = question + " " + description

                    if any(kw in text for kw in self.NBA_KEYWORDS):
                        all_markets.append(market)

                offset += 50
                time.sleep(0.5)

            except requests.RequestException as e:
                print(f"  ⚠ Request error: {e}")
                break

        print(f"  ✓ Found {len(all_markets)} NBA markets")
        return all_markets

    def extract_match_odds(self, market: dict) -> PolymarketOdds | None:
        """
        Extract probability from market data.
        NBA markets are usually binary (Win/Lose, no draw).
        """
        try:
            outcomes = market.get("outcomes", [])
            prices_raw = market.get("outcomePrices", "[]")

            if isinstance(prices_raw, str):
                prices = json.loads(prices_raw)
            else:
                prices = prices_raw

            if len(prices) < 2:
                return None

            prices = [float(p) for p in prices]

            return PolymarketOdds(
                home_win=prices[0],
                away_win=prices[1],
                liquidity=float(market.get("liquidity", 0) or 0),
                volume_24h=float(market.get("volume24hr", 0) or 0),
                market_slug=market.get("slug", ""),
                last_updated=market.get("updatedAt", ""),
            )

        except (ValueError, IndexError, KeyError) as e:
            print(f"  ⚠ Could not extract prices: {e}")
            return None


# === Usage ===
poly_client = PolymarketClient()
nba_markets = poly_client.search_nba_markets(limit=200)

for market in nba_markets[:5]:
    odds = poly_client.extract_match_odds(market)
    if odds:
        print(f"\n  📊 {market['question']}")
        print(f"     Home: {odds.home_win:.1%} | "
              f"Away: {odds.away_win:.1%}")
        print(f"     Liquidity: ${odds.liquidity:,.0f} | "
              f"24h Vol: ${odds.volume_24h:,.0f}")
Retrieving Historical Prices
python
class PolymarketHistorical:
    """
    Retrieve historical prices for backtesting.
    """

    CLOB_API = "https://clob.polymarket.com"

    def get_price_history(
        self, token_id: str, interval: str = "1d",
        fidelity: int = 60,
    ) -> pd.DataFrame:
        try:
            resp = requests.get(
                f"{self.CLOB_API}/prices-history",
                params={
                    "market": token_id,
                    "interval": interval,
                    "fidelity": fidelity,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data or "history" not in data:
                return pd.DataFrame()

            df = pd.DataFrame(data["history"])
            df["timestamp"] = pd.to_datetime(df["t"], unit="s")
            df["price"] = df["p"].astype(float)
            return df[["timestamp", "price"]].sort_values("timestamp")

        except requests.RequestException as e:
            print(f"  ⚠ Error: {e}")
            return pd.DataFrame()

    def get_orderbook_snapshot(self, token_id: str) -> dict:
        """
        Snapshot order book — liquidity depth.
        NBA markets usually have high liquidity,
        → more reliable signal.
        """
        try:
            resp = requests.get(
                f"{self.CLOB_API}/book",
                params={"token_id": token_id},
                timeout=15,
            )
            resp.raise_for_status()
            book = resp.json()

            bids = book.get("bids", [])
            asks = book.get("asks", [])

            total_bid = sum(float(b.get("size", 0)) for b in bids)
            total_ask = sum(float(a.get("size", 0)) for a in asks)

            best_bid = float(bids[0]["price"]) if bids else 0
            best_ask = float(asks[0]["price"]) if asks else 1
            spread = best_ask - best_bid
            midpoint = (best_bid + best_ask) / 2

            return {
                "midpoint": midpoint,
                "spread": spread,
                "spread_pct": spread / midpoint if midpoint > 0 else 0,
                "bid_depth_usd": total_bid,
                "ask_depth_usd": total_ask,
                "total_depth": total_bid + total_ask,
                "imbalance": (
                    (total_bid - total_ask) / (total_bid + total_ask)
                    if (total_bid + total_ask) > 0 else 0
                ),
            }

        except (requests.RequestException, IndexError, ValueError):
            return {}
Combining Three Probability Layers
python
class TripleLayerFeatures:
    """
    Combining three layers for NBA:
    1. Sportsbook (DraftKings/FanDuel) — moneyline/spread
    2. Polymarket — crowd intelligence
    3. ML model — our own score
    
    NBA-specific: binary market (Win/Lose),
    so we work with two outcomes instead of three.
    """

    @staticmethod
    def compute_divergence_features(
        sportsbook_probs: dict,
        polymarket_probs: dict,
        ml_probs: dict | None = None,
    ) -> dict:
        features = {}

        # Raw probability
        for prefix, probs in [("sb", sportsbook_probs),
                               ("poly", polymarket_probs)]:
            features[f"{prefix}_prob_home"] = probs.get("home", 0)
            features[f"{prefix}_prob_away"] = probs.get("away", 0)

        # KL divergence
        epsilon = 1e-6
        kl_div = 0
        for key in ["home", "away"]:
            p = max(sportsbook_probs.get(key, epsilon), epsilon)
            q = max(polymarket_probs.get(key, epsilon), epsilon)
            kl_div += p * np.log(p / q)
        features["kl_div_sb_poly"] = kl_div

        # Absolute divergences
        for key in ["home", "away"]:
            sb = sportsbook_probs.get(key, 0)
            poly = polymarket_probs.get(key, 0)
            features[f"divergence_{key}"] = sb - poly
            features[f"abs_divergence_{key}"] = abs(sb - poly)

        features["max_divergence"] = max(
            features["abs_divergence_home"],
            features["abs_divergence_away"],
        )

        # Source consensus
        sb_fav = max(sportsbook_probs, key=sportsbook_probs.get)
        poly_fav = max(polymarket_probs, key=polymarket_probs.get)
        features["sources_agree"] = int(sb_fav == poly_fav)

        # Blended probabilities
        for key in ["home", "away"]:
            features[f"blended_prob_{key}"] = (
                0.5 * sportsbook_probs.get(key, 0)
                + 0.5 * polymarket_probs.get(key, 0)
            )

        # Triple layer
        if ml_probs:
            for key in ["home", "away"]:
                ml = ml_probs.get(key, 0)
                sb = sportsbook_probs.get(key, 0)
                poly = polymarket_probs.get(key, 0)

                features[f"ml_prob_{key}"] = ml
                features[f"ml_vs_sb_{key}"] = ml - sb
                features[f"ml_vs_poly_{key}"] = ml - poly
                features[f"triple_blend_{key}"] = (
                    0.40 * ml + 0.35 * poly + 0.25 * sb
                )

            ml_fav = max(ml_probs, key=ml_probs.get)
            features["all_three_agree"] = int(
                sb_fav == poly_fav == ml_fav
            )

        return features


# === Example ===
sportsbook = {"home": 0.62, "away": 0.38}
polymarket = {"home": 0.58, "away": 0.42}
ml_probs = {"home": 0.65, "away": 0.35}

triple_features = TripleLayerFeatures.compute_divergence_features(
    sportsbook_probs=sportsbook,
    polymarket_probs=polymarket,
    ml_probs=ml_probs,
)
print("=== Triple Layer Features (NBA) ===")
for k, v in triple_features.items():
    print(f"  {k:30s} = {v:.4f}")
Visualize divergences
python
def plot_nba_divergence(matches: list[dict], figsize=(12, 6)):
    """
    Scatter plot: sportsbook vs Polymarket for NBA.
    Binary market → one chart instead of three.
    """
    fig, ax = plt.subplots(figsize=figsize)

    sb_probs = [m["sb_home"] for m in matches]
    poly_probs = [m["poly_home"] for m in matches]

    ax.scatter(sb_probs, poly_probs, alpha=0.6,
               color="#e67e22", edgecolors="white", s=80)

    ax.plot([0, 1], [0, 1], "k--", alpha=0.3, linewidth=1)

    ax.fill_between([0, 1], [0.03, 1.03], [0, 1],
                    alpha=0.05, color="blue",
                    label="Polymarket above")
    ax.fill_between([0, 1], [0, 1], [-0.03, 0.97],
                    alpha=0.05, color="red",
                    label="Sportsbook above")

    ax.set_xlabel("Sportsbook P(Home Win)", fontsize=12)
    ax.set_ylabel("Polymarket P(Home Win)", fontsize=12)
    ax.set_title(
        "NBA: Sportsbook vs Polymarket\n"
        "Points far from diagonal → potential value",
        fontsize=14,
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig("nba_divergence.png", bbox_inches="tight")
    plt.show()


def plot_triple_layer_bar(
    match_name: str,
    sportsbook: dict,
    polymarket: dict,
    ml_model: dict,
):
    """
    Grouped bar chart: three sources side by side for NBA.
    Simpler radar chart for binary market.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(2)
    width = 0.25
    labels = ["Home Win", "Away Win"]
    keys = ["home", "away"]

    bars1 = ax.bar(x - width, [sportsbook[k] for k in keys],
                    width, label="Sportsbook", color="#3498db")
    bars2 = ax.bar(x, [polymarket[k] for k in keys],
                    width, label="Polymarket", color="#e74c3c")
    bars3 = ax.bar(x + width, [ml_model[k] for k in keys],
                    width, label="ML Model", color="#2ecc71")

    ax.set_ylabel("Probability")
    ax.set_title(f"Triple Layer: {match_name}", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    # Annotations
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.0%}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig("nba_triple_bar.png", bbox_inches="tight")
    plt.show()
Claude Analyzes Divergences
python
def claude_analyze_nba_divergence(
    match: str,
    sportsbook: dict,
    polymarket: dict,
    ml_model: dict,
    poly_liquidity: float,
    poly_volume_24h: float,
) -> str:
    """
    Claude analyzes divergences between three sources
    in the NBA context.
    """
    prompt = f"""You are a senior NBA analyst. You have three sources of
probabilities for games. Analyze divergences.

**Game:** {match}

| Source | Home Win | Away Win |
|---|---|---|
| Sportsbook | {sportsbook['home']:.1%} | {sportsbook['away']:.1%} |
| Polymarket | {polymarket['home']:.1%} | {polymarket['away']:.1%} |
| ML model | {ml_model['home']:.1%} | {ml_model['away']:.1%} |

**Metadata Polymarket:**
- Liquidity: ${poly_liquidity:,.0f}
- 24h volume: ${poly_volume_24h:,.0f}

**Task:**
1. Where are the main divergences and what could they mean?
   (injuries, load management, lineup changes, matchup advantages)
2. Which source should be trusted more and why?
3. Are there signs of insider activity?
   (NBA injury reports come out ~30 min before games)
4. Forecast with confidence level.

Be specific, 5-8 sentences.""""""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
Building the ML Model
Data Preparation
python
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, log_loss,
)


def prepare_model_data(df: pd.DataFrame) -> tuple:
    """
    Prepare data. NBA = binary classification (Win/Loss).
    """
    feature_cols = [
        c for c in df.columns
        if c.startswith(("home_", "away_", "diff_",
                         "elo_", "h2h_", "rest_",
                         "b2b_", "norm_prob_", "odds_spread"))
        and "TEAM" not in c
    ]

    X = df[feature_cols].copy()
    y = df["HOME_WIN"].copy()

    X = X.fillna(X.median())

    print(f"Features: {X.shape[1]}")
    print(f"Games: {X.shape[0]}")
    print(f"Balance: Home Win={y.mean():.1%}, "
          f"Away Win={1-y.mean():.1%}")

    return X, y, feature_cols


X, y, feature_names = prepare_model_data(featured_data)
Model training
python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    VotingClassifier,
)
from xgboost import XGBClassifier


def train_and_evaluate(X, y):
    """
    Train models with TimeSeriesSplit.
    NBA: binary classification → accuracy ~65-72%.
    """
    tscv = TimeSeriesSplit(n_splits=5)
    scaler = StandardScaler()

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=1000, C=0.5,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=8,
            min_samples_leaf=10, random_state=42,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300, max_depth=5,
            learning_rate=0.05, subsample=0.8,
            colsample_bytree=0.8, random_state=42,
            eval_metric="logloss",
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=4,
            learning_rate=0.08, random_state=42,
        ),
    }

    results = {}

    for name, model in models.items():
        fold_accs = []
        fold_lls = []

        for train_idx, test_idx in tscv.split(X):
            X_train = scaler.fit_transform(X.iloc[train_idx])
            X_test = scaler.transform(X.iloc[test_idx])
            y_train = y.iloc[train_idx]
            y_test = y.iloc[test_idx]

            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            proba = model.predict_proba(X_test)

            fold_accs.append(accuracy_score(y_test, preds))
            fold_lls.append(log_loss(y_test, proba))

        results[name] = {
            "accuracy_mean": np.mean(fold_accs),
            "accuracy_std": np.std(fold_accs),
            "log_loss_mean": np.mean(fold_lls),
            "log_loss_std": np.std(fold_lls),
        }

        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"  Accuracy:  {results[name]['accuracy_mean']:.4f} "
              f"± {results[name]['accuracy_std']:.4f}")
        print(f"  Log Loss:  {results[name]['log_loss_mean']:.4f} "
              f"± {results[name]['log_loss_std']:.4f}")

    return results, models


results, models = train_and_evaluate(X, y)
Ensemble
python
def build_ensemble(X, y):
    """Ensemble with soft voting for NBA."""
    scaler = StandardScaler()

    ensemble = VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=1000, C=0.5)),
            ("rf", RandomForestClassifier(
                n_estimators=200, max_depth=8, random_state=42)),
            ("xgb", XGBClassifier(
                n_estimators=300, max_depth=5, learning_rate=0.05,
                random_state=42, eval_metric="logloss")),
        ],
        voting="soft",
        weights=[1, 1, 2],  # XGBoost gets higher weight
    )

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    ensemble.fit(X_train_scaled, y_train)
    preds = ensemble.predict(X_test_scaled)
    proba = ensemble.predict_proba(X_test_scaled)

    print(f"\n{'='*60}")
    print(f"  ENSEMBLE (Soft Voting)")
    print(f"  Accuracy:  {accuracy_score(y_test, preds):.4f}")
    print(f"  Log Loss:  {log_loss(y_test, proba):.4f}")
    print(f"\n{classification_report(y_test, preds, "
          f"target_names=['Away Win', 'Home Win'])}")

    return ensemble, scaler


ensemble_model, scaler = build_ensemble(X, y)
Claude API Integration for Interpretation
Generating a Detailed Prediction
python
def generate_nba_prediction_report(
    home_team: str,
    away_team: str,
    model_proba: dict,
    stats: dict,
) -> str:
    """
    Analytical report on an upcoming NBA game.
    """
    prompt = f"""You are a professional NBA analyst. Based on the data from
ML models and statistics, compose a brief analytical report.

## Data models

Game: **{home_team}** vs **{away_team}**

Probabilities (ML Ensemble):
- Win {home_team}: {model_proba['home_win']:.1%}
- Win {away_team}: {model_proba['away_win']:.1%}

Stats for {home_team} (last 10 games):
- Points (avg): {stats['home_avg_PTS']:.1f}
- Net Rating: {stats['home_avg_NET_RTG']:.1f}
- eFG%: {stats['home_eFG']:.1%}
- TOV%: {stats['home_TOV_PCT']:.1%}
- Form (Win%): {stats['home_Form']:.1%}
- Streak: {stats['home_Streak']}

Stats for {away_team} (last 10 games):
- Points (avg): {stats['away_avg_PTS']:.1f}
- Net Rating: {stats['away_avg_NET_RTG']:.1f}
- eFG%: {stats['away_eFG']:.1%}
- TOV%: {stats['away_TOV_PCT']:.1%}
- Form (Win%): {stats['away_Form']:.1%}
- Streak: {stats['away_Streak']}

## Task
1. Key prediction factors (Four Factors, matchup advantages)
2. Result forecast + expected margin
3. Confidence score (high / medium / low)
4. Potential upset scenarios

Concise and professional.""""""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
Batch Analysis of NBA Slate
python
def analyze_nba_slate(games: list[dict]) -> str:
    """
    Analyze all games of the day in a single Claude call.
    A typical NBA slate = 5-15 games.
    """
    games_text = ""
    for i, g in enumerate(games, 1):
        games_text += f"""
{i}. {g['home']} vs {g['away']}
   ML: Home={g['prob_H']:.0%} | Away={g['prob_A']:.0%}
   ELO: {g['elo_home']:.0f} vs {g['elo_away']:.0f}
   B2B: Home={'Yes' if g.get('home_b2b') else 'No'} | Away={'Yes' if g.get('away_b2b') else 'No'}
"""

    prompt = f"""Analyze the NBA slate. For each game:
- Forecast (winner)
- Confidence (⭐ / ⭐⭐ / ⭐⭐⭐)
- Expected margin
- Brief comment (1 sentence)

Games:
{games_text}

At the end: top 3 best bets from the slate (highest confidence).""""""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
Results Visualization
Model Comparison
python
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns

matplotlib.rcParams["figure.dpi"] = 120
matplotlib.rcParams["font.size"] = 11
sns.set_style("whitegrid")


def plot_model_comparison(results: dict):
    """Model comparison visualization for NBA."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    names = list(results.keys())
    accs = [results[n]["accuracy_mean"] for n in names]
    acc_stds = [results[n]["accuracy_std"] for n in names]
    lls = [results[n]["log_loss_mean"] for n in names]
    ll_stds = [results[n]["log_loss_std"] for n in names]

    colors = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12"]

    bars = axes[0].barh(names, accs, xerr=acc_stds,
                         color=colors, edgecolor="white", linewidth=1.5)
    axes[0].set_xlabel("Accuracy")
    axes[0].set_title("Model Accuracy (NBA, TimeSeriesSplit CV)")
    axes[0].set_xlim(0.5, 0.75)
    for bar, val in zip(bars, accs):
        axes[0].text(val + 0.005, bar.get_y() + bar.get_height()/2,
                     f"{val:.3f}", va="center", fontweight="bold")

    bars = axes[1].barh(names, lls, xerr=ll_stds,
                         color=colors, edgecolor="white", linewidth=1.5)
    axes[1].set_xlabel("Log Loss")
    axes[1].set_title("Log Loss (lower = better)")
    for bar, val in zip(bars, lls):
        axes[1].text(val + 0.005, bar.get_y() + bar.get_height()/2,
                     f"{val:.3f}", va="center", fontweight="bold")

    plt.tight_layout()
    plt.savefig("nba_model_comparison.png", bbox_inches="tight")
    plt.show()
Confusion Matrix
python
def plot_nba_confusion_matrix(y_true, y_pred):
    """Confusion matrix for binary NBA classification."""
    cm = confusion_matrix(y_true, y_pred)
    labels = ["Away Win", "Home Win"]

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Oranges",
        xticklabels=labels, yticklabels=labels,
        ax=ax, linewidths=0.5, linecolor="white",
        annot_kws={"size": 16, "weight": "bold"},
    )
    ax.set_xlabel("Predicted result", fontsize=12)
    ax.set_ylabel("Actual result", fontsize=12)
    ax.set_title("Confusion Matrix — NBA Ensemble", fontsize=14)

    cm_pct = cm / cm.sum(axis=1, keepdims=True)
    for i in range(2):
        for j in range(2):
            ax.text(j + 0.5, i + 0.75,
                    f"({cm_pct[i, j]:.0%})",
                    ha="center", va="center",
                    fontsize=10, color="gray")

    plt.tight_layout()
    plt.savefig("nba_confusion_matrix.png", bbox_inches="tight")
    plt.show()
Feature Importance
python
def plot_feature_importance(model, feature_names, top_n=15):
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        return

    indices = np.argsort(importances)[-top_n:]

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.YlOrRd(np.linspace(0.3, 0.9, top_n))
    ax.barh(range(top_n), importances[indices],
            color=colors, edgecolor="white", linewidth=0.8)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_names[i] for i in indices])
    ax.set_xlabel("Feature Importance")
    ax.set_title(f"NBA: Top-{top_n} Important Features", fontsize=14)

    plt.tight_layout()
    plt.savefig("nba_feature_importance.png", bbox_inches="tight")
    plt.show()
Backtesting & Model Evaluation
Walk-Forward Backtest
python
class WalkForwardBacktest:
    """
    Walk-forward for NBA: train on past games,
    predict the next slate.
    
    step_size=15 ≈ one NBA game day
    (on an average day 5-15 games).
    """

    def __init__(self, model, scaler,
                 initial_train_size: int = 1000,
                 step_size: int = 15):
        self.model = model
        self.scaler = scaler
        self.initial_train_size = initial_train_size
        self.step_size = step_size

    def run(self, X: pd.DataFrame, y: pd.Series) -> dict:
        all_preds = []
        all_proba = []
        all_true = []

        for start in range(self.initial_train_size,
                           len(X) - self.step_size,
                           self.step_size):
            end = start + self.step_size

            X_train = X.iloc[:start]
            y_train = y.iloc[:start]
            X_test = X.iloc[start:end]
            y_test = y.iloc[start:end]

            X_train_s = self.scaler.fit_transform(X_train)
            X_test_s = self.scaler.transform(X_test)

            self.model.fit(X_train_s, y_train)
            preds = self.model.predict(X_test_s)
            proba = self.model.predict_proba(X_test_s)

            all_preds.extend(preds)
            all_proba.extend(proba)
            all_true.extend(y_test.values)

        all_preds = np.array(all_preds)
        all_proba = np.array(all_proba)
        all_true = np.array(all_true)

        acc = accuracy_score(all_true, all_preds)
        ll = log_loss(all_true, all_proba)

        print(f"Walk-Forward NBA Backtest:")
        print(f"  Total predictions: {len(all_preds)}")
        print(f"  Accuracy: {acc:.4f}")
        print(f"  Log Loss: {ll:.4f}")
        print(f"\n{classification_report(all_true, all_preds, "
              f"target_names=['Away Win', 'Home Win'])}")

        return {
            "predictions": all_preds,
            "probabilities": all_proba,
            "actuals": all_true,
            "accuracy": acc,
            "log_loss": ll,
        }


# backtester = WalkForwardBacktest(
#     model=XGBClassifier(n_estimators=300, max_depth=5,
#                         learning_rate=0.05, random_state=42),
#     scaler=StandardScaler(),
#     initial_train_size=1000,
#     step_size=15,
# )
# backtest_results = backtester.run(X, y)
Calibration probabilities
python
def plot_nba_calibration(y_true, y_proba):
    """
    Calibration plot for NBA.
    Binary task → one class (Home Win).
    """
    from sklearn.calibration import calibration_curve

    prob_true, prob_pred = calibration_curve(
        y_true, y_proba[:, 1],
        n_bins=10, strategy="uniform",
    )

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot([0, 1], [0, 1], "k--", label="Perfectly calibrated")
    ax.plot(prob_pred, prob_true, "s-", color="#e67e22",
            label="NBA Model", linewidth=2, markersize=8)

    ax.fill_between(prob_pred, prob_true, prob_pred,
                     alpha=0.1, color="#e67e22")

    ax.set_xlabel("Predicted P(Home Win)")
    ax.set_ylabel("Actual home win fraction")
    ax.set_title("NBA Calibration Curve")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig("nba_calibration.png", bbox_inches="tight")
    plt.show()
Advanced Architecture: Hybrid System
Hybrid ML + Claude + Polymarket for NBA
python
class NBAHybridPredictor:
    """
    NBA prediction hybrid system (Triple Layer):
      ML model (quantitative analysis)
    + Polymarket (crowd intelligence)
    + Claude (qualitative analysis + synthesis)
    
    NBA-specific:
    - Binary classification (no draws)
    - Spread prediction (not only Win/Lose)
    - Injury reports as a critical factor
    """

    def __init__(self, ml_model, scaler, feature_names):
        self.ml_model = ml_model
        self.scaler = scaler
        self.feature_names = feature_names
        self.client = anthropic.Anthropic()
        self.poly_client = PolymarketClient()
        self.triple_layer = TripleLayerFeatures()

    def predict(self, match_features: pd.DataFrame,
                home_team: str, away_team: str,
                polymarket_odds: PolymarketOdds | None = None,
                sportsbook_probs: dict | None = None) -> dict:
        """Full pipeline with three layers."""

        # Step 1: ML prediction
        X_scaled = self.scaler.transform(
            match_features[self.feature_names]
        )
        ml_proba = self.ml_model.predict_proba(X_scaled)[0]
        ml_result = {
            "away_win": float(ml_proba[0]),
            "home_win": float(ml_proba[1]),
        }

        # Step 2: Polymarket
        poly_probs = None
        if polymarket_odds:
            poly_probs = {
                "home": polymarket_odds.home_win,
                "away": polymarket_odds.away_win,
            }

        # Step 3: Sportsbook
        sb_probs = sportsbook_probs or {
            "home": ml_result["home_win"],
            "away": ml_result["away_win"],
        }

        # Step 4: Divergence features
        divergence = {}
        if poly_probs:
            divergence = self.triple_layer.compute_divergence_features(
                sportsbook_probs=sb_probs,
                polymarket_probs=poly_probs,
                ml_probs={
                    "home": ml_result["home_win"],
                    "away": ml_result["away_win"],
                },
            )

        # Step 5: Claude synthesis
        claude_analysis = self._get_claude_synthesis(
            home_team, away_team,
            ml_result, sb_probs, poly_probs,
            divergence, polymarket_odds,
        )

        # Step 6: Combine
        final = self._triple_combine(
            ml_result, sb_probs, poly_probs, claude_analysis,
            poly_liquidity=(
                polymarket_odds.liquidity if polymarket_odds else 0
            ),
        )

        return {
            "match": f"{home_team} vs {away_team}",
            "layers": {
                "ml_model": ml_result,
                "sportsbook": sb_probs,
                "polymarket": poly_probs,
            },
            "divergence_features": divergence,
            "claude_analysis": claude_analysis,
            "final_prediction": final,
        }

    def _get_claude_synthesis(
        self, home, away, ml_proba, sb_probs, poly_probs,
        divergence, poly_odds,
    ) -> dict:
        poly_section = ""
        if poly_probs:
            poly_section = f"""
Polymarket (crowd intelligence):
- Win {home}: {poly_probs['home']:.1%}
- Win {away}: {poly_probs['away']:.1%}
- Liquidity: ${poly_odds.liquidity:,.0f}
- 24h volume: ${poly_odds.volume_24h:,.0f}

KL-divergence (SB vs Poly): {divergence.get('kl_div_sb_poly', 0):.4f}
Source consensus: {'Yes' if divergence.get('all_three_agree') else 'No'}"""

        prompt = f"""You are a senior NBA analyst. Synthesize three sources.

Game: {home} (home) vs {away} (away)

ML model:
- Win {home}: {ml_proba['home_win']:.1%}
- Win {away}: {ml_proba['away_win']:.1%}

Sportsbook:
- Win {home}: {sb_probs['home']:.1%}
- Win {away}: {sb_probs['away']:.1%}
{poly_section}

Return ONLY JSON:
{{
    "confidence": <"high"|"medium"|"low">,
    "adjusted_home_win": <float 0-1>,
    "adjusted_away_win": <float 0-1>,
    "polymarket_trust_level": <"high"|"medium"|"low">,
    "divergence_interpretation": "<what the divergence means>",
    "key_insight": "<main takeaway>",
    "expected_margin": <int, expected point difference>,
    "risk_factor": "<main risk>"
}}"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        text = message.content[0].text.strip()
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            return {"error": "Failed to parse"}

    def _triple_combine(self, ml_result, sb_probs, poly_probs,
                         claude_result, poly_liquidity) -> dict:
        """Adaptive merging for NBA."""
        if "error" in claude_result:
            return {
                "predicted_result": max(ml_result, key=ml_result.get),
                "probabilities": ml_result,
                "source": "ml_only",
            }

        if poly_probs and poly_liquidity > 10_000:
            weights = {"ml": 0.35, "poly": 0.35,
                       "sb": 0.15, "claude": 0.15}
        elif poly_probs and poly_liquidity > 1_000:
            weights = {"ml": 0.40, "poly": 0.20,
                       "sb": 0.20, "claude": 0.20}
        else:
            weights = {"ml": 0.50, "poly": 0.0,
                       "sb": 0.25, "claude": 0.25}

        combined = {}
        for key in ["home_win", "away_win"]:
            ml_key = "home" if key == "home_win" else "away"
            claude_key = f"adjusted_{key}"

            ml_val = ml_result[key]
            sb_val = sb_probs.get(ml_key, ml_val)
            poly_val = poly_probs.get(ml_key, ml_val) if poly_probs else ml_val
            claude_val = claude_result.get(claude_key, ml_val)

            combined[key] = (
                weights["ml"] * ml_val
                + weights["poly"] * poly_val
                + weights["sb"] * sb_val
                + weights["claude"] * claude_val
            )

        total = sum(combined.values())
        combined = {k: v / total for k, v in combined.items()}

        return {
            "predicted_result": max(combined, key=combined.get),
            "probabilities": combined,
            "weights_used": weights,
            "confidence": claude_result.get("confidence", "unknown"),
            "expected_margin": claude_result.get("expected_margin", 0),
            "insight": claude_result.get("key_insight", ""),
            "risk": claude_result.get("risk_factor", ""),
            "source": "triple_hybrid",
        }
Ablation Study
python
class AblationStudy:
    """
    Ablation Study for NBA:
      A) ML model only
      B) ML + sportsbook lines
      C) ML + sportsbook + Polymarket
      D) ML + sportsbook + Polymarket + Claude features
    """

    def __init__(self, base_model, scaler, feature_sets: dict):
        self.base_model = base_model
        self.scaler = scaler
        self.feature_sets = feature_sets

    def run(self, df, y, claude_features=None) -> dict:
        from copy import deepcopy
        tscv = TimeSeriesSplit(n_splits=5)
        results = {}

        for config_name, features in self.feature_sets.items():
            X = df[features].fillna(df[features].median())
            fold_acc, fold_ll = [], []

            for train_idx, test_idx in tscv.split(X):
                model = deepcopy(self.base_model)
                sc = deepcopy(self.scaler)

                X_tr = sc.fit_transform(X.iloc[train_idx])
                X_te = sc.transform(X.iloc[test_idx])

                model.fit(X_tr, y.iloc[train_idx])
                proba = model.predict_proba(X_te)
                preds = model.predict(X_te)

                fold_acc.append(accuracy_score(y.iloc[test_idx], preds))
                fold_ll.append(log_loss(y.iloc[test_idx], proba))

            results[config_name] = {
                "accuracy": np.mean(fold_acc),
                "accuracy_std": np.std(fold_acc),
                "log_loss": np.mean(fold_ll),
                "log_loss_std": np.std(fold_ll),
            }

        return results

    @staticmethod
    def print_results(results: dict):
        print(f"\n{'='*65}")
        print(f"  {'Config':<25s} {'Accuracy':>10s} {'Log Loss':>10s}")
        print(f"{'='*65}")
        baseline_acc = None
        for name, m in sorted(results.items()):
            acc, ll = m["accuracy"], m["log_loss"]
            if baseline_acc is None:
                baseline_acc = acc
                delta = ""
            else:
                diff = acc - baseline_acc
                delta = f"  ({'+' if diff > 0 else ''}{diff:.2%})"
            print(f"  {name:<25s} {acc:>8.4f}±{m['accuracy_std']:.3f}"
                  f"  {ll:>8.4f}{delta}")
        print(f"{'='*65}")
Deployment & Automation
Automated Pipeline
python
import schedule
import time
from datetime import datetime


class NBAPredictionPipeline:
    """
    Automated pipeline for NBA:
    data loading → model update → today's predictions.
    
    NBA slate is usually 7:00–10:00 PM ET,
    so running at 5:00 PM ET yields fresh predictions.
    """

    def __init__(self):
        self.loader = NBADataLoader(
            seasons=["2025-26", "2024-25", "2023-24"]
        )
        self.engineer = NBAFeatureEngineer(window=10)
        self.model = XGBClassifier(
            n_estimators=300, max_depth=5,
            learning_rate=0.05, random_state=42,
            eval_metric="logloss",
        )
        self.scaler = StandardScaler()

    def run_daily(self):
        print(f"\n{'='*60}")
        print(f"  NBA Pipeline: {datetime.now()}")
        print(f"{'='*60}\n")

        # 1. Load data
        raw = self.loader.load_all()
        clean = DataCleaner.clean(raw)
        featured = self.engineer.build_match_features(clean)
        featured = compute_four_factors(featured)
        
        elo = NBAELO(k=20, home_advantage=100)
        featured = elo.compute_elo_features(featured)
        featured = compute_nba_fatigue_features(featured)

        # 2. Training
        X, y, fnames = prepare_model_data(featured)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

        acc = accuracy_score(y, self.model.predict(X_scaled))
        print(f"  Training accuracy: {acc:.4f}")

        # 3. Today's predictions (add via NBA API)
        print(f"  Pipeline completed.")
        return True


# pipeline = NBAPredictionPipeline()
# schedule.every().day.at("17:00").do(pipeline.run_daily)
# while True:
#     schedule.run_pending()
#     time.sleep(60)
Project Structure
nba-ai-predictor/
├── config/
│   └── settings.py              # API keys, parameters
├── data/
│   ├── loader.py                 # NBADataLoader
│   ├── cleaner.py                # DataCleaner
│   └── polymarket.py             # PolymarketClient + Historical
├── features/
│   ├── engineering.py            # NBAFeatureEngineer
│   ├── four_factors.py           # compute_four_factors
│   ├── elo.py                    # NBAELO
│   ├── fatigue.py                # compute_nba_fatigue_features
│   ├── claude_features.py        # Claude-based features
│   ├── spread_features.py        # add_spread_features
│   └── triple_layer.py           # TripleLayerFeatures
├── models/
│   ├── train.py                  # Model training
│   ├── ensemble.py               # Ensemble
│   └── hybrid.py                 # NBAHybridPredictor
├── evaluation/
│   ├── backtest.py               # WalkForwardBacktest
│   ├── ablation.py               # AblationStudy
│   └── metrics.py                # Metrics and charts
├── visualization/
│   ├── plots.py                  # Basic plots
│   └── divergence.py             # Divergence charts
├── pipeline.py                   # NBAPredictionPipeline
├── requirements.txt
└── README.md
Key Takeaways
XGBoost + SHAP is the gold standard (Ouyang et al., 2024: ~70% accuracy). Four Factors explain ~95% of outcomes. The sportsbook baseline (~65–67%) is the bar to beat. GNNs are promising (71.54%) but resource-intensive. Walk-forward validation is mandatory - k-fold allows data leakage from the future.
8:04 AM · Apr 20, 2026
·
707.3K
 Views