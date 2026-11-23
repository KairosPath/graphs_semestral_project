"""Select a small, reproducible subset of MovieLens ml-latest-small.

Selection rules (deterministic):
  * movies: the N_MOVIES most-rated movies that have >= 50 ratings and >= MIN_TAGS tags
  * users:  N_USERS "moderately active" users who rated between MIN_COV and
            MAX_COV of the selected movies, spread evenly over that band (so each
            has unrated movies left for recommendation), plus the N_TAGGERS users who tagged them most
  * ratings: every rating by a selected user on a selected movie
  * tags:    every tag by a selected user on a selected movie, capped at
             MAX_TAGS_PER_MOVIE per movie (the most frequently used labels win)

Usage: python select_subset.py <raw_dir> <out_dir>
"""
import sys
from pathlib import Path

import pandas as pd

N_MOVIES = 25
MIN_TAGS = 8
N_USERS = 10
MIN_COV, MAX_COV = 7, 14
N_TAGGERS = 3
MAX_TAGS_PER_MOVIE = 4

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

movies = pd.read_csv(raw / "movies.csv", encoding="utf-8")
ratings = pd.read_csv(raw / "ratings.csv")
tags = pd.read_csv(raw / "tags.csv", encoding="utf-8")
links = pd.read_csv(raw / "links.csv", dtype={"imdbId": str, "tmdbId": "Int64"})

n_ratings = ratings.groupby("movieId").size().rename("n_ratings")
n_tags = tags.groupby("movieId").size().rename("n_tags")
stats = movies.set_index("movieId").join([n_ratings, n_tags]).fillna(0)
movie_ids = (
    stats[(stats.n_ratings >= 50) & (stats.n_tags >= MIN_TAGS)]
    .sort_values(["n_ratings", "title"], ascending=[False, True])
    .head(N_MOVIES)
    .index
)

r_sel = ratings[ratings.movieId.isin(movie_ids)]
t_sel = tags[tags.movieId.isin(movie_ids)]
coverage = r_sel.userId.value_counts().sort_index().sort_values(ascending=False, kind="stable")
top_raters = coverage[(coverage >= MIN_COV) & (coverage <= MAX_COV)]
top_taggers = t_sel.userId.value_counts().sort_index().sort_values(ascending=False, kind="stable")
# spread the pick evenly over the activity band (not just the most active ones)
step = max(1, len(top_raters) // N_USERS)
user_ids = sorted(set(top_raters.index[::step][:N_USERS]) | set(top_taggers.index[:N_TAGGERS]))

r_out = r_sel[r_sel.userId.isin(user_ids)].sort_values(["userId", "movieId"])

t_out = t_sel[t_sel.userId.isin(user_ids)].copy()
t_out["tag"] = t_out.tag.str.strip()
t_out["tag_norm"] = t_out.tag.str.lower()
t_out = t_out.drop_duplicates(["userId", "movieId", "tag_norm"])
# global label popularity -> keep labels that are shared across movies first
popularity = t_out.tag_norm.map(t_out.groupby("tag_norm").movieId.nunique())
t_out = (
    t_out.assign(pop=popularity)
    .sort_values(["movieId", "pop", "timestamp"], ascending=[True, False, True])
    .groupby("movieId")
    .head(MAX_TAGS_PER_MOVIE)
    .drop(columns=["pop"])
    .sort_values(["movieId", "userId", "timestamp"])
)

movies[movies.movieId.isin(movie_ids)].to_csv(out / "movies.csv", index=False)
links[links.movieId.isin(movie_ids)].to_csv(out / "links.csv", index=False)
r_out.to_csv(out / "ratings.csv", index=False)
t_out.drop(columns=["tag_norm"]).to_csv(out / "tags.csv", index=False)

print(f"movies={len(movie_ids)} users={len(user_ids)} ratings={len(r_out)} "
      f"tags={len(t_out)} distinct_tags={t_out.tag_norm.nunique()} "
      f"users_with_tags={t_out.userId.nunique()}")
