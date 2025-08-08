from rdflib import Graph, URIRef
from rdflib.namespace import SKOS, OWL # OWL for owl:inverseOf if we were to use it directly

def add_inverse_properties(graph: Graph) -> Graph:
    """
    Reviews an RDF graph and adds inverse properties based on common SKOS relationships.

    Args:
        graph (Graph): The rdflib Graph object to modify.

    Returns:
        Graph: The modified graph with inverse properties added.
    """
    # Define a mapping of properties to their inverse properties.
    # This dictionary can be extended with more inverse pairs as needed.
    # Note: For symmetric properties like skos:related, the property is its own inverse.
    inverse_map = {
        SKOS.broader: SKOS.narrower,
        SKOS.narrower: SKOS.broader,
        SKOS.related: SKOS.related, # skos:related is symmetric
        SKOS.hasTopConcept: SKOS.topConceptOf,
        SKOS.topConceptOf: SKOS.hasTopConcept,
        # Add more inverse pairs here if needed, e.g.:
        # URIRef("http://example.org/myvocab/hasPart"): URIRef("http://example.org/myvocab/isPartOf"),
    }

    triples_to_add = []
    
    # Iterate over a copy of the graph's triples to avoid modification issues
    print("Checking for inverse properties to add...")
    for s, p, o in list(graph): # Using list(graph) creates a copy of triples
        if p in inverse_map:
            inverse_predicate = inverse_map[p]
            # Check if the inverse triple already exists to avoid duplicates
            if (o, inverse_predicate, s) not in graph:
                triples_to_add.append((o, inverse_predicate, s))
                # print(f"  Adding inverse: ({o}, {inverse_predicate}, {s})") # Uncomment for verbose output

    if triples_to_add:
        for t in triples_to_add:
            graph.add(t)
        print(f"Added {len(triples_to_add)} inverse triples to the graph.")
    else:
        print("No new inverse triples found to add.")

    return graph