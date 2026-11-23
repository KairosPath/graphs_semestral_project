"""Transform the MovieLens subset + Wikidata enrichment into RDF (Turtle).

Usage: python build_rdf.py <subset_dir> <out_ttl>
"""
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

MLO = Namespace("http://example.org/movielens/ontology#")
MLR = Namespace("http://example.org/movielens/resource/")
WD = Namespace("http://www.wikidata.org/entity/")

subset, out = Path(sys.argv[1]), Path(sys.argv[2])
movies = pd.read_csv(subset / "movies.csv", encoding="utf-8")
links = pd.read_csv(subset / "links.csv", dtype={"imdbId": str, "tmdbId": "Int64"})
ratings = pd.read_csv(subset / "ratings.csv")
tags = pd.read_csv(subset / "tags.csv", encoding="utf-8")
wikidata = json.loads((subset / "wikidata.json").read_text(encoding="utf-8"))

g = Graph()
for prefix, ns in [("mlo", MLO), ("mlr", MLR), ("wd", WD), ("owl", OWL), ("xsd", XSD)]:
    g.bind(prefix, ns)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def ts(unix):
    return Literal(datetime.fromtimestamp(int(unix), tz=timezone.utc)
                   .strftime("%Y-%m-%dT%H:%M:%SZ"), datatype=XSD.dateTime)


def clean_title(raw):
    """'Matrix, The (1999)' -> ('The Matrix', 1999); drops '(a.k.a. ...)' aliases."""
    m = re.match(r"^(.*)\s+\((\d{4})\)\s*$", raw)
    title, year = m.group(1), int(m.group(2))
    title = re.sub(r"\s*\((a\.k\.a\.[^)]*|[^)]*)\)", "", title).strip()
    art = re.match(r"^(.*), (The|A|An)$", title)
    if art:
        title = f"{art.group(2)} {art.group(1)}"
    return title, year


# ---- Wikidata lookups -------------------------------------------------------
wd_film, wd_runtime = {}, defaultdict(set)
wd_countries, wd_langs = defaultdict(set), defaultdict(set)
countries, languages = {}, {}          # wikidata uri -> (label, iso)
for row in wikidata["movies"]:
    imdb = row["imdb"]
    wd_film[imdb] = row["film"]
    if "duration" in row:
        wd_runtime[imdb].add(round(float(row["duration"])))
    if "country" in row:
        wd_countries[imdb].add(row["country"])
        countries[row["country"]] = (row["countryLabel"], row.get("countryIso"))
    if "lang" in row:
        wd_langs[imdb].add(row["lang"])
        languages[row["lang"]] = (row["langLabel"], row.get("langIso"))

directors = {}                         # wikidata uri -> dict
film_directors = defaultdict(set)
for row in wikidata["directors"]:
    d = directors.setdefault(row["director"], {"name": row["directorLabel"],
                                               "birth": row.get("birth"),
                                               "citizen": set()})
    if "citizen" in row:
        d["citizen"].add(row["citizen"])
        countries[row["citizen"]] = (row["citizenLabel"], row.get("citizenIso"))
    film_directors[row["imdb"]].add(row["director"])


def qid(uri):
    return uri.rsplit("/", 1)[1]


def country_node(uri):
    label, iso = countries[uri]
    return MLR[f"country-{iso.lower() if iso else qid(uri)}"]


def language_node(uri):
    label, iso = languages[uri]
    return MLR[f"language-{iso if iso else qid(uri)}"]


# ---- Countries, languages, directors ---------------------------------------
for uri, (label, iso) in countries.items():
    n = country_node(uri)
    g.add((n, RDF.type, MLO.Country))
    g.add((n, RDFS.label, Literal(label, lang="en")))
    if iso:
        g.add((n, MLO.isoCode, Literal(iso)))
    g.add((n, OWL.sameAs, URIRef(uri)))

for uri, (label, iso) in languages.items():
    n = language_node(uri)
    g.add((n, RDF.type, MLO.Language))
    g.add((n, RDFS.label, Literal(label, lang="en")))
    if iso:
        g.add((n, MLO.isoCode, Literal(iso)))
    g.add((n, OWL.sameAs, URIRef(uri)))

for uri, d in directors.items():
    n = MLR[f"person-{qid(uri)}"]
    g.add((n, RDF.type, MLO.Director))
    g.add((n, MLO.name, Literal(d["name"])))
    if d["birth"]:
        g.add((n, MLO.birthDate, Literal(d["birth"][:10], datatype=XSD.date)))
    for c in sorted(d["citizen"]):
        g.add((n, MLO.citizenOf, country_node(c)))
    g.add((n, OWL.sameAs, URIRef(uri)))

