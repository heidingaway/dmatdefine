import re
from rdflib import Graph, URIRef, Literal, RDFS
from urllib.parse import urlparse

def find_label_for_uri(uri: URIRef, graph: Graph) -> str:
    """Finds a human-readable label for a given URI."""
    for _, _, label in graph.triples((uri, RDFS.label, None)):
        if isinstance(label, Literal):
            return str(label)
    return get_uri_last_part(str(uri))

def get_uri_last_part(uri: str) -> str:
    """Helper function to robustly extract the last part of a URI."""
    if ':' in uri and not uri.startswith('http'):
        return uri.split(':', 1)[1]
    
    try:
        parsed_uri = urlparse(uri)
        if parsed_uri.fragment:
            return parsed_uri.fragment
        
        path_parts = parsed_uri.path.split('/')
        label = next((part for part in reversed(path_parts) if part), '')
        if label:
            return label
    except Exception:
        pass
    return uri

def find_uri_for_filename(filename: str, graph: Graph, base_uri: str) -> URIRef:
    """Finds the URI reference in the graph that corresponds to the given filename."""
    normalized_filename = filename.lower().replace(" ", "_").replace("-", "_")
    for s, _, o in graph.triples((None, None, None)):
        if get_uri_last_part(str(s)).lower().replace(" ", "_").replace("-", "_") == normalized_filename:
            return s
        if isinstance(o, URIRef) and get_uri_last_part(str(o)).lower().replace(" ", "_").replace("-", "_") == normalized_filename:
            return o
    return URIRef(f"{base_uri}{normalized_filename}")

def get_subclass_depth(entity_uri: URIRef, graph: Graph, root_classes: set) -> int:
    """Finds the shortest path depth of an entity from a root class."""
    # (Implementation remains the same)
    RDFS_SUBCLASSOF = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    queue = [(entity_uri, 0)]
    visited = set()
    while queue:
        current_uri, depth = queue.pop(0)
        if current_uri in root_classes:
            return depth
        if current_uri in visited:
            continue
        visited.add(current_uri)
        for _, _, super_class in graph.triples((current_uri, RDFS_SUBCLASSOF, None)):
            queue.append((super_class, depth + 1))
    return -1