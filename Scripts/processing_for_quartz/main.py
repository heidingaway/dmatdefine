import os
import glob
import shutil
from rdflib import Graph, URIRef
from .markdown.read_write_clean_md import read_markdown_file, write_markdown_file, clean_markdown_body
from .markdown.generate_md_body import generate_body_content, update_frontmatter
from .markdown.frontmatter_sync import update_source_yaml_with_related_entities
from .mermaid.generate_mermaid import generate_mermaid_syntax
from .rdf.parse_graph import load_dynamic_predicates
from .rdf.rdf_helpers import find_uri_for_filename, get_subclass_depth
from .config import SOURCE_DIR, DESTINATION_DIR, TTL_DIR, DRAFT_STATUS, BASE_URI

def main():
    """
    Main function to orchestrate the preprocessing and synchronization workflow.
    """
    # 1. Setup and RDF Graph Loading
    os.makedirs(DESTINATION_DIR, exist_ok=True)
    
    ttl_files = glob.glob(os.path.join(TTL_DIR, "**/*.ttl"), recursive=True)
    g = Graph()
    for ttl_file in ttl_files:
        try:
            g.parse(ttl_file, format="turtle")
        except Exception as e:
            print(f"Error parsing {ttl_file}: {e}")
            continue

    # 2. Get Predicate Sets
    RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY, \
    RELATIONSHIP_PREDICATES_LOWER, METADATA_PREDICATES_LOWER, LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER = load_dynamic_predicates(g)

    # 3. Pre-collect source file names
    all_source_markdown_basenames_lower = set()
    for md_file_path_in_source in glob.glob(os.path.join(SOURCE_DIR, "**/*.md"), recursive=True):
        filename_no_ext = os.path.splitext(os.path.basename(md_file_path_in_source))[0].lower()
        all_source_markdown_basenames_lower.add(filename_no_ext)

    # 4. Copy source files to destination
    source_md_files = glob.glob(os.path.join(SOURCE_DIR, "**/*.md"), recursive=True)
    for md_file_path_src in source_md_files:
        relative_path = os.path.relpath(md_file_path_src, SOURCE_DIR)
        dest_file_path = os.path.join(DESTINATION_DIR, relative_path)
        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
        shutil.copy2(md_file_path_src, dest_file_path)

    # 5. Process each Markdown file in the destination folder
    GENERIC_ROOT_CLASSES = {
        URIRef("https://schema.org/Thing"),
        URIRef("http://www.w3.org/2002/07/owl#Thing"),
        URIRef("http://www.w3.org/2000/01/rdf-schema#Resource"),
    }
    RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    RDFS_CLASS = URIRef("http://www.w3.org/2000/01/rdf-schema#Class")
    
    dest_md_files = glob.glob(os.path.join(DESTINATION_DIR, "**/*.md"), recursive=True)
    for md_file_path_in_dest in dest_md_files:
        filename_with_ext = os.path.basename(md_file_path_in_dest)
        filename = os.path.splitext(filename_with_ext)[0]
        
        # Determine the URI and class depth
        file_uri_ref = find_uri_for_filename(filename, g, BASE_URI)
        class_depth = get_subclass_depth(file_uri_ref, g, GENERIC_ROOT_CLASSES)
        is_rdfs_class = (file_uri_ref, RDF_TYPE, RDFS_CLASS) in g
        should_skip_inverse_relationships = (class_depth <= 1 and class_depth != -1) or is_rdfs_class

        # Read, clean, and process the file
        existing_frontmatter, raw_markdown_body = read_markdown_file(md_file_path_in_dest)
        
        clean_body = clean_markdown_body(raw_markdown_body, existing_frontmatter.get("title", filename))

        # Generate Mermaid syntax and get related entities
        # The mermaid_layers variable must be an integer from your frontmatter.
        mermaid_layers = existing_frontmatter.get("mermaid_layers", 1)

        mermaid_syntax_content, graph_node_ids = generate_mermaid_syntax(
            current_page_title=existing_frontmatter.get("title", filename),
            graph=g,
            RELATIONSHIP_PREDICATES=RELATIONSHIP_PREDICATES,
            METADATA_PREDICATES=METADATA_PREDICATES,
            LITERAL_PROPERTIES_FOR_NODE_DISPLAY=LITERAL_PROPERTIES_FOR_NODE_DISPLAY,
            RELATIONSHIP_PREDICATES_LOWER=RELATIONSHIP_PREDICATES_LOWER,
            METADATA_PREDICATES_LOWER=METADATA_PREDICATES_LOWER,
            LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER=LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER,
            current_page_full_uri=file_uri_ref,
            should_skip_inverse_relationships=should_skip_inverse_relationships,
            max_layers=mermaid_layers
        )

        # Generate new body content (Mermaid and wikilinks)
        body_append_content = generate_body_content(mermaid_syntax_content, graph_node_ids, all_source_markdown_basenames_lower)
        
        # Update frontmatter
        updated_frontmatter = update_frontmatter(
            existing_frontmatter, g, filename, graph_node_ids, file_uri_ref, DRAFT_STATUS, BASE_URI)
            
        # Write the final file
        final_body = clean_body + body_append_content
        write_markdown_file(md_file_path_in_dest, updated_frontmatter, final_body)

    print("Preprocessing complete!")
    
    # 6. Synchronize frontmatter back to source files
    update_source_yaml_with_related_entities(SOURCE_DIR, DESTINATION_DIR)

if __name__ == "__main__":
    main()