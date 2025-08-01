import os
import glob
import shutil
import re
from rdflib import Graph, URIRef, Literal 
from urllib.parse import urlparse
import yaml

# --- Configuration ---
SOURCE_DIR = "/home/hide/Documents/Heidi2workspace/heidi2/publish"
DESTINATION_DIR = "/home/hide/quartz/content"
TTL_DIR = "/home/hide/Documents/Heidi2workspace/ttl_publish"
DRAFT_STATUS = "false"
BASE_URI = "https://heidingaway.github.io/heidi2/"

# --- Define common predicate types for clear separation ---
# These are properties whose values you want to display *inside* a Mermaid node.
LITERAL_PROPERTIES_FOR_NODE_DISPLAY = {"birthDate", "nationality", "type", "field", "description"} 
# Removed "name" from here. "name" is usually the primary label and will be used as the main node text.

# These are predicates that represent relationships *between* entities and should be drawn as Mermaid edges.
RELATIONSHIP_PREDICATES = {"creator", "subject", "seeAlso", "hasTopic", "title", "influencedBy", "hasField"} 
# Added "influencedBy" and "hasField" here.

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

def get_uri_last_part(uri: str) -> str:
    """
    Helper function to extract the last part of a URI (after '#' or '/')
    or return a literal, and then sanitize it for Mermaid.
    """
    try:
        parsed_uri = urlparse(uri)
        if parsed_uri.fragment:
            label = parsed_uri.fragment
        else:
            path_parts = parsed_uri.path.split('/')
            label = next((part for part in reversed(path_parts) if part), uri)
            if not label and parsed_uri.netloc:
                label = parsed_uri.netloc
    except Exception:
        label = uri

    return get_mermaid_safe_label(label)

def find_entities_in_ttl(filename: str, ttl_files: list) -> tuple[list, Graph]:
    """
    Finds entities in TTL files that have the given filename as part of a URI.
    Returns a list of unique predicate-object or predicate-subject pairs with full URIs,
    and the loaded RDF graph.
    """
    entities = []
    g = Graph()
    
    for ttl_file in ttl_files:
        try:
            g.parse(ttl_file, format="turtle")
        except Exception as e:
            print(f"Error parsing {ttl_file}: {e}")
            continue
    
    file_uri_ref = None
    for s, p, o in g:
        s_last_part = get_uri_last_part(str(s)).lower()
        o_last_part = get_uri_last_part(str(o)).lower()
        
        if s_last_part == filename.lower():
            file_uri_ref = s
            break
        elif o_last_part == filename.lower():
            file_uri_ref = o
            break

    if not file_uri_ref:
        print(f"DEBUG: No URI found for filename '{filename}' in TTL files.")
        return [], g

    print(f"DEBUG: Found URI for '{filename}': {file_uri_ref}")

    for s, p, o in g.triples((file_uri_ref, None, None)):
        entities.append({
            "relationship": str(p),
            "entity": str(o)
        })
        print(f"DEBUG: Direct triple found: {s} {p} {o}")

    for s, p, o in g.triples((None, None, file_uri_ref)):
        entities.append({
            "inverse_relationship": str(p),
            "entity": str(s)
        })
        print(f"DEBUG: Inverse triple found: {s} {p} {o}")

    return entities, g

def get_entity_properties_for_mermaid(graph: Graph, entity_uri: str) -> str:
    """
    Queries the graph for direct properties of a given entity URI
    and formats them as plain text for Mermaid node display.
    Only includes properties from LITERAL_PROPERTIES_FOR_NODE_DISPLAY.
    """
    properties_list = []
    entity_ref = URIRef(entity_uri)
    
    print(f"DEBUG: Getting properties for entity_uri: {entity_uri}")
    for s, p, o in graph.triples((entity_ref, None, None)):
        prop_name = get_uri_last_part(str(p))
        prop_value = get_uri_last_part(str(o))
        
        # Only add if the predicate is in our defined set for internal node display
        if prop_name in LITERAL_PROPERTIES_FOR_NODE_DISPLAY:
            properties_list.append(f"+ {prop_name}: {prop_value}")
            print(f"DEBUG:   Property added: {prop_name}: {prop_value}")
        else:
            print(f"DEBUG:   Property excluded (not for internal node display): {prop_name}: {prop_value}")
    
    if properties_list:
        return "<br>" + "<br>".join(properties_list)
        
    return ""

