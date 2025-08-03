import os
import glob
import shutil
import re
from rdflib import Graph, URIRef, Literal, RDFS, OWL, RDF
from urllib.parse import urlparse
import yaml

# --- Configuration ---
SOURCE_DIR = "/home/hide/Documents/Heidi2workspace/heidi2/publish"
DESTINATION_DIR = "/home/hide/quartz/content"
TTL_DIR = "/home/hide/Documents/Heidi2workspace/ttl_publish"
DRAFT_STATUS = False # Set to Python boolean False for 'draft: false'
BASE_URI = "https://heidingaway.github.io/heidi2/"
ENTITY_FILTER_NAMESPACE = [
    "https://gcxgce.sharepoint.com/teams/10001579/",
    # You can add more namespaces here, for example:
    # "http://example.com/another_namespace/",
    # "https://my-internal-wiki.com/pages/"
]

# --- Core Literal Properties (less dynamic, as it's about display preference) ---
# These are properties whose values you typically want to display *inside* a Mermaid node.
# This set remains somewhat static as it's about how you want to present data,
# not necessarily inferred from the ontology structure itself.
CORE_LITERAL_PROPERTIES_FOR_NODE_DISPLAY = {
    "birthDate", "nationality", "type", "field", "description",
    "comment", "versionInfo", "label", "name" 
} 

import re

def get_mermaid_safe_label(text: str) -> str:
    """
    Sanitizes a string for safe inclusion as a label in Mermaid diagrams.
    Removes Markdown links and other problematic characters.
    """
    safe_text = str(text)

    # 1. First, remove Markdown link syntax (e.g., [text](url))
    # This regex removes the entire link pattern, including the parentheses.
    safe_text = re.sub(r'\[.*?\]\(.*?\)', '', safe_text)

    # 2. Then, handle double backslashes first to prevent them from being escaped again
    safe_text = safe_text.replace('\\', '\\\\')

    # 3. Escape or replace other special Mermaid characters that can break syntax.
    #    This includes quotes, backticks, parentheses, and slashes that might be in URLs.
    safe_text = safe_text.replace('"', '\\"')
    safe_text = safe_text.replace('`', "'")
    safe_text = safe_text.replace('\n', '<br>')
    safe_text = safe_text.replace('(', '').replace(')', '') # Remove parentheses
    safe_text = safe_text.replace('<', '&lt;').replace('>', '&gt;')
    safe_text = safe_text.replace('|', '/')
    safe_text = safe_text.replace('//', '/') # Replace double slashes to prevent issues

    # 4. Remove any remaining non-printable characters
    safe_text = re.sub(r'[^\x20-\x7E]', '', safe_text)

    # 5. Trim leading/trailing whitespace
    return safe_text.strip()

def find_label_for_uri(uri: URIRef, graph: Graph) -> str:
    """
    Finds a human-readable label for a given URI.
    First tries to find an rdfs:label in the graph.
    If no label is found, falls back to extracting the last part of the URI.
    """
    for _, _, label in graph.triples((uri, RDFS.label, None)):
        if isinstance(label, Literal):
            # Return the first literal label found
            return str(label)
    
    # If no rdfs:label is found, fall back to the last part of the URI
    return get_uri_last_part(str(uri))

def get_uri_last_part(uri: str) -> str:
    """
    Helper function to robustly extract the last part of a URI,
    handling both standard URIs and common prefixed identifiers.
    """
    # First, handle prefixed URIs like 'ex:label'
    if ':' in uri and not uri.startswith('http'):
        return uri.split(':', 1)[1]
    
    # Then handle standard URIs
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

    # If all else fails, return the full string
    return uri

