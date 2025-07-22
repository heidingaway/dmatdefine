import rdflib
from rdflib import BNode
import csv
import re

def get_label_from_uri(uri_node):
    """
    Extracts a human-readable label from an RDFLib URI or BNode.
    Prioritizes text after '#' or '/', then removes query parameters.
    Handles BNode IDs.
    """
    uri_str = str(uri_node)
    
    if isinstance(uri_node, BNode):
        return f"BlankNode_{uri_str.replace(':', '_').replace('.', '_')}" 
    
    label = uri_str
    if "#" in uri_str:
        label = uri_str.rsplit("#", 1)[-1]
    elif "/" in uri_str:
        label = uri_str.rsplit("/", 1)[-1]
   
    label = re.sub(r'[^\w\s-]', '', label)
    label = label.strip()
    label = re.sub(r'\s+', '_', label)
    
    return label

def rdf_to_csv(rdf_file_path, csv_file_path):
    # Load RDF graph
    g = rdflib.Graph()
    g.parse(rdf_file_path, format=rdflib.util.guess_format(rdf_file_path))

    # Open CSV file for writing
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['Subject', 'Predicate', 'Object'])  # Header

        # Write each triple to the CSV with cleaned labels
        for subj, pred, obj in g:
            subj_label = get_label_from_uri(subj)
            pred_label = get_label_from_uri(pred)
            obj_label = get_label_from_uri(obj) if isinstance(obj, (rdflib.URIRef, BNode)) else str(obj)
            writer.writerow([subj_label, pred_label, obj_label])

    print(f"RDF data from '{rdf_file_path}' has been written to '{csv_file_path}' with cleaned labels.")

# Example usage
rdf_to_csv('gc_data_competency_framework_dcterms.ttl', 'competency_output.csv')