def generate_mermaid_syntax(current_page_filename: str, entities: list, graph: Graph) -> str:
    """
    Generates Mermaid graph syntax from a list of entities, including properties,
    and adds an additional layer of depth, preventing duplicate nodes and edges.
    """
    current_page_id = re.sub(r'[^a-zA-Z0-9_]', '', current_page_filename.replace(" ", "_").replace("-", "_"))
    
    mermaid_syntax_lines = ["graph TD"]
    nodes_in_graph = set() # Stores IDs of nodes already added to the graph syntax
    edges_in_graph = set() # Stores (source_id, predicate_label, target_id) tuples for unique edges
    nodes_to_process_for_depth = set() # Stores URIs of nodes whose relationships we need to explore

    # --- First Layer: Current Page and its Direct Connections ---
    current_page_full_uri = None
    for s, p, o in graph.triples((None, None, None)):
        s_last_part = get_uri_last_part(str(s)).lower()
        o_last_part = get_uri_last_part(str(o)).lower()

        if s_last_part == current_page_filename.lower():
            current_page_full_uri = s
            break
        elif o_last_part == current_page_filename.lower():
            current_page_full_uri = o
            break
            
    if not current_page_full_uri:
        current_page_full_uri = URIRef(f"{BASE_URI}{current_page_filename.replace(' ', '_')}")
        print(f"DEBUG: Current page URI not found in graph, using fallback: {current_page_full_uri}")

    current_page_properties = get_entity_properties_for_mermaid(graph, str(current_page_full_uri))
    
    nodes_in_graph.add(current_page_id)
    # The main page's label should just be its filename, as its properties are handled by properties_list
    mermaid_syntax_lines.append(f"  {current_page_id}[\"{get_mermaid_safe_label(current_page_filename)}{current_page_properties}\"]")
    nodes_to_process_for_depth.add(str(current_page_full_uri))
    print(f"DEBUG: Current page node syntax: {mermaid_syntax_lines[-1]}")

    for rel in entities:
        entity_uri = rel.get("entity", "")
        entity_label = get_uri_last_part(entity_uri)
        entity_id = re.sub(r'[^a-zA-Z0-9_]', '', entity_label.replace(" ", "_").replace("-", "_"))

        if entity_id not in nodes_in_graph:
            nodes_in_graph.add(entity_id)
            related_entity_properties = get_entity_properties_for_mermaid(graph, entity_uri)
            mermaid_syntax_lines.append(f"  {entity_id}[\"{entity_label}{related_entity_properties}\"]")
            nodes_to_process_for_depth.add(entity_uri)
            print(f"DEBUG:   Related entity node syntax (1st layer): {mermaid_syntax_lines[-1]}")

        predicate_label = ""
        source_node_id = ""
        target_node_id = ""

        if "relationship" in rel:
            predicate_label = get_uri_last_part(rel["relationship"])
            source_node_id = current_page_id
            target_node_id = entity_id
        elif "inverse_relationship" in rel:
            predicate_label = get_uri_last_part(rel["inverse_relationship"])
            source_node_id = entity_id
            target_node_id = current_page_id
        
        # Only add edge if the predicate is a defined relationship
        if predicate_label in RELATIONSHIP_PREDICATES:
            edge_tuple = (source_node_id, predicate_label, target_node_id)
            if edge_tuple not in edges_in_graph:
                edges_in_graph.add(edge_tuple)
                mermaid_syntax_lines.append(f"  {source_node_id}-->|\" {predicate_label} \"|{target_node_id}")
                print(f"DEBUG:   Relationship added (1st layer): {source_node_id} --> {target_node_id} ({predicate_label})")
            else:
                print(f"DEBUG:   Skipping duplicate relationship (1st layer): {source_node_id} --> {target_node_id} ({predicate_label})")
        else:
            print(f"DEBUG:   Skipping predicate (not a defined relationship): {predicate_label}")


    # --- Second Layer: Relationships of First-Layer Entities ---
    print(f"\nDEBUG: Exploring second layer of depth for {len(nodes_to_process_for_depth)} entities.")
    for source_entity_uri_str in list(nodes_to_process_for_depth):
        source_entity_ref = URIRef(source_entity_uri_str)
        source_entity_label = get_uri_last_part(source_entity_uri_str)
        source_entity_id = re.sub(r'[^a-zA-Z0-9_]', '', source_entity_label.replace(" ", "_").replace("-", "_"))

        # Find direct relationships FROM this source_entity_ref
        for s2, p2, o2 in graph.triples((source_entity_ref, None, None)):
            target_entity_uri = str(o2)
            target_entity_label = get_uri_last_part(target_entity_uri)
            target_entity_id = re.sub(r'[^a-zA-Z0-9_]', '', target_entity_label.replace(" ", "_").replace("-", "_"))
            predicate2_label = get_uri_last_part(str(p2))

            # Only add an edge if the predicate is a defined relationship predicate
            if predicate2_label in RELATIONSHIP_PREDICATES:
                if target_entity_id not in nodes_in_graph:
                    nodes_in_graph.add(target_entity_id)
                    target_entity_properties = get_entity_properties_for_mermaid(graph, target_entity_uri)
                    mermaid_syntax_lines.append(f"  {target_entity_id}[\"{target_entity_label}{target_entity_properties}\"]")
                    print(f"DEBUG:     Related entity node syntax (2nd layer): {mermaid_syntax_lines[-1]}")
                
                edge_tuple = (source_entity_id, predicate2_label, target_entity_id)
                if edge_tuple not in edges_in_graph:
                    edges_in_graph.add(edge_tuple)
                    mermaid_syntax_lines.append(f"  {source_entity_id}-->|\" {predicate2_label} \"|{target_entity_id}")
                    print(f"DEBUG:     2nd layer direct relationship: {source_entity_id} --> {target_entity_id} ({predicate2_label})")
                else:
                    print(f"DEBUG:     Skipping duplicate relationship (2nd layer): {source_entity_id} --> {target_entity_id} ({predicate2_label})")
            else:
                print(f"DEBUG:     Skipping predicate (not a defined relationship) in 2nd layer direct: {predicate2_label}")

        # Find inverse relationships TO this source_entity_ref
        for s2, p2, o2 in graph.triples((None, None, source_entity_ref)):
            source_entity_inverse_uri = str(s2)
            source_entity_inverse_label = get_uri_last_part(source_entity_inverse_uri)
            source_entity_inverse_id = re.sub(r'[^a-zA-Z0-9_]', '', source_entity_inverse_label.replace(" ", "_").replace("-", "_"))
            predicate2_label = get_uri_last_part(str(p2))

            # Only add an edge if the predicate is a defined relationship predicate
            if predicate2_label in RELATIONSHIP_PREDICATES:
                if source_entity_inverse_id not in nodes_in_graph:
                    nodes_in_graph.add(source_entity_inverse_id)
                    source_entity_inverse_properties = get_entity_properties_for_mermaid(graph, source_entity_inverse_uri)
                    mermaid_syntax_lines.append(f"  {source_entity_inverse_id}[\"{source_entity_inverse_label}{source_entity_inverse_properties}\"]")
                    print(f"DEBUG:     Related entity node syntax (2nd layer inverse): {mermaid_syntax_lines[-1]}")
                
                edge_tuple = (source_entity_inverse_id, predicate2_label, source_entity_id)
                if edge_tuple not in edges_in_graph:
                    edges_in_graph.add(edge_tuple)
                    mermaid_syntax_lines.append(f"  {source_entity_inverse_id}-->|\" {predicate2_label} \"|{source_entity_id}")
                    print(f"DEBUG:     2nd layer inverse relationship: {source_entity_inverse_id} --> {source_entity_id} ({predicate2_label})")
                else:
                    print(f"DEBUG:     Skipping duplicate relationship (2nd layer inverse): {source_entity_inverse_id} --> {source_entity_id} ({predicate2_label})")
            else:
                print(f"DEBUG:     Skipping predicate (not a defined relationship) in 2nd layer inverse: {predicate2_label}")
            
    return "\n".join(mermaid_syntax_lines)

