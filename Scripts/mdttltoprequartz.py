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

def get_mermaid_safe_label(text: str) -> str:
    """
    Sanitizes a string for safe inclusion as a label in Mermaid diagrams.
    Escapes double quotes and converts newlines.
    """
    safe_text = str(text)
    safe_text = safe_text.replace('\\', '\\\\')
    safe_text = safe_text.replace('"', '\\"') 
    safe_text = safe_text.replace('`', "'") 
    safe_text = safe_text.replace('\n', '<br>') 
    safe_text = safe_text.replace('[', '(').replace(']', ')') 
    safe_text = safe_text.replace('<', '&lt;').replace('>', '&gt;') 
    safe_text = safe_text.replace('|', '/') 
    safe_text = re.sub(r'[^\x20-\x7E]', '', safe_text)
    return safe_text

from urllib.parse import urlparse

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

    # Add common RDF/OWL vocabulary terms to metadata predicates
    dynamic_metadata_predicates.update({
        get_uri_last_part(str(RDF.type)), 
        get_uri_last_part(str(RDFS.subClassOf)),
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
    
    # Ensure standard relationship predicates are always included
    dynamic_relationship_predicates.update({
        "creator", "subject", "seeAlso", "hasTopic", "title", "influencedBy", "hasField",
        "defines", "drives", "interactsWith", "delivers", "hasPart", "partOf"
    })

    # Ensure standard metadata predicates are always included
    dynamic_metadata_predicates.update({
        "comment", "versionInfo", "label", "subClassOf"
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
    
    # print(f"DEBUG: Getting properties for entity_uri: {entity_uri}") # Too verbose
    for s, p, o in graph.triples((entity_ref, None, None)):
        prop_name = get_uri_last_part(str(p))
        prop_value = get_uri_last_part(str(o))
        
        # Only add if the predicate is in our defined set for internal node display
        # and the object is a literal or a URI that shouldn't be a separate node
        if prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, Literal):
            properties_list.append(f"+ {prop_name}: {prop_value}")
            # print(f"DEBUG:   Property added: {prop_name}: {prop_value}") # Too verbose
        elif prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY and isinstance(o, URIRef):
            # If it's a URI but we still want it as a property (e.g., rdf:type)
            # and it's not a relationship predicate, add it.
            # Also ensure it's not a metadata predicate that should be filtered out
            if prop_name not in RELATIONSHIP_PREDICATES and prop_name not in METADATA_PREDICATES:
                properties_list.append(f"+ {prop_name}: {prop_value}")
                # print(f"DEBUG:   Property added (URI as property): {prop_name}: {prop_value}") # Too verbose
            # else:
                # print(f"DEBUG:   Skipping property (URI is a relationship or metadata): {prop_name}: {prop_value}") # Too verbose
        # else:
            # print(f"DEBUG:   Property excluded (not for internal node display or is relationship): {prop_name}: {prop_value}") # Too verbose
    
    if properties_list:
        return "<br>" + "<br>".join(properties_list)
        
    return ""

# This is the corrected version of generate_mermaid_syntax.
def generate_mermaid_syntax(current_page_filename: str, graph: Graph,
                            RELATIONSHIP_PREDICATES: set,
                            METADATA_PREDICATES: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY: set,
                            RELATIONSHIP_PREDICATES_LOWER: set,
                            METADATA_PREDICATES_LOWER: set,
                            LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER: set,
                            current_page_full_uri: URIRef,
                            should_skip_inverse_relationships: bool) -> tuple[str, set]: # New argument added
    """
    Generates Mermaid graph syntax by traversing the graph from a starting URI.
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
            label.lower() not in METADATA_PREDICATES_LOWER and
            label.lower() not in RELATIONSHIP_PREDICATES_LOWER and
            uri_str not in nodes_to_render
        )

    current_page_label = get_mermaid_safe_label(current_page_filename)
    current_page_id = get_or_create_node_id(str(current_page_full_uri), current_page_filename)
    current_page_properties = get_entity_properties_for_mermaid(graph, str(current_page_full_uri),
                                                                 RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
    nodes_to_render[str(current_page_full_uri)] = {
        "id": current_page_id,
        "label": current_page_label,
        "props": current_page_properties,
    }

    for layer in range(1, 4):
        next_layer_nodes = set()
        for source_uri_str in list(current_layer_nodes):
            source_uri_ref = URIRef(source_uri_str)
            source_id = nodes_to_render[source_uri_str]["id"]
            
            # Find forward relationships
            for _, p, o in graph.triples((source_uri_ref, None, None)):
                target_uri_str, target_uri_ref = str(o), o
                predicate_label = get_uri_last_part(str(p))
                if predicate_label in RELATIONSHIP_PREDICATES and predicate_label not in METADATA_PREDICATES:
                    if is_valid_node(target_uri_str, target_uri_ref):
                        target_label = get_uri_last_part(target_uri_str)
                        target_id = get_or_create_node_id(target_uri_str, target_label)
                        target_properties = get_entity_properties_for_mermaid(graph, target_uri_str, RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
                        nodes_to_render[target_uri_str] = {"id": target_id, "label": target_label, "props": target_properties}
                        next_layer_nodes.add(target_uri_str)
                    if target_uri_str in nodes_to_render:
                        edges_to_render.add((source_id, predicate_label, nodes_to_render[target_uri_str]["id"]))

            # Find inverse relationships, now controlled by the new flag
            if not should_skip_inverse_relationships:
                for s, p, _ in graph.triples((None, None, source_uri_ref)):
                    source_inverse_uri_str, source_inverse_uri_ref = str(s), s
                    predicate_label = get_uri_last_part(str(p))
                    if predicate_label in RELATIONSHIP_PREDICATES and predicate_label not in METADATA_PREDICATES:
                        if is_valid_node(source_inverse_uri_str, source_inverse_uri_ref):
                            source_inverse_label = get_uri_last_part(source_inverse_uri_str)
                            source_inverse_id = get_or_create_node_id(source_inverse_uri_str, source_inverse_label)
                            source_inverse_properties = get_entity_properties_for_mermaid(graph, source_inverse_uri_str, RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY)
                            nodes_to_render[source_inverse_uri_str] = {"id": source_inverse_id, "label": source_inverse_label, "props": source_inverse_properties}
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
        if source_id in {data['id'] for data in nodes_to_render.values()} and target_id in {data['id'] for data in nodes_to_render.values()}:
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
    old_title = existing_frontmatter.get("title")
    normalized_old_title = old_title.lower().replace(" ", "-") if old_title else ""
    normalized_filename = filename.lower().replace(" ", "-")
    if old_title and normalized_old_title != normalized_filename:
        aliases = existing_frontmatter.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = [aliases]
        if old_title not in aliases:
            aliases.append(old_title)
        existing_frontmatter["aliases"] = aliases
    existing_frontmatter["title"] = filename
    title_heading_pattern = re.compile(r'^\s*#\s*' + re.escape(filename) + r'\s*$', re.MULTILINE | re.IGNORECASE)
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
    
    mermaid_syntax_content, graph_node_ids = generate_mermaid_syntax(
        filename,
        graph,
        RELATIONSHIP_PREDICATES, METADATA_PREDICATES, LITERAL_PROPERTIES_FOR_NODE_DISPLAY,
        RELATIONSHIP_PREDICATES_LOWER, METADATA_PREDICATES_LOWER, LITERAL_PROPERTIES_FOR_NODE_DISPLAY_LOWER,
        current_page_full_uri,
        should_skip_inverse_relationships
    )
    
    related_for_body = set()
    related_for_frontmatter = set()

    for node_id in graph_node_ids:
        related_entity_uri = find_uri_for_filename(node_id, graph)
        if related_entity_uri:
            related_for_frontmatter.add(str(related_entity_uri))
            
        if node_id.lower() in all_source_markdown_basenames_lower and node_id.lower() != filename.lower():
            related_for_body.add(f"[[{node_id}]]")

    # === NEW LOGIC: Check for and add parent classes to entities list ===
    if (current_page_full_uri, RDF.type, RDFS.Class) in graph:
        print(f"DEBUG: '{filename}' is a class. Checking for parent classes...")
        for _, _, parent_class_uri in graph.triples((current_page_full_uri, RDFS.subClassOf, None)):
            if parent_class_uri != current_page_full_uri: # Avoid self-referential subClassOf
                related_for_frontmatter.add(str(parent_class_uri))
                print(f"DEBUG:   Added parent class '{parent_class_uri}' to entities.")
    # ===================================================================

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
    
    # === CRITICAL: 'g' MUST BE INITIALIZED HERE ===
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
    """
    Reviews the YAML front matter of Markdown files in the specified directory,
    extracts URIs from the 'entities:' list,
    and returns the URI and its last section (sanitized for Mermaid).
    
    This function has been updated to correctly handle the list-based 'entities' structure.

    Args:
        destination_dir (str): The path to the directory containing Markdown files.
        valid_target_basenames (set[str]): A set of lowercase basenames (filenames without extension)
                                            from the directory containing the target files (DESTINATION_DIR),
                                            used for filtering.

    Returns:
        dict: A dictionary where keys are Markdown file paths (relative to destination_dir)
              and values are lists of dictionaries. Each inner dictionary contains
              'uri' and 'last_section' for each extracted entity.
              Returns an empty dictionary if no entities are found or an error occurs.
    """
    extracted_data = {}

    # Regex to find YAML front matter (between '---' lines)
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
                        # Load the YAML data
                        data = yaml.safe_load(yaml_string)

                        # --- FIX: Check if 'entities' key exists and is a LIST ---
                        if data and 'entities' in data and isinstance(data['entities'], list):
                            entities_in_file = []
                            # --- Iterate through the list of URIs directly ---
                            for uri in data['entities']:
                                last_section = get_uri_last_part(uri)

                                # Check if the extracted filename exists in our list of valid files
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

# The update_source_yaml_with_related_entities function should now work as expected
# once the extraction function is fixed.

def update_source_yaml_with_related_entities(source_dir: str, destination_dir: str):
    """
    Updates the YAML front matter of Markdown files in the SOURCE_DIR
    by adding a 'related:' key with links derived from entities found
    in the corresponding files in the DESTINATION_DIR.
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
    for relative_path, entities_list in extracted_entities_map.items():
        source_file_path = os.path.join(source_dir, relative_path)

        if not os.path.exists(source_file_path):
            print(f"  Warning: Source file not found for '{relative_path}'. Skipping.")
            continue

        try:
            with open(source_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = yaml_front_matter_and_content_regex.match(content)
            if not match:
                print(f"  Warning: No YAML front matter found in source file '{relative_path}'. Skipping update.")
                continue

            yaml_string = match.group(1)
            remaining_content = match.group(2)

            source_yaml_data = yaml.safe_load(yaml_string)
            if source_yaml_data is None:
                source_yaml_data = {}

            # Create a set to store all related links, normalized to lowercase
            all_related_links = set()
            
            # Get the basename of the current file for comparison and filtering
            current_basename = os.path.splitext(os.path.basename(source_file_path))[0]

            # 1. Process existing 'related' links
            if 'related' in source_yaml_data and isinstance(source_yaml_data['related'], list):
                for link in source_yaml_data['related']:
                    link_text = link.strip('[').strip(']').lower()
                    if link_text != current_basename.lower():
                        all_related_links.add(link_text)
            
            # 2. Process newly generated links
            for entity in entities_list:
                link_text = entity['last_section'].lower()
                if link_text != current_basename.lower():
                    all_related_links.add(link_text)

            # 3. Format and sort the final list
            final_related_links = sorted([f"[[{link}]]" for link in all_related_links])
            source_yaml_data['related'] = final_related_links

            updated_yaml_string = yaml.dump(source_yaml_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{updated_yaml_string}---\n{remaining_content}"

            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated_count += 1

        except yaml.YAMLError as e:
            print(f"  Error parsing YAML in source file '{relative_path}': {e}")
        except Exception as e:
            print(f"  An unexpected error occurred while updating '{relative_path}': {e}")

    print(f"\nFinished updating. Successfully updated {updated_count} source files.")

if __name__ == "__main__":
    preprocess_files(SOURCE_DIR, DESTINATION_DIR, TTL_DIR)
    update_source_yaml_with_related_entities("/home/hide/Documents/Heidi2workspace/heidi2/publish", "/home/hide/quartz/content")