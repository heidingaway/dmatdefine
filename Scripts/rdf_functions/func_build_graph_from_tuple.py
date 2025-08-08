from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import SKOS, RDF, DCTERMS
from typing import Any

def build_graph_from_tuple(concepts_data: dict[URIRef, dict[str, Any]],
                      config: dict[str, Any],
                      subject_categories: set[str],
                      terms_to_uri: dict[str, URIRef]) -> Graph:
    """
    Builds a final rdflib Graph from a processed data dictionary and a configuration.

    Args:
        concepts_data (dict[URIRef, dict[str, Any]]): The data structure of concepts,
                                                     labels, and relationships.
        config (dict[str, Any]): A dictionary containing configurable graph properties.
        subject_categories (set[str]): Set of subject category terms.
        terms_to_uri (dict[str, URIRef]): Mapping of all terms to their URI references.

    Returns:
        Graph: The final, populated RDF graph.
    """
    g = Graph()
    
    # Dynamically bind all namespaces from the config dictionary
    for prefix, namespace in config["namespaces"].items():
        g.bind(prefix, namespace)

    # Note: SKOS, RDF, DCTERMS are standard rdflib objects, so we can still use them directly
    # even if they are bound dynamically.
    
    # Use the configurable namespace for the concept scheme URI
    concept_scheme_uri = config["main_namespace"][""]
    g.add((concept_scheme_uri, RDF.type, SKOS.ConceptScheme))
    g.add((concept_scheme_uri, DCTERMS.title, Literal(config["title"], lang=config["default_lang"])))

    print("Building the RDF graph...")
    for subject_uri, data in concepts_data.items():
        if subject_uri in [terms_to_uri[cat] for cat in subject_categories if cat in terms_to_uri]:
            data['type'].append(SKOS.Collection)

        for t in data['type']:
            g.add((subject_uri, RDF.type, t))
        
        g.add((subject_uri, SKOS.inScheme, concept_scheme_uri))
        
        # Add prefLabels
        for lang, label in data['prefLabel'].items():
            g.add((subject_uri, SKOS.prefLabel, Literal(label, lang=lang)))
        
        # Add altLabels
        for alt_label in data['altLabel']:
            g.add((subject_uri, SKOS.altLabel, Literal(alt_label, lang=config["default_lang"])))

        # Add relationships
        for predicate, obj in data['relationships']:
            g.add((subject_uri, predicate, obj))
    
    return g