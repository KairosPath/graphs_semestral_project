# MovieLens Knowledge Graph

Semestral project for 4IZ444 Graph-based and relational data (VŠE, winter semester 2026).
Rostislav and Vojta Pardubský.

We took a small part of the [MovieLens](https://grouplens.org/datasets/movielens/latest/) dataset
(movies, ratings, tags), turned it into an RDF knowledge graph and added directors, countries and
languages from Wikidata. Then we wrote SPARQL queries for our competency questions and SHACL shapes
to check the data.

- Report: [`report/MovieLens_Knowledge_Graph_Report.pdf`](report/MovieLens_Knowledge_Graph_Report.pdf)
- Presentation: [`report/MovieLens_KG_Presentation.pdf`](report/MovieLens_KG_Presentation.pdf)

## What is where

| Folder | What's inside |
|---|---|
| `ontology/` | the ontology in Turtle (11 classes, 20 properties) |
| `data/` | the knowledge graph, 1,743 triples |
| `queries/` | 8 queries for the competency questions (`cq1`–`cq8`) and 3 extra ones (`a1`–`a3`), results in `queries/results/` |
| `shacl/` | 4 SHACL shapes, a file with broken test data and the validation reports |
| `scripts/` | Python scripts that build the graph from the CSV files |
| `subset/` | the part of MovieLens we used, plus the Wikidata answers (`wikidata.json`) |
| `report/` | report and presentation as PDF, and the HTML template the report PDF is built from |

## Running it

You need Python 3 with `pandas rdflib pyshacl owlrl owlready2 requests`, and Java with
[Apache Jena](https://jena.apache.org/download/) if you want to run the queries the same way we did.

Rebuild the graph from `subset/` and check it with the reasoners (HermiT and OWL RL):

```
python scripts/build_rdf.py subset data/movielens-data.ttl
python scripts/check_hermit.py ontology/movielens-ontology.ttl data/movielens-data.ttl
python scripts/check_consistency.py ontology/movielens-ontology.ttl data/movielens-data.ttl
```

To pick the subset again, download the original CSV files from
[ml-latest-small](https://github.com/smanihwr/ml-latest-small) into `raw/` and run
`python scripts/select_subset.py raw subset` (and `scripts/fetch_wikidata.py` for the Wikidata part).

Run a query or the SHACL validation with Jena:

```
java -cp "<jena>/lib/*" arq.sparql --data data/movielens-data.ttl --query queries/cq1_top_rated_movies.rq
java -cp "<jena>/lib/*" shacl.shacl validate --shapes shacl/movielens-shapes.ttl --data data/movielens-data.ttl
```

Or in Fuseki: create a dataset, upload the ontology and the data file and paste a query.

## Data and license

The movie data comes from the MovieLens ml-latest-small dataset by GroupLens Research, University of
Minnesota. It may only be used under its own license conditions, which are in
[`MOVIELENS_LICENSE.txt`](MOVIELENS_LICENSE.txt) (no commercial use, and the dataset has to be cited):

> F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context.
> ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19. https://doi.org/10.1145/2827872

Directors, countries and languages come from [Wikidata](https://www.wikidata.org/) (CC0).