def load_dynamic_predicates(graph: Graph) -> tuple[set, set, set, set, set, set]:
    """
    Dynamically loads relationship predicates and metadata predicates from the RDF graph.
    Returns both original and lowercase versions of the sets for robust comparison.
    """
    dynamic_relationship_predicates = set()
    dynamic_metadata_predicates = set()
    dynamic_literal_properties = set(CORE_LITERAL_PROPERTIES_FOR_NODE_DISPLAY)

    # Add common RDF/OWL vocabulary terms to metadata predicates.
    # We remove 'subClassOf' from this list.
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

    # Iterate through the graph to find defined datatype properties and add them to literal properties
    for s, p, o in graph.triples((None, RDF.type, OWL.DatatypeProperty)):
        label_triples = list(graph.triples((s, RDFS.label, None)))
        if label_triples:
            literal_prop_label = get_uri_last_part(str(label_triples[0][2]))
            dynamic_literal_properties.add(literal_prop_label)
        else:
            literal_prop_label = get_uri_last_part(str(s))
            dynamic_literal_properties.add(literal_prop_label)

    # Now, iterate through ALL predicates in the graph and classify them
    for p_uri in graph.predicates():
        predicate_label = get_uri_last_part(str(p_uri))
        if predicate_label not in dynamic_metadata_predicates and \
           predicate_label not in dynamic_literal_properties:
            dynamic_relationship_predicates.add(predicate_label)

    # Add any predicates that are explicitly defined as inverses (they are also relationships)
    for s, p, o in graph.triples((None, OWL.inverseOf, None)):
        label_s = next((get_uri_last_part(str(l[2])) for l in graph.triples((s, RDFS.label, None))), get_uri_last_part(str(s)))
        label_o = next((get_uri_last_part(str(l[2])) for l in graph.triples((o, RDFS.label, None))), get_uri_last_part(str(o)))
        dynamic_relationship_predicates.add(label_s)
        dynamic_relationship_predicates.add(label_o)
    
    # Ensure 'subClassOf' is in the relationship predicates
    dynamic_relationship_predicates.update({
        "subClassOf", # Add the simple label
        str(RDFS.subClassOf), # Add the full URI part
        "creator", "subject", "seeAlso", "hasTopic", "title", "influencedBy", "hasField",
        "defines", "drives", "interactsWith", "delivers", "hasPart", "partOf"
    })
    # Ensure standard metadata predicates are always included
    dynamic_metadata_predicates.update({
        "comment", "versionInfo", "label"
    })
    
    # Create lowercase versions for robust comparison
    dynamic_relationship_predicates_lower = {p.lower() for p in dynamic_relationship_predicates}
    dynamic_metadata_predicates_lower = {p.lower() for p in dynamic_metadata_predicates}
    dynamic_literal_properties_lower = {p.lower() for p in dynamic_literal_properties}
    
    return (dynamic_relationship_predicates, dynamic_metadata_predicates, dynamic_literal_properties, 
            dynamic_relationship_predicates_lower, dynamic_metadata_predicates_lower, dynamic_literal_properties_lower)



def find_uri_for_filename(filename: str, graph: Graph) -> URIRef:
    """
    Finds the URI reference in the graph that corresponds to the given filename.
    If no matching URI is found, it constructs a new one based on the filename.
    """
    normalized_filename = filename.lower().replace(" ", "_").replace("-", "_")
    file_uri_ref = None

    for s, _, o in graph.triples((None, None, None)):
        if get_uri_last_part(str(s)).lower().replace(" ", "_").replace("-", "_") == normalized_filename:
            file_uri_ref = s
            break
        if isinstance(o, URIRef) and get_uri_last_part(str(o)).lower().replace(" ", "_").replace("-", "_") == normalized_filename:
            file_uri_ref = o
            break
            
    if not file_uri_ref:
        file_uri_ref = URIRef(f"{BASE_URI}{normalized_filename}")
        
    return file_uri_ref
    
