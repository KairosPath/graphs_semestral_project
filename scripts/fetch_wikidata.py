"""Enrich the selected movies with facts from Wikidata, matched by IMDb ID.

For every movie it fetches: Wikidata entity, director(s) (+ birth date and
country of citizenship), country of origin, original language, duration.
Results are cached to JSON so the RDF build is reproducible offline.

Usage: python fetch_wikidata.py <subset_dir> <out_json>
"""
import json
import sys
from pathlib import Path

import pandas as pd
import requests

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "GRD-coursework-movielens-kg/1.0 (educational script)",
           "Accept": "application/sparql-results+json"}

subset, out = Path(sys.argv[1]), Path(sys.argv[2])
links = pd.read_csv(subset / "links.csv", dtype={"imdbId": str})
imdb_values = " ".join(f'"tt{i.zfill(7)}"' for i in links.imdbId)


def run(query):
    r = requests.post(ENDPOINT, data={"query": query}, headers=HEADERS, timeout=120)
    r.raise_for_status()
    return [{k: v["value"] for k, v in b.items()} for b in r.json()["results"]["bindings"]]


movies_q = f"""
SELECT ?imdb ?film ?filmLabel ?duration ?country ?countryLabel ?countryIso ?lang ?langLabel ?langIso WHERE {{
  VALUES ?imdb {{ {imdb_values} }}
  ?film wdt:P345 ?imdb ; wdt:P31/wdt:P279* wd:Q11424 .
  OPTIONAL {{ ?film wdt:P2047 ?duration }}
  OPTIONAL {{ ?film wdt:P495 ?country . OPTIONAL {{ ?country wdt:P297 ?countryIso }} }}
  OPTIONAL {{ ?film wdt:P364 ?lang . OPTIONAL {{ ?lang wdt:P218 ?langIso }} }}
  OPTIONAL {{ ?film rdfs:label ?filmEn FILTER(lang(?filmEn) = "en") }}
  OPTIONAL {{ ?film rdfs:label ?filmMul FILTER(lang(?filmMul) = "mul") }}
  BIND(COALESCE(?filmEn, ?filmMul) AS ?filmLabel)
  OPTIONAL {{ ?country rdfs:label ?countryEn FILTER(lang(?countryEn) = "en") }}
  OPTIONAL {{ ?country rdfs:label ?countryMul FILTER(lang(?countryMul) = "mul") }}
  BIND(COALESCE(?countryEn, ?countryMul) AS ?countryLabel)
  OPTIONAL {{ ?lang rdfs:label ?langEn FILTER(lang(?langEn) = "en") }}
  OPTIONAL {{ ?lang rdfs:label ?langMul FILTER(lang(?langMul) = "mul") }}
  BIND(COALESCE(?langEn, ?langMul) AS ?langLabel)
}}"""

directors_q = f"""
SELECT ?imdb ?director ?directorLabel ?birth ?citizen ?citizenLabel ?citizenIso WHERE {{
  VALUES ?imdb {{ {imdb_values} }}
  ?film wdt:P345 ?imdb ; wdt:P57 ?director .
  OPTIONAL {{ ?director wdt:P569 ?birth }}
  OPTIONAL {{ ?director wdt:P27 ?citizen . OPTIONAL {{ ?citizen wdt:P297 ?citizenIso }} }}
  OPTIONAL {{ ?director rdfs:label ?directorEn FILTER(lang(?directorEn) = "en") }}
  OPTIONAL {{ ?director rdfs:label ?directorMul FILTER(lang(?directorMul) = "mul") }}
  BIND(COALESCE(?directorEn, ?directorMul) AS ?directorLabel)
  OPTIONAL {{ ?citizen rdfs:label ?citizenEn FILTER(lang(?citizenEn) = "en") }}
  OPTIONAL {{ ?citizen rdfs:label ?citizenMul FILTER(lang(?citizenMul) = "mul") }}
  BIND(COALESCE(?citizenEn, ?citizenMul) AS ?citizenLabel)
}}"""

result = {"movies": run(movies_q), "directors": run(directors_q)}
out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
found = {row["imdb"] for row in result["movies"]}
missing = [i for i in links.imdbId if f"tt{i.zfill(7)}" not in found]
print(f"movie rows={len(result['movies'])} director rows={len(result['directors'])} "
      f"matched={len(found)}/{len(links)} missing={missing}")
