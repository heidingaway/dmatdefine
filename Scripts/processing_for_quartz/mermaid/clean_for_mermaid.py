import re
from rdflib import Graph, URIRef, Literal

def get_mermaid_safe_label(text: str) -> str:
    """Sanitizes a string for safe inclusion as a label in Mermaid diagrams."""
    safe_text = str(text)
    # 1. Remove Markdown link syntax
    safe_text = re.sub(r'\[.*?\]\(.*?\)', '', safe_text)
    # 2. Escape double backslashes
    safe_text = safe_text.replace('\\', '\\\\')
    # 3. Escape or replace other special characters
    safe_text = safe_text.replace('"', '\\"')
    safe_text = safe_text.replace('`', "'")
    safe_text = safe_text.replace('\n', '<br>')
    safe_text = safe_text.replace('(', '').replace(')', '')
    safe_text = safe_text.replace('<', '&lt;').replace('>', '&gt;')
    safe_text = safe_text.replace('|', '/')
    safe_text = safe_text.replace('//', '/')
    # 4. Remove any remaining non-printable characters
    safe_text = re.sub(r'[^\x20-\x7E]', '', safe_text)
    # 5. Trim whitespace
    return safe_text.strip()

def get_entity_properties_for_mermaid(graph: Graph, entity_uri: str, 
                                      RELATIONSHIP_PREDICATES: set, 
                                      METADATA_PREDICATES: set, 
                                      LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set) -> str:
    """
    Queries the graph for direct properties of a given entity and formats them
    as plain text for Mermaid node display.
    """
    from ..rdf.rdf_helpers import get_uri_last_part  # Avoids circular import
    properties_list = []
    entity_ref = URIRef(entity_uri)
    for s, p, o in graph.triples((entity_ref, None, None)):
        prop_name = get_uri_last_part(str(p))
        prop_value = get_uri_last_part(str(o))
        if prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, Literal):
            properties_list.append(f"+ {prop_name}: {prop_value}")
        elif prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, URIRef):
            if prop_name not in RELATIONSHIP_PREDICATES and prop_name not in METADATA_PREDICATES:
                properties_list.append(f"+ {prop_name}: {prop_value}")
    if properties_list:
        return "<br>" + "<br>".join(properties_list)
    return ""