def get_entity_properties_for_mermaid(graph: Graph, entity_uri: str, 
                                      RELATIONSHIP_PREDICATES: set, 
                                      METADATA_PREDICATES: set, 
                                      LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set) -> str:
    """
    Queries the graph for direct properties of a given entity URI
    and formats them as plain text for Mermaid node display.
    Only includes properties from LITERAL_PROPERTIES_FOR_NODE_DISPLAY.
    """
    properties_list = []
    entity_ref = URIRef(entity_uri)
    
    for s, p, o in graph.triples((entity_ref, None, None)):
        prop_name = get_uri_last_part(str(p))
        prop_value = get_uri_last_part(str(o))
        
        # Only add if the predicate is in our defined set for internal node display
        # and the object is a literal or a URI that shouldn't be a separate node
        if prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, Literal):
            properties_list.append(f"+ {prop_name}: {prop_value}")
        elif prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, URIRef):
            # If it's a URI but we still want it as a property (e.g., rdf:type)
            # and it's not a relationship predicate, add it.
            # Also ensure it's not a metadata predicate that should be filtered out
            if prop_name not in RELATIONSHIP_PREDICATES and prop_name not in METADATA_PREDICATES:
                properties_list.append(f"+ {prop_name}: {prop_value}")
    
    if properties_list:
        return "<br>" + "<br>".join(properties_list)
        
    return ""

