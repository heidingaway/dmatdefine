import rdflib
from rdflib import Graph, Literal, URIRef, BNode
from rdflib.namespace import FOAF, RDF, RDFS, SKOS, XSD
import os
import yaml
from datetime import datetime

# Global dictionary to map BNode IDs to human-readable names
# This is crucial for consistent naming across different references to the same BNode.
BLANK_NODE_NAMES = {}
BLANK_NODE_COUNTER = 0

def get_blank_node(bnode_ref, graph):
    """
    Generates or retrieves a consistent human-readable name for a blank node.
    Prioritizes labels/types if available, otherwise uses an incremental counter.
    """
    global BLANK_NODE_COUNTER
    if bnode_ref in BLANK_NODE_NAMES:
        return BLANK_NODE_NAMES[bnode_ref]

    # Attempt to derive a name from properties of the blank node itself
    # (Less likely to have direct labels on unionOf blank nodes, but good practice)
    labels = list(graph.objects(bnode_ref, RDFS.label))
    en_labels = [str(l) for l in labels if l.language == 'en']
    if en_labels:
        name = en_labels[0]
        BLANK_NODE_NAMES[bnode_ref] = name
        return name

    # Try to get the type(s) of the blank node
    types = list(graph.objects(bnode_ref, RDF.type))
    if types:
        type_names = []
        for t in types:
            # Get display name for the type, prioritizing QName or label
            type_display = get_display_name(graph, t, for_filename=False) # Get human name for the type
            type_names.append(type_display)
        name = "BlankNode_" + "_".join(type_names) # Combine type names
        BLANK_NODE_NAMES[bnode_ref] = name
        return name


    # Fallback to an incremental counter
    BLANK_NODE_COUNTER += 1
    name = f"BlankNode_{BLANK_NODE_COUNTER}"
    BLANK_NODE_NAMES[bnode_ref] = name
    return name

def qname_or_uri(graph, uri_ref, for_yaml_key=False, for_filename=False):
    """
    Returns the QName for a URI if available, otherwise the full URI string.
    If for_yaml_key is True, replaces the colon from the QName with an underscore.
    If for_filename is True, replaces the colon from the QName directly (e.g., 'fr:Word' -> 'frWord').
    Handles BNodes by returning their human-readable name.
    """
    if isinstance(uri_ref, BNode):
        human_name = get_blank_node(uri_ref, graph)
        if for_filename:
            return sanitize_filename(human_name)
        elif for_yaml_key:
            return human_name.replace(' ', '_').replace('-', '_') # Sanitize for YAML key
        else:
            return human_name

    # Only attempt qname for URIRefs
    qname = graph.namespace_manager.qname(uri_ref)
    if qname:
        qname_str = str(qname)
        if for_yaml_key and ':' in qname_str:
            return qname_str.replace(':', '_')
        if for_filename and ':' in qname_str:
            return qname_str.replace(':', '') # Remove colon entirely for filename
        return qname_str

    # If no QName found, fallback to URI splitting (only for URIRefs)
    return str(uri_ref).split('/')[-1].split('#')[-1] if '#' in str(uri_ref) or '/' in str(uri_ref) else str(uri_ref)

def get_display_name(graph, uri_ref, for_filename=False):
    """
    Attempts to find a human-readable display name for a URI or BNode.
    If for_filename is True, it prioritizes a 'prefixLocalName' style name if a QName exists.
    Handles BNodes by returning a human-readable name.
    """
    if isinstance(uri_ref, BNode):
        return get_blank_node(uri_ref, graph)

    # 1. Prioritize 'prefixLocalName' style filename if requested and QName exists
    if for_filename:
        qname_name = qname_or_uri(graph, uri_ref, for_filename=True)
        # Check if it's a valid QName (not a full URI, which would start with http/https)
        if qname_name and not qname_name.startswith('http'):
            return qname_name # e.g., "frWord", "frAdverb"

    # 2. Fallback to rdfs:label for display (Markdown H1)
    # Prefer English label if available, otherwise any label.
    labels = list(graph.objects(uri_ref, RDFS.label))
    en_labels = [str(l) for l in labels if l.language == 'en']
    if en_labels:
        return en_labels[0]
    if labels: # If no English, take any available label
        return str(labels[0])

    # 3. Fallback to SKOS prefLabel
    pref_labels = list(graph.objects(uri_ref, SKOS.prefLabel))
    en_pref_labels = [str(l) for l in pref_labels if l.language == 'en']
    if en_pref_labels:
        return en_pref_labels[0]
    if pref_labels:
        return str(pref_labels[0])

    # 4. Fallback to FOAF name
    foaf_names = list(graph.objects(uri_ref, FOAF.name))
    if foaf_names:
        return str(foaf_names[0])

    # 5. Final fallback to last part of URI or full URI
    # This part should only be reached by URIRefs, as BNodes are handled above.
    uri_part = str(uri_ref).split('/')[-1].split('#')[-1]
    return uri_part if uri_part else str(uri_ref)

def sanitize_filename(name):
    """Sanitizes a string to be suitable for a filename."""
    # Replace problematic characters with underscores
    sanitized = "".join(c if c.isalnum() or c in ['-', '_', '.'] else '_' for c in name)
    # Replace multiple underscores with single ones
    sanitized = '_'.join(filter(None, sanitized.split('_')))
    # Remove any leading/trailing underscores or hyphens
    sanitized = sanitized.strip('-_')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "untitled_resource"
    return sanitized

