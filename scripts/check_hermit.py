"""Check ontology + data with the HermiT reasoner (the default reasoner in Protégé).

Needs Java and `pip install owlready2 rdflib`.
Usage: python check_hermit.py <ontology_ttl> <data_ttl>
"""
import sys
import tempfile
from pathlib import Path

from owlready2 import OwlReadyInconsistentOntologyError, World, sync_reasoner
from rdflib import Graph

g = Graph()
g.parse(sys.argv[1])
g.parse(sys.argv[2])

with tempfile.TemporaryDirectory() as tmp:
    owl_file = Path(tmp) / "kg.owl"
    g.serialize(owl_file, format="xml")       # owlready2 reads RDF/XML
    world = World()
    onto = world.get_ontology("file://" + owl_file.as_posix()).load()
    try:
        with onto:
            sync_reasoner(world, debug=0)
    except OwlReadyInconsistentOntologyError:
        print("HermiT: the ontology with data is INCONSISTENT")
        sys.exit(1)
    unsat = list(world.inconsistent_classes())
    print(f"HermiT: consistent, {len(g)} triples, unsatisfiable classes: {unsat or 'none'}")
    sys.exit(1 if unsat else 0)
