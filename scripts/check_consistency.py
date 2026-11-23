"""Load ontology + data, run OWL 2 RL reasoning (owlrl) and report inconsistencies.

Usage: python check_consistency.py <ontology_ttl> <data_ttl>
"""
import sys

import owlrl
from rdflib import Graph, Namespace, OWL, RDF

MLO = Namespace("http://example.org/movielens/ontology#")
g = Graph()
g.parse(sys.argv[1])
onto_size = len(g)
classes = {c for c in g.subjects(RDF.type, OWL.Class) if str(c).startswith(str(MLO))}
obj = {p for p in g.subjects(RDF.type, OWL.ObjectProperty)}
dat = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty)}
print(f"ontology: {onto_size} triples, {len(classes)} classes, "
      f"{len(obj)} object + {len(dat)} datatype properties")
g.parse(sys.argv[2])
before = len(g)
closure = owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, rdfs_closure=False,
                                 axiomatic_triples=False, datatype_axioms=False)
closure.expand(g)
print(f"asserted triples: {before}, after OWL RL closure: {len(g)}")
errors = [(s, p, o) for s, p, o in g if "error" in str(p).lower() or "error" in str(o).lower()]
nothing = list(g.subjects(RDF.type, OWL.Nothing))
print(f"inconsistency reports: {len(errors)}, owl:Nothing members: {len(nothing)}")
for e in errors[:10]:
    print("  ", e)
print("inferred: Person", len(set(g.subjects(RDF.type, MLO.Person))),
      "| UserActivity", len(set(g.subjects(RDF.type, MLO.UserActivity))))
sys.exit(1 if errors or nothing else 0)