def process_markdown_file(file_path: str, filename: str, entities_data: dict, graph: Graph):
    """
    Adds or updates YAML frontmatter and appends Mermaid syntax to a markdown file.
    Ensures only one Mermaid block is present.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    existing_frontmatter = {}
    markdown_body = content
    
    # Extract existing YAML frontmatter
    if content.startswith("---"):
        try:
            yaml_end_index = content.find("---", 3)
            if yaml_end_index != -1:
                yaml_str = content[3:yaml_end_index].strip()
                existing_frontmatter = yaml.safe_load(yaml_str) or {}
                markdown_body = content[yaml_end_index + 3:].strip()
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}. Treating as no existing frontmatter.")
            pass

    # --- Remove existing Mermaid block if present ---
    mermaid_block_pattern = re.compile(
        r'(?:^---\s*\n)?' # Optional leading ---
        r'(?:^###\s*Semantic\s*Connections\s*\n+)?' # Optional Semantic Connections heading with one or more newlines
        r'^```mermaid\s*\n' # Start of mermaid block
        r'.*?' # Non-greedy match for content
        r'\n^```\s*$' # End of mermaid block (newline then ``` at start of line)
        , re.DOTALL | re.MULTILINE
    )
    
    markdown_body = mermaid_block_pattern.sub('', markdown_body).strip()

    # --- Manage title and aliases ---
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
    
    merged_frontmatter = {**existing_frontmatter, **entities_data, "draft": DRAFT_STATUS}
    
    # Generate NEW Mermaid syntax block
    mermaid_syntax_block = ""
    if entities_data.get("entities"):
        mermaid_syntax_content = generate_mermaid_syntax(filename, entities_data["entities"], graph)
        mermaid_syntax_block = f"\n\n---\n\n### Semantic Connections\n\n```mermaid\n{mermaid_syntax_content}\n```"

    # Reconstruct the file content
    new_content = f"---\n{yaml.dump(merged_frontmatter, sort_keys=False)}---\n\n{markdown_body}{mermaid_syntax_block}"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

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

    md_files = glob.glob(os.path.join(source, "**/*.md"), recursive=True)

    for md_file_path in md_files:
        print(f"Processing {md_file_path}...")
        
        filename_with_ext = os.path.basename(md_file_path)
        filename = os.path.splitext(filename_with_ext)[0]

        entities_list, _ = find_entities_in_ttl(filename, ttl_files)
        
        entity_yaml_data = {"entities": entities_list}
        
        process_markdown_file(md_file_path, filename, entity_yaml_data, g) 

    print(f"\nCopying files from {source} to {destination}...")
    
    for md_file_path in md_files:
        relative_path = os.path.relpath(md_file_path, source)
        dest_file_path = os.path.join(destination, relative_path)
        
        os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
        shutil.copy2(md_file_path, dest_file_path)
        
    print("Preprocessing complete!")

if __name__ == "__main__":
    preprocess_files(SOURCE_DIR, DESTINATION_DIR, TTL_DIR)