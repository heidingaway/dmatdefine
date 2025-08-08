import os
import re
from rdflib import URIRef, Graph, RDFS, RDF

def generate_body_content(mermaid_syntax_content: str, graph_node_ids: set, all_source_markdown_basenames_lower: set) -> str:
    """
    Generates the 'Related Links' and 'Semantic Connections' sections for the Markdown body.
    """
    body_append_content = ""
    related_for_body = set()
    for node_id in graph_node_ids:
        if node_id.lower() in all_source_markdown_basenames_lower:
            related_for_body.add(f"[[{node_id}]]")

    if related_for_body:
        sorted_related_links = sorted(list(related_for_body))
        links_markdown = "\n".join([f"- {link}" for link in sorted_related_links])
        body_append_content += f"\n\n## Related Links\n\n{links_markdown}\n"
    if mermaid_syntax_content:
        body_append_content += f"\n\n## Semantic Connections\n\n```mermaid\n{mermaid_syntax_content}\n```"
    
    return body_append_content

def update_frontmatter(existing_frontmatter: dict, graph: Graph, filename: str,
                       graph_node_ids: set, current_page_full_uri: URIRef, draft_status: bool, base_uri: str) -> dict:
    """
    Updates the frontmatter dictionary with new entities and draft status.
    """
    from ..rdf.rdf_helpers import find_uri_for_filename  # Import here to avoid circular dependency
    
    related_for_frontmatter = set()

    for node_id in graph_node_ids:
        related_entity_uri = find_uri_for_filename(node_id, graph, base_uri)
        if related_entity_uri:
            related_for_frontmatter.add(str(related_entity_uri))
            
    if (current_page_full_uri, RDF.type, RDFS.Class) in graph:
        for _, _, parent_class_uri in graph.triples((current_page_full_uri, RDFS.subClassOf, None)):
            if parent_class_uri != current_page_full_uri:
                related_for_frontmatter.add(str(parent_class_uri))

    merged_frontmatter = {
        **existing_frontmatter,
        "entities": sorted(list(related_for_frontmatter)),
        "draft": draft_status,
    }
    for key in ["related", "semantic_links"]:
        if key in merged_frontmatter:
            del merged_frontmatter[key]
    
    return merged_frontmatter