from rdflib import Graph, URIRef, RDFS, OWL, RDF
from .rdf_helpers import get_uri_last_part

CORE_LITERAL_PROPERTIES_FOR_NODE_DISPLAY = {
    "birthDate", "nationality", "type", "field", "description",
    "comment", "versionInfo", "label", "name" 
} 

def load_dynamic_predicates(graph: Graph) -> tuple:
    """
    Dynamically loads relationship predicates and metadata predicates from the RDF graph.
    """
    # (Implementation remains the same)
    # The function is self-contained and only needs the 'graph' object.
    # It returns all the predicate sets for other modules to use.
    dynamic_relationship_predicates = set()
    dynamic_metadata_predicates = set()
    dynamic_literal_properties = set(CORE_LITERAL_PROPERTIES_FOR_NODE_DISPLAY)

    # Add common RDF/OWL vocabulary terms to metadata predicates.
    dynamic_metadata_predicates.update({
        get_uri_last_part(str(RDF.type)), 
        get_uri_last_part(str(RDFS.domain)),
        get_uri_last_part(str(RDFS.range)),
        get_uri_last_part(str(OWL.inverseOf)),
        get_uri_last_part(str(OWL.Ontology)),
        get_uri_last_part(str(OWL.ObjectProperty)),
        get_uri_last_part(str(OWL.DatatypeProperty)),
        get_uri_last_part(str(RDFS.label)), 
        get_uri_last_part(str(RDFS.comment)), 
        get_uri_last_part(str(OWL.versionInfo)),
        "isDefinedBy"
    })

    for s, p, o in graph.triples((None, RDF.type, OWL.DatatypeProperty)):
        label_triples = list(graph.triples((s, RDFS.label, None)))
        if label_triples:
            literal_prop_label = get_uri_last_part(str(label_triples[0][2]))
            dynamic_literal_properties.add(literal_prop_label)
        else:
            literal_prop_label = get_uri_last_part(str(s))
            dynamic_literal_properties.add(literal_prop_label)

    for p_uri in graph.predicates():
        predicate_label = get_uri_last_part(str(p_uri))
        if predicate_label not in dynamic_metadata_predicates and \
           predicate_label not in dynamic_literal_properties:
            dynamic_relationship_predicates.add(predicate_label)

    for s, p, o in graph.triples((None, OWL.inverseOf, None)):
        label_s = next((get_uri_last_part(str(l[2])) for l in graph.triples((s, RDFS.label, None))), get_uri_last_part(str(s)))
        label_o = next((get_uri_last_part(str(l[2])) for l in graph.triples((o, RDFS.label, None))), get_uri_last_part(str(o)))
        dynamic_relationship_predicates.add(label_s)
        dynamic_relationship_predicates.add(label_o)
    
    dynamic_relationship_predicates.update({
        "subClassOf", str(RDFS.subClassOf), "creator", "subject", "seeAlso", "hasTopic", "title", "influencedBy", "hasField",
        "defines", "drives", "interactsWith", "delivers", "hasPart", "partOf"
    })
    dynamic_metadata_predicates.update({
        "comment", "versionInfo", "label"
    })
    
    dynamic_relationship_predicates_lower = {p.lower() for p in dynamic_relationship_predicates}
    dynamic_metadata_predicates_lower = {p.lower() for p in dynamic_metadata_predicates}
    dynamic_literal_properties_lower = {p.lower() for p in dynamic_literal_properties}
    
    return (dynamic_relationship_predicates, dynamic_metadata_predicates, dynamic_literal_properties, 
            dynamic_relationship_predicates_lower, dynamic_metadata_predicates_lower, dynamic_literal_properties_lower)