# ---- Genres & movies ---------------------------------------------------------
links = links.set_index("movieId")
for m in movies.itertuples(index=False):
    mid = int(m.movieId)
    node = MLR[f"movie-{mid}"]
    title, year = clean_title(m.title)
    imdb = "tt" + links.loc[mid, "imdbId"].zfill(7)
    g.add((node, RDF.type, MLO.Movie))
    g.add((node, MLO.title, Literal(title)))
    g.add((node, MLO.releaseYear, Literal(year, datatype=XSD.integer)))
    g.add((node, MLO.movieLensId, Literal(mid, datatype=XSD.integer)))
    g.add((node, MLO.imdbId, Literal(imdb)))
    for genre in m.genres.split("|"):
        gn = MLR[f"genre-{slug(genre)}"]
        g.add((gn, RDF.type, MLO.Genre))
        g.add((gn, RDFS.label, Literal(genre, lang="en")))
        g.add((node, MLO.hasGenre, gn))
    if imdb in wd_film:
        g.add((node, OWL.sameAs, URIRef(wd_film[imdb])))
    if wd_runtime[imdb]:
        g.add((node, MLO.runtimeMinutes, Literal(min(wd_runtime[imdb]), datatype=XSD.integer)))
    for c in sorted(wd_countries[imdb]):
        g.add((node, MLO.countryOfOrigin, country_node(c)))
    for lang in sorted(wd_langs[imdb]):
        g.add((node, MLO.originalLanguage, language_node(lang)))
    for d in sorted(film_directors[imdb]):
        g.add((node, MLO.directedBy, MLR[f"person-{qid(d)}"]))

# ---- Users, ratings, tags ---------------------------------------------------
for uid in sorted(set(ratings.userId) | set(tags.userId)):
    u = MLR[f"user-{uid}"]
    g.add((u, RDF.type, MLO.User))
    g.add((u, MLO.movieLensId, Literal(int(uid), datatype=XSD.integer)))

for r in ratings.itertuples(index=False):
    n = MLR[f"rating-{r.userId}-{r.movieId}"]
    g.add((n, RDF.type, MLO.Rating))
    g.add((n, MLO.performedBy, MLR[f"user-{r.userId}"]))
    g.add((n, MLO.concernsMovie, MLR[f"movie-{r.movieId}"]))
    g.add((n, MLO.ratingValue, Literal(f"{r.rating:.1f}", datatype=XSD.decimal)))
    g.add((n, MLO.createdAt, ts(r.timestamp)))

for t in tags.itertuples(index=False):
    label = t.tag.strip().lower()
    tag_node = MLR[f"tag-{slug(label)}"]
    g.add((tag_node, RDF.type, MLO.Tag))
    g.add((tag_node, MLO.tagLabel, Literal(label)))
    n = MLR[f"tagging-{t.userId}-{t.movieId}-{slug(label)}"]
    g.add((n, RDF.type, MLO.TagAssignment))
    g.add((n, MLO.performedBy, MLR[f"user-{t.userId}"]))
    g.add((n, MLO.concernsMovie, MLR[f"movie-{t.movieId}"]))
    g.add((n, MLO.usesTag, tag_node))
    g.add((n, MLO.createdAt, ts(t.timestamp)))

# ---- Serialise grouped by class, so the file reads top-down -----------------
SECTIONS = ["Movie", "Genre", "Director", "Country", "Language", "User",
            "Rating", "TagAssignment", "Tag"]
prefix_lines, body = set(), []
for cls in SECTIONS:
    sub = Graph(namespace_manager=g.namespace_manager)
    members = set(g.subjects(RDF.type, MLO[cls]))
    for s_ in members:
        for triple in g.triples((s_, None, None)):
            sub.add(triple)
    lines = sub.serialize(format="turtle").splitlines()
    prefix_lines |= {l for l in lines if l.startswith("@prefix")}
    rule = "# " + "=" * 76
    body.append(f"{rule}\n#  {cls} ({len(members)} instances)\n{rule}\n\n")
    body.append("\n".join(l for l in lines if not l.startswith("@prefix")).strip() + "\n\n")
header = ("# MovieLens knowledge graph - instance data\n"
          "# Source: MovieLens ml-latest-small (GroupLens) subset + Wikidata enrichment\n"
          "# Generated by scripts/build_rdf.py\n\n")
out.write_text(header + "\n".join(sorted(prefix_lines)) + "\n\n" + "".join(body), encoding="utf-8")
counts = {c: len(set(g.subjects(RDF.type, MLO[c]))) for c in SECTIONS}
print(f"triples={len(g)}", counts)