def rdf_to_markdown_with_yaml(ttl_file_path, output_dir="french_grammar_notes"):
    """
    Converts an RDF Turtle file into Markdown notes with YAML front matter,
    creating a separate file for each main subject/resource.
    """
    g = Graph()
    try:
        g.parse(ttl_file_path, format="turtle")
        print(f"Successfully parsed {ttl_file_path}")
    except Exception as e:
        print(f"Error parsing RDF file: {e}: {e}")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Reset blank node counter and names for each new graph processing
    global BLANK_NODE_COUNTER
    global BLANK_NODE_NAMES
    BLANK_NODE_COUNTER = 0
    BLANK_NODE_NAMES = {}

    # Identify main subjects (those that appear as subjects of triples)
    subjects = sorted(list(set(s for s, p, o in g if isinstance(s, URIRef) or isinstance(s, BNode))))

    for s in subjects:
        front_matter = {}
        markdown_body = []

        # Get a display name for the Markdown heading (prioritizes rdfs:label, not stripped QName)
        note_title_display = get_display_name(g, s, for_filename=False)

        # Get the filename-specific name (prioritizes stripped QName or human-readable BNode name)
        filename_base = get_display_name(g, s, for_filename=True)
        sanitized_filename = sanitize_filename(filename_base)

        markdown_body.append(f"# {note_title_display}\n")
        markdown_body.append(f"**URI/ID:** {str(s)}\n")

        # Process properties for YAML front matter
        for p, o in g.predicate_objects(s):
            pred_key = qname_or_uri(g, p, for_yaml_key=True)

            # Special handling for rdf:type, linking to classes
            if p == RDF.type:
                # Use display name for the link text itself (e.g., "Adverb" or "Blank Node 1")
                type_display_name = get_display_name(g, o, for_filename=False)
                # Use the filename-style name for the internal link target (e.g., "frAdverb" or "BlankNode1")
                type_filename_target = get_display_name(g, o, for_filename=True)

                if "rdfType" not in front_matter:
                    front_matter["rdfType"] = []
                # Only create an internal link if the object is a URIRef or BNode that is also a subject in our graph
                if (isinstance(o, URIRef) or isinstance(o, BNode)) and o in subjects:
                    front_matter["rdfType"].append(f"[[{type_filename_target}]]")
                else:
                    front_matter["rdfType"].append(type_display_name if type_display_name else str(o))
                continue

            # Prepare value for YAML
            yaml_value = None
            if isinstance(o, Literal):
                if o.datatype == XSD.date:
                    try:
                        yaml_value = datetime.strptime(str(o), '%Y-%m-%d').strftime('%Y-%m-%d')
                    except ValueError:
                        yaml_value = str(o)
                elif o.datatype == XSD.gYear:
                    yaml_value = str(o)
                elif o.language:
                    # For strings with language tags, format them as "value@lang"
                    yaml_value = f"{str(o)}@{o.language}"
                else:
                    yaml_value = str(o)
            elif isinstance(o, URIRef):
                # If the object is a URIRef and also a subject we're processing, create an internal link
                if o in subjects:
                    obj_display_name = get_display_name(g, o, for_filename=False) # Display for link
                    obj_filename_target = get_display_name(g, o, for_filename=True) # Filename for link
                    yaml_value = f"[[{obj_filename_target}]]" # Use the filename-style name for the internal link target
                else:
                    yaml_value = str(o)
            elif isinstance(o, BNode):
                # For blank nodes in YAML, we'll use their human-readable name for potential linking,
                # as they are now treated as subjects with their own notes.
                bnode_display_name = get_display_name(g, o, for_filename=False) # Human-readable display
                bnode_filename_target = get_display_name(g, o, for_filename=True) # Filename for link
                if o in subjects: # If this BNode is also a subject with its own note
                     yaml_value = f"[[{bnode_filename_target}]]"
                else: # If it's just an object, still use the human-readable name, but not as a link
                     yaml_value = bnode_display_name


            # Add to front matter. Handle multiple values for the same predicate.
            if pred_key in front_matter:
                if not isinstance(front_matter[pred_key], list):
                    front_matter[pred_key] = [front_matter[pred_key]]
                front_matter[pred_key].append(yaml_value)
            else:
                front_matter[pred_key] = yaml_value

        # Construct the final Markdown content
        full_content = []
        if front_matter:
            full_content.append("---\n")
            # Use safe_dump for YAML to prevent issues with complex strings
            full_content.append(yaml.dump(front_matter, allow_unicode=True, default_flow_style=False, sort_keys=False))
            full_content.append("---\n\n")

        full_content.extend(markdown_body)

        # Save the note
        output_file_path = os.path.join(output_dir, f"{sanitized_filename}.md")

        try:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write("".join(full_content))
            print(f"Created note: {output_file_path}")
        except Exception as e:
            print(f"Error writing file {output_file_path}: {e}")


# --- How to use the function ---
ttl_filename = "rdf/french.ttl"

rdf_to_markdown_with_yaml(ttl_filename, output_dir="french_grammar_notes")
