from rdflib import Graph, URIRef
from .clean_for_mermaid import get_mermaid_safe_label, get_entity_properties_for_mermaid
from .traverse_ttl_to_mermaid import traverse_ttl_to_mermaid
from ..rdf.rdf_helpers import get_uri_last_part

def generate_mermaid_syntax(current_page_title: str, 
                            graph: Graph,
                            RELATIONSHIP_PREDICATES: set,
                            METADATA_PREDICATES: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set,
                            RELATIONSHIP_PREDICATES_LOWER: set,
                            METADATA_PREDICATES_LOWER: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER: set,
                            current_page_full_uri: URIRef,
                            should_skip_inverse_relationships: bool,
                            max_layers: int) -> tuple[str, set]:
    """
    Generates a Mermaid graph syntax string based on a central entity and its relationships.
    """
    predicates = {
        'RELATIONSHIP': RELATIONSHIP_PREDICATES,
        'METADATA': METADATA_PREDICATES,
        'LITERAL_PROPERTIES': LITERAL_PROPERTIES_FOR_NODE_DISPLAY,
        'RELATIONSHIP_LOWER': RELATIONSHIP_PREDICATES_LOWER,
        'METADATA_LOWER': METADATA_PREDICATES_LOWER,
        'LITERAL_PROPERTIES_LOWER': LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER,
    }

    nodes_to_render, edges_to_render = traverse_ttl_to_mermaid(
        current_page_title, graph, predicates, current_page_full_uri,
        should_skip_inverse_relationships, max_layers
    )

    current_page_id = nodes_to_render[str(current_page_full_uri)]["id"]

    mermaid_syntax_lines = ["graph TD"]
    for uri, data in nodes_to_render.items():
        if data['id'] == current_page_id:
            mermaid_syntax_lines.append(f"  {data['id']}[\"{data['label']}{data['props']}\"]:::current-page-node")
        else:
            mermaid_syntax_lines.append(f"  {data['id']}[\"{data['label']}{data['props']}\"]")
    
    for source_id, predicate_label, target_id in edges_to_render:
        mermaid_syntax_lines.append(f"  {source_id}-->|\" {predicate_label} \"|{target_id}")

    final_node_ids = {get_uri_last_part(uri) for uri in nodes_to_render.keys()}
    return "\n".join(mermaid_syntax_lines), final_node_ids