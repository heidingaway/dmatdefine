import csv
from rdflib import Graph, Literal, Namespace, URIRef
import re
import unicodedata

# Define namespaces for SKOS, the thesaurus, and Dublin Core
skos = Namespace("http://www.w3.org/2004/02/skos/core#")
gct = Namespace("http://www.thesaurus.gc.ca/#")
dc = Namespace("http://purl.org/dc/elements/1.1/")

def generate_uri_id(text):
    """
    Generates a URI-safe string by converting to lowercase and replacing
    special characters, accents, and quotes.
    """
    text = str(text)
    text = text.lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    uri_id = re.sub(r'[\s",?#\[\]\(\)\+\'/]', '_', text)
    uri_id = re.sub(r'_{2,}', '_', uri_id)
    return uri_id.strip('_')

def clean_term(text):
    """
    Cleans a term string by normalizing Unicode and removing problematic characters.
    This should be applied to the raw text from CSV before further processing.
    """
    text = str(text)
    text = unicodedata.normalize('NFC', text)
    # Remove problematic characters like the Unicode Replacement Character ''
    # and any stray double quotes that might be part of the content but not CSV delimiters
    return text.replace('\ufffd', '').replace('"', '')

def convert_csv_to_ttl(input_csv_path, output_ttl_path):
    """
    Reads a CSV thesaurus in a triple-like format, converts it to a complete RDF graph,
    and saves it as a Turtle file. It ensures all concepts have both an English
    and a French prefLabel.
    """
    try:
        print(f"Reading CSV from {input_csv_path}...")
        
        # --- First Pass: Identify all Concepts and Non-Preferred Terms ---
        concept_terms = set()
        non_preferred_terms = set()
        subject_categories = set()
        
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) == 3:
                    subject_raw, predicate_raw, obj_raw = row
                    
                    subject_term = clean_term(subject_raw)
                    object_term = clean_term(obj_raw)
                    
                    # Assume all subjects are concepts initially
                    concept_terms.add(subject_term)
                    
                    # Add objects of concept-to-concept relationships to the concept list
                    if predicate_raw in ["Broader Term", "Narrower Term", "Related Term", "Subject Category"]:
                        concept_terms.add(object_term)
                    
                    # Mark subjects of "Use" relationships as non-preferred
                    if predicate_raw == "Use":
                        non_preferred_terms.add(subject_term)
                    
                    # Collect all terms that are objects of a 'Subject Category' predicate
                    if predicate_raw == "Subject Category":
                        subject_categories.add(object_term)
        
        # Remove non-preferred terms from the concept list
        concept_terms -= non_preferred_terms
        
        # Now, create a final mapping of concept terms to their URIs
        terms_to_uri = {term: gct[generate_uri_id(term)] for term in concept_terms}
        
        # --- Second Pass: Initialize concepts_data and populate relationships ---
        concepts_data = {}
        
        # Initialize concepts_data for every term that is a concept
        for term_str, uri_ref in terms_to_uri.items():
            concepts_data.setdefault(uri_ref, {
                'type': [skos.Concept],
                'prefLabel': {'en': term_str},
                'relationships': [],
                'altLabel': []
            })
            
        # Re-read the CSV to populate relationships and specific labels
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) == 3:
                    subject_raw, predicate_str, object_raw = row
                    
                    subject_term = clean_term(subject_raw)
                    object_term = clean_term(object_raw)
                    
                    if subject_term in concept_terms:
                        subject_uri = terms_to_uri[subject_term]
                        
                        if predicate_str == "French":
                            concepts_data[subject_uri]['prefLabel']['fr'] = object_term
                        elif predicate_str == "Used For":
                            concepts_data[subject_uri]['altLabel'].append(object_term)
                        elif predicate_str == "Scope Note":
                            concepts_data[subject_uri]['relationships'].append((skos.scopeNote, Literal(object_term, lang='en')))
                        elif predicate_str == "Broader Term":
                            obj_uri = terms_to_uri[object_term]
                            concepts_data[subject_uri]['relationships'].append((skos.broader, obj_uri))
                            # Add the inverse relationship
                            concepts_data[obj_uri]['relationships'].append((skos.narrower, subject_uri))
                        elif predicate_str == "Narrower Term":
                            obj_uri = terms_to_uri[object_term]
                            concepts_data[subject_uri]['relationships'].append((skos.narrower, obj_uri))
                            # Add the inverse relationship
                            concepts_data[obj_uri]['relationships'].append((skos.broader, subject_uri))
                        elif predicate_str == "Related Term":
                            obj_uri = terms_to_uri[object_term]
                            concepts_data[subject_uri]['relationships'].append((skos.related, obj_uri))
                            # For related terms, the inverse is also skos:related
                            concepts_data[obj_uri]['relationships'].append((skos.related, subject_uri))
                        elif predicate_str == "Subject Category":
                            obj_uri = terms_to_uri[object_term]
                            concepts_data[subject_uri]['relationships'].append((skos.broader, obj_uri))
                            # Add the inverse relationship for subject categories
                            concepts_data[obj_uri]['relationships'].append((skos.narrower, subject_uri))

                    # Handle non-preferred terms
                    elif predicate_str == "Use":
                        if object_term in concept_terms:
                            obj_uri = terms_to_uri[object_term]
                            concepts_data[obj_uri].setdefault('altLabel', []).append(subject_term)

        # --- Third Pass: Build the final RDF graph ---
        g = Graph()
        g.bind("skos", skos)
        g.bind("gct", gct)
        g.bind("dc", dc)
        
        concept_scheme_uri = gct[""]
        g.add((concept_scheme_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.ConceptScheme))
        g.add((concept_scheme_uri, dc.title, Literal("Government of Canada Core Subject Thesaurus", lang='en')))

        print("Building the RDF graph...")
        for subject_uri, data in concepts_data.items():
            # Add skos:Collection type to all identified subject categories
            if subject_uri in [terms_to_uri[cat] for cat in subject_categories if cat in terms_to_uri]:
                 data['type'].append(skos.Collection)

            for t in data['type']:
                g.add((subject_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), t))
            
            g.add((subject_uri, skos.inScheme, concept_scheme_uri))
            g.remove((subject_uri, skos.prefLabel, None))
            
            for lang, label in data['prefLabel'].items():
                g.add((subject_uri, skos.prefLabel, Literal(label, lang=lang)))
            
            if 'fr' not in data['prefLabel'] and 'en' in data['prefLabel']:
                g.add((subject_uri, skos.prefLabel, Literal(data['prefLabel']['en'], lang='fr')))

            for alt_label in data['altLabel']:
                g.add((subject_uri, skos.altLabel, Literal(alt_label, lang='en')))

            for predicate, obj in data['relationships']:
                g.add((subject_uri, predicate, obj))

        print(f"\nGraph has {len(g)} triples.")

        print(f"Serializing graph to Turtle and saving to {output_ttl_path}...")
        g.serialize(destination=output_ttl_path, format='turtle')

        print(f"RDF graph successfully saved to {output_ttl_path}")

    except FileNotFoundError:
        print(f"Error: The file '{input_csv_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    input_csv_path = "/home/hide/Documents/Heidi2workspace/CST20250610.csv"
    output_ttl_path = "/home/hide/quartz/heidi2/ttl_publish/gc_thesaurus.ttl"

    convert_csv_to_ttl(input_csv_path, output_ttl_path)