def generate_mermaid_syntax(current_page_filename: str, current_page_title: str, graph: Graph,
                            RELATIONSHIP_PREDICATES: set,
                            METADATA_PREDICATES: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set,
                            RELATIONSHIP_PREDICATES_LOWER: set,
                            METADATA_PREDICATES_LOWER: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER: set,
                            current_page_full_uri: URIRef,
                            should_skip_inverse_relationships: bool,
                            max_layers: int) -> tuple[str, set]:
    
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
            label.lower() not in METADATA_PREDICATES_LOWER and
            label.lower() not in RELATIONSHIP_PREDICATES_LOWER and
            uri_str not in nodes_to_render
        )

    current_page_label = get_mermaid_safe_label(current_page_title)
    current_page_id = get_or_create_node_id(str(current_page_full_uri), current_page_title)
    current_page_properties = get_entity_properties_for_mermaid(graph, str(current_page_full_uri),
                                                                 RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
    nodes_to_render[str(current_page_full_uri)] = {
        "id": current_page_id,
        "label": current_page_label,
        "props": current_page_properties,
    }
    
    # Traverse connections up to the specified maximum number of layers
    for layer in range(1, max_layers + 1):
        next_layer_nodes = set()
        for source_uri_str in list(current_layer_nodes):
            source_uri_ref = URIRef(source_uri_str)
            source_id = nodes_to_render[source_uri_str]["id"]
            
            # --- Forward Relationships ---
            for _, p, o in graph.triples((source_uri_ref, None, None)):
                target_uri_str, target_uri_ref = str(o), o
                predicate_label = get_uri_last_part(str(p))
                
                if predicate_label in RELATIONSHIP_PREDICATES and predicate_label not in METADATA_PREDICATES:
                    if is_valid_node(target_uri_str, target_uri_ref):
                        target_label = find_label_for_uri(target_uri_ref, graph)
                        target_id = get_or_create_node_id(target_uri_str, target_label)
                        target_properties = get_entity_properties_for_mermaid(graph, target_uri_str, RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
                        nodes_to_render[target_uri_str] = {"id": target_id, "label": get_mermaid_safe_label(target_label), "props": target_properties}
                        next_layer_nodes.add(target_uri_str)
                    if target_uri_str in nodes_to_render:
                        edges_to_render.add((source_id, predicate_label, nodes_to_render[target_uri_str]["id"]))

            # --- Inverse Relationships (Controlled) ---
            if not should_skip_inverse_relationships:
                for s, p, _ in graph.triples((None, None, source_uri_ref)):
                    source_inverse_uri_str, source_inverse_uri_ref = str(s), s
                    predicate_label = get_uri_last_part(str(p))

                    if predicate_label in RELATIONSHIP_PREDICATES and predicate_label not in METADATA_PREDICATES:
                        if is_valid_node(source_inverse_uri_str, source_inverse_uri_ref):
                            source_inverse_label = find_label_for_uri(source_inverse_uri_ref, graph)
                            source_inverse_id = get_or_create_node_id(source_inverse_uri_str, source_inverse_label)
                            source_inverse_properties = get_entity_properties_for_mermaid(graph, source_inverse_uri_str, RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
                            nodes_to_render[source_inverse_uri_str] = {"id": source_inverse_id, "label": get_mermaid_safe_label(source_inverse_label), "props": source_inverse_properties}
                            next_layer_nodes.add(source_inverse_uri_str)
                        if source_inverse_uri_str in nodes_to_render:
                            edges_to_render.add((nodes_to_render[source_inverse_uri_str]["id"], predicate_label, source_id))
        
        current_layer_nodes = next_layer_nodes
        if not current_layer_nodes:
            break
            
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



def process_markdown_file(file_path: str, filename: str, graph: Graph,
                            RELATIONSHIP_PREDICATES: set,
                            METADATA_PREDICATES: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set,
                            all_source_markdown_basenames_lower: set,
                            current_page_full_uri: URIRef,
                            RELATIONSHIP_PREDICATES_LOWER: set,
                            METADATA_PREDICATES_LOWER: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER: set,
                            should_skip_inverse_relationships: bool):
    """
    Adds or updates YAML frontmatter, appends Mermaid syntax, and adds related wikilinks
    to the body of a markdown file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    existing_frontmatter = {}
    markdown_body = content
    if content.startswith("---"):
        try:
            yaml_end_index = content.find("---", 3)
            if yaml_end_index != -1:
                yaml_str = content[3:yaml_end_index].strip()
                existing_frontmatter = yaml.safe_load(yaml_str) or {}
                if False in existing_frontmatter:
                    del existing_frontmatter[False]
                markdown_body = content[yaml_end_index + 3:].strip()
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}. Treating as no existing frontmatter.")
            pass
            
    # Get the human-readable title from the front matter
    title_for_removal = existing_frontmatter.get("title")

    # --- NEW: Get the number of layers for the Mermaid diagram ---
    mermaid_layers = existing_frontmatter.get("mermaid_layers", 1) # Default to 1 layer
    if not isinstance(mermaid_layers, int) or mermaid_layers <= 0:
        mermaid_layers = 1 # Ensure it's a valid integer
    
    if title_for_removal:
        # Build a regex pattern using the human-readable title from the front matter
        title_heading_pattern = re.compile(
            r'^\s*#\s*' + re.escape(title_for_removal) + r'\s*$', 
            re.MULTILINE | re.IGNORECASE
        )
        # Remove the matching H1 heading from the body
        markdown_body = title_heading_pattern.sub('', markdown_body, count=1).strip()
    mermaid_block_pattern = re.compile(
        r'(?:\s*^##\s*Semantic\s*Connections\s*$\s*)?^\s*```mermaid\s*$\n.*?\n^\s*```\s*$', re.DOTALL | re.MULTILINE)
    related_links_block_pattern = re.compile(
        r'(?:\s*^##\s*Related\s*Links\s*$\s*)?(?:^\s*-\s*\[\[.*?\]\]\s*$\n)*', re.DOTALL | re.MULTILINE | re.IGNORECASE)
    footnotes_header_pattern = re.compile(r'^\s*#+\s*Footnotes\s*$', re.MULTILINE | re.IGNORECASE)
    markdown_body = mermaid_block_pattern.sub('', markdown_body).strip()
    markdown_body = related_links_block_pattern.sub('', markdown_body).strip()
    markdown_body = footnotes_header_pattern.sub('', markdown_body).strip()
    mermaid_syntax_content = ""
    graph_node_ids = set()
    
    # Get human-readable title for Mermaid syntax
    human_readable_title = existing_frontmatter.get("title", filename)

    # Parse 'subClassOf' from existing front matter and add to the graph
    subClassOf_list = existing_frontmatter.get("subClassOf", [])
    if isinstance(subClassOf_list, list):
        for parent_filename in subClassOf_list:
            parent_filename = parent_filename.replace("[[", "").replace("]]", "")
            parent_uri = find_uri_for_filename(parent_filename, graph)
            if parent_uri:
                graph.add((current_page_full_uri, RDFS.subClassOf, parent_uri))
                print(f"DEBUG: Added subClassOf relationship for '{filename}' to '{parent_filename}'.")

    # Now, call generate_mermaid_syntax with both filename AND title, and the new mermaid_layers
    mermaid_syntax_content, graph_node_ids = generate_mermaid_syntax(
        filename,
        human_readable_title,
        graph,
        RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY,
        RELATIONSHIP_PREDICATES_LOWER, METADATA_PREDICATES_LOWER, LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER,
        current_page_full_uri,
        should_skip_inverse_relationships,
        mermaid_layers # Pass the new parameter
    )
    
    related_for_body = set()
    related_for_frontmatter = set()

    for node_id in graph_node_ids:
        related_entity_uri = find_uri_for_filename(node_id, graph)
        if related_entity_uri:
            related_for_frontmatter.add(str(related_entity_uri))
            
        if node_id.lower() in all_source_markdown_basenames_lower and node_id.lower() != filename.lower():
            related_for_body.add(f"[[{node_id}]]")

    if (current_page_full_uri, RDF.type, RDFS.Class) in graph:
        print(f"DEBUG: '{filename}' is a class. Checking for parent classes...")
        for _, _, parent_class_uri in graph.triples((current_page_full_uri, RDFS.subClassOf, None)):
            if parent_class_uri != current_page_full_uri:
                related_for_frontmatter.add(str(parent_class_uri))
                print(f"DEBUG:   Added parent class '{parent_class_uri}' to entities.")

    merged_frontmatter = {
        **existing_frontmatter,
        "entities": sorted(list(related_for_frontmatter)),
        "draft": DRAFT_STATUS,
    }
    for key in ["related", "semantic_links"]:
        if key in merged_frontmatter:
            del merged_frontmatter[key]
    print(f"DEBUG: Final frontmatter keys before dump: {merged_frontmatter.keys()}")
    body_append_content = ""
    markdown_body = re.sub(r'\n\s*\n', '\n\n', markdown_body).strip()
    if related_for_body:
        sorted_related_links = sorted(list(related_for_body))
        links_markdown = "\n".join([f"- {link}" for link in sorted_related_links])
        body_append_content += f"\n\n## Related Links\n\n{links_markdown}\n"
    if mermaid_syntax_content:
        body_append_content += f"\n\n## Semantic Connections\n\n```mermaid\n{mermaid_syntax_content}\n```"
    frontmatter_yaml = yaml.dump(merged_frontmatter, sort_keys=False).strip()
    new_content = f"---\n{frontmatter_yaml}\n---\n\n{markdown_body}{body_append_content}"
    new_content = re.sub(r'\n\n\n+', '\n\n', new_content).strip() + '\n'
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_subclass_depth(entity_uri: URIRef, graph: Graph, root_classes: set) -> int:
    """
    Finds the shortest path depth of an entity from a root class.
    Returns 0 for a root class, 1 for a direct child, 2 for a grandchild, etc.
    Returns -1 if the entity is not a subclass of any root class.
    """
    queue = [(entity_uri, 0)] # (URI, depth)
    visited = set()
    
    RDFS_SUBCLASSOF = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    
    while queue:
        current_uri, depth = queue.pop(0)
        
        if current_uri in root_classes:
            return depth
            
        if current_uri in visited:
            continue
            
        visited.add(current_uri)
        
        # Find all direct superclasses
        for _, _, super_class in graph.triples((current_uri, RDFS_SUBCLASSOF, None)):
            queue.append((super_class, depth + 1))
            
    return -1
    
def preprocess_files(source: str, destination: str, ttl_source: str):
    """
    Main function to orchestrate the preprocessing workflow.
    """
    os.makedirs(destination, exist_ok=True)
    
    ttl_files = glob.glob(os.path.join(ttl_source, "**/*.ttl"), recursive=True)
    
    g = Graph()
    for ttl_file in ttl_files:
        try:
            g.parse(ttl_file, format="turtle")
        except Exception as e:
            print(f"Error parsing {ttl_file}: {e}")
            continue

    RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY, \
    RELATIONSHIP_PREDICATES_LOWER, METADATA_PREDICATES_LOWER, LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER = load_dynamic_predicates(g)

    all_source_markdown_basenames_lower = set()
    for md_file_path_in_source in glob.glob(os.path.join(SOURCE_DIR, "**/*.md"), recursive=True):
        filename_no_ext = os.path.splitext(os.path.basename(md_file_path_in_source))[0].lower()
        all_source_markdown_basenames_lower.add(filename_no_ext)

    source_md_files = glob.glob(os.path.join(source, "**/*.md"), recursive=True)
    for md_file_path_src in source_md_files:
        relative_path = os.path.relpath(md_file_path_src, source)
        dest_file_path = os.path.join(destination, relative_path)
        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
        shutil.copy2(md_file_path_src, dest_file_path)

    GENERIC_ROOT_CLASSES = {
        URIRef("https://schema.org/Thing"),
        URIRef("http://www.w3.org/2002/07/owl#Thing"),
        URIRef("http://www.w3.org/2000/01/rdf-schema#Resource"),
    }
    RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    RDFS_CLASS = URIRef("http://www.w3.org/2000/01/rdf-schema#Class")
    
    dest_md_files = glob.glob(os.path.join(destination, "**/*.md"), recursive=True)
    for md_file_path_in_dest in dest_md_files:
        filename_with_ext = os.path.basename(md_file_path_in_dest)
        filename = os.path.splitext(filename_with_ext)[0]
        file_uri_ref = find_uri_for_filename(filename, g) 
        
        # Re-introducing the depth-based check
        class_depth = get_subclass_depth(file_uri_ref, g, GENERIC_ROOT_CLASSES)
        is_rdfs_class = (file_uri_ref, RDF_TYPE, RDFS_CLASS) in g
        should_skip_inverse_relationships = (class_depth <= 1 and class_depth != -1) or is_rdfs_class

        process_markdown_file(
            md_file_path_in_dest, filename, g,
            RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY,
            all_source_markdown_basenames_lower, 
            file_uri_ref,
            RELATIONSHIP_PREDICATES_LOWER, METADATA_PREDICATES_LOWER, LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER,
            should_skip_inverse_relationships # Pass the new flag
        ) 

    print("Preprocessing complete!")
    
def extract_entity_uris_from_markdown_yaml(destination_dir: str, valid_target_basenames: set[str]):
    # (This function remains unchanged)
    extracted_data = {}
    yaml_front_matter_regex = re.compile(r"^-{3}\s*\n(.*?)\n-{3}\s*\n", re.DOTALL)
    for root, _, files in os.walk(destination_dir):
        for file_name in files:
            if file_name.endswith(".md"):
                file_path = os.path.join(root, file_name)
                relative_file_path = os.path.relpath(file_path, destination_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = yaml_front_matter_regex.match(content)
                if match:
                    yaml_string = match.group(1)
                    try:
                        data = yaml.safe_load(yaml_string)
                        if data and 'entities' in data and isinstance(data['entities'], list):
                            entities_in_file = []
                            for uri in data['entities']:
                                last_section = get_uri_last_part(uri)
                                if last_section.lower() not in valid_target_basenames:
                                    continue
                                entities_in_file.append({
                                    'uri': uri,
                                    'last_section': last_section
                                })
                            if entities_in_file:
                                extracted_data[relative_file_path] = entities_in_file
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML in {relative_file_path}: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred processing {relative_file_path}: {e}")
    return extracted_data

def update_source_yaml_with_related_entities(source_dir: str, destination_dir: str):
    """
    Updates the YAML front matter of Markdown files in the SOURCE_DIR
    by replacing the 'related:' key with a new list of links derived
    from entities found in the corresponding files in the DESTINATION_DIR.
    """
    print(f"Step 1: Pre-collecting Markdown basenames from '{destination_dir}' for filtering...")
    all_destination_markdown_basenames_lower = set()
    for md_file_path_in_dest in glob.glob(os.path.join(destination_dir, "**/*.md"), recursive=True):
        filename_no_ext = os.path.splitext(os.path.basename(md_file_path_in_dest))[0].lower()
        all_destination_markdown_basenames_lower.add(filename_no_ext)
    
    print(f"\nStep 2: Extracting entities from Markdown files in '{destination_dir}'...")
    extracted_entities_map = extract_entity_uris_from_markdown_yaml(destination_dir, all_destination_markdown_basenames_lower)
    print(f"Found entities in {len(extracted_entities_map)} files in destination directory (after filtering).")

    yaml_front_matter_and_content_regex = re.compile(r"^-{3}\s*\n(.*?)\n-{3}\s*\n(.*)", re.DOTALL)

    print(f"\nStep 3: Updating YAML in source files in '{source_dir}'...")
    updated_count = 0
    
    for relative_file_path, entities_list in extracted_entities_map.items():
        source_file_path = os.path.join(source_dir, relative_file_path)

        if not os.path.exists(source_file_path):
            print(f"  Warning: Source file not found for '{relative_file_path}'. Skipping.")
            continue

        try:
            with open(source_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = yaml_front_matter_and_content_regex.match(content)
            if not match:
                print(f"  Warning: No YAML front matter found in source file '{relative_file_path}'. Skipping update.")
                continue

            yaml_string = match.group(1)
            remaining_content = match.group(2)

            source_yaml_data = yaml.safe_load(yaml_string)
            if source_yaml_data is None:
                source_yaml_data = {}

            # --- START: Updated logic to overwrite the 'related' key ---
            # Use a dictionary to deduplicate links case-insensitively
            new_related_links_dict = {}
            current_basename_lower = os.path.splitext(os.path.basename(source_file_path))[0].lower()
            
            for entity in entities_list:
                entity_basename_lower = entity['last_section'].lower()
                
                # Only add the link if it's not a self-reference
                if entity_basename_lower != current_basename_lower:
                    # If the link doesn't exist (case-insensitively), add it
                    if entity_basename_lower not in new_related_links_dict:
                        formatted_link = f"[[{entity['last_section']}]]"
                        new_related_links_dict[entity_basename_lower] = formatted_link

            # The final list is the sorted values of our dictionary
            final_related_links = sorted(list(new_related_links_dict.values()))
            source_yaml_data['related'] = final_related_links
            # --- END: Updated logic ---

            updated_yaml_string = yaml.dump(source_yaml_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{updated_yaml_string}---\n{remaining_content}"

            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated_count += 1

        except yaml.YAMLError as e:
            print(f"  Error parsing YAML in source file '{relative_file_path}': {e}")
        except Exception as e:
            print(f"  An unexpected error occurred while updating '{relative_file_path}': {e}")

    print(f"\nFinished updating. Successfully updated {updated_count} source files.")


if __name__ == "__main__":
    preprocess_files(SOURCE_DIR, DESTINATION_DIR, TTL_DIR)
    update_source_yaml_with_related_entities("/home/hide/Documents/Heidi2workspace/heidi2/publish", "/home/hide/quartz/content")