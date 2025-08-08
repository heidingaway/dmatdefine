import re
from rdflib import Graph, URIRef, Literal
from ..rdf.rdf_helpers import get_uri_last_part, find_label_for_uri
from .clean_for_mermaid import get_entity_properties_for_mermaid, get_mermaid_safe_label

def traverse_ttl_to_mermaid(current_page_title: str, graph: Graph, predicates: dict,
                            current_page_full_uri: URIRef,
                            should_skip_inverse_relationships: bool, max_layers: int) -> tuple[dict, set]:
    """
    Traverses the RDF graph to build a dictionary of nodes and a set of edges.
    """
    nodes_to_render = {}
    edges_to_render = set()
    current_layer_nodes = {str(current_page_full_uri)}
    uri_to_id = {}

    def get_or_create_node_id(uri: str, label: str) -> str:
        if uri not in uri_to_id:
            sanitized_label = re.sub(r'[^a-zA-Z0-9_]', '', label.replace(" ", "_").replace("-", "_"))
            node_id = sanitized_label
            counter = 1
            while node_id in uri_to_id.values():
                node_id = f"{sanitized_label}_{counter}"
                counter += 1
            uri_to_id[uri] = node_id
        return uri_to_id[uri]
    
    def is_valid_node(uri_str, uri_obj):
        label = get_uri_last_part(uri_str)
        return (
            uri_str != str(current_page_full_uri) and
            not isinstance(uri_obj, Literal) and
            label.lower() not in predicates['METADATA_LOWER'] and
            label.lower() not in predicates['RELATIONSHIP_LOWER'] and
            uri_str not in nodes_to_render
        )

    current_page_label = get_mermaid_safe_label(current_page_title)
    current_page_id = get_or_create_node_id(str(current_page_full_uri), current_page_title)
    current_page_properties = get_entity_properties_for_mermaid(
        graph, str(current_page_full_uri), predicates['RELATIONSHIP'], predicates['METADATA'], predicates['LITERAL_PROPERTIES'])
    nodes_to_render[str(current_page_full_uri)] = {
        "id": current_page_id,
        "label": current_page_label,
        "props": current_page_properties,
    }
    
    for layer in range(1, max_layers + 1):
        next_layer_nodes = set()
        for source_uri_str in list(current_layer_nodes):
            source_uri_ref = URIRef(source_uri_str)
            source_id = nodes_to_render[source_uri_str]["id"]
            
            # Forward relationships
            for _, p, o in graph.triples((source_uri_ref, None, None)):
                target_uri_str, target_uri_ref = str(o), o
                predicate_label = get_uri_last_part(str(p))
                
                if predicate_label in predicates['RELATIONSHIP'] and predicate_label not in predicates['METADATA']:
                    if is_valid_node(target_uri_str, target_uri_ref):
                        target_label = find_label_for_uri(target_uri_ref, graph)
                        target_id = get_or_create_node_id(target_uri_str, target_label)
                        target_properties = get_entity_properties_for_mermaid(
                            graph, target_uri_str, predicates['RELATIONSHIP'], predicates['METADATA'], predicates['LITERAL_PROPERTIES'])
                        nodes_to_render[target_uri_str] = {"id": target_id, "label": get_mermaid_safe_label(target_label), "props": target_properties}
                        next_layer_nodes.add(target_uri_str)
                    if target_uri_str in nodes_to_render:
                        edges_to_render.add((source_id, predicate_label, nodes_to_render[target_uri_str]["id"]))

            # Inverse relationships
            if not should_skip_inverse_relationships:
                for s, p, _ in graph.triples((None, None, source_uri_ref)):
                    source_inverse_uri_str, source_inverse_uri_ref = str(s), s
                    predicate_label = get_uri_last_part(str(p))
                    if predicate_label in predicates['RELATIONSHIP'] and predicate_label not in predicates['METADATA']:
                        if is_valid_node(source_inverse_uri_str, source_inverse_uri_ref):
                            source_inverse_label = find_label_for_uri(source_inverse_uri_ref, graph)
                            source_inverse_id = get_or_create_node_id(source_inverse_uri_str, source_inverse_label)
                            source_inverse_properties = get_entity_properties_for_mermaid(
                                graph, source_inverse_uri_str, predicates['RELATIONSHIP'], predicates['METADATA'], predicates['LITERAL_PROPERTIES'])
                            nodes_to_render[source_inverse_uri_str] = {"id": source_inverse_id, "label": get_mermaid_safe_label(source_inverse_label), "props": source_inverse_properties}
                            next_layer_nodes.add(source_inverse_uri_str)
                        if source_inverse_uri_str in nodes_to_render:
                            edges_to_render.add((nodes_to_render[source_inverse_uri_str]["id"], predicate_label, source_id))
        
        current_layer_nodes = next_layer_nodes
        if not current_layer_nodes:
            break
            
    return nodes_to_render, edges_to_render