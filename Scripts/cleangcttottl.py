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
    text = text.lower()  # Convert to lowercase
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    uri_id = re.sub(r'[\s",?#\[\]\(\)\+\'/]', '_', text)
    uri_id = re.sub(r'_{2,}', '_', uri_id)
    return uri_id.strip('_')

def convert_csv_to_ttl(input_csv_path, output_ttl_path):
    """
    Reads a CSV thesaurus in a triple-like format, converts it to a complete RDF graph,
    and saves it as a Turtle file.
    """
    try:
        print(f"Reading CSV from {input_csv_path}...")
        
        # First Pass: Read data to build a mapping and identify collections
        terms_to_uri = {}
        collections = {}
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) == 3:
                    subject, predicate, obj = row
                    terms_to_uri[subject] = gct[generate_uri_id(subject)]
                    if predicate in ["Use", "Broader Term", "Narrower Term", "Related Term", "Subject Category"]:
                        terms_to_uri[obj] = gct[generate_uri_id(obj)]
                        if predicate == "Subject Category":
                            if obj not in collections:
                                collections[obj] = []
                            collections[obj].append(terms_to_uri[subject])

        g = Graph()
        g.bind("skos", skos)
        g.bind("gct", gct)
        g.bind("dc", dc)
        
        concept_scheme_uri = gct[""]
        g.add((concept_scheme_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.ConceptScheme))
        g.add((concept_scheme_uri, dc.title, Literal("Government of Canada Core Subject Thesaurus", lang='en')))

        for category_term, members in collections.items():
            category_uri = terms_to_uri[category_term]
            g.add((category_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))
            g.add((category_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Collection))
            g.add((category_uri, skos.inScheme, concept_scheme_uri))
            g.add((category_uri, skos.prefLabel, Literal(f"{category_term}", lang='en')))
            
            for member_uri in members:
                g.add((category_uri, skos.member, member_uri))

        # Second Pass: Process relationships and build the graph
        print("Processing relationships and building the graph...")
        with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) == 3:
                    subject_term, predicate_str, object_term = row
                    
                    if subject_term in terms_to_uri:
                        subject_uri = terms_to_uri[subject_term]
                        
                        if predicate_str != "Subject Category":
                             g.add((subject_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))

                        if predicate_str == "French":
                            g.add((subject_uri, skos.prefLabel, Literal(object_term, lang='fr')))
                        elif predicate_str == "English":
                            g.add((subject_uri, skos.prefLabel, Literal(object_term, lang='en')))
                        elif predicate_str == "Use":
                            object_uri = terms_to_uri[object_term]
                            g.add((object_uri, skos.altLabel, Literal(subject_term, lang='en')))
                            g.add((subject_uri, skos.related, object_uri))
                            g.add((object_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))
                        elif predicate_str == "Used For":
                            g.add((subject_uri, skos.altLabel, Literal(object_term, lang='en')))
                        elif predicate_str == "Scope Note":
                            g.add((subject_uri, skos.scopeNote, Literal(object_term, lang='en')))
                        elif predicate_str == "Broader Term":
                            object_uri = terms_to_uri[object_term]
                            g.add((subject_uri, skos.broader, object_uri))
                            g.add((object_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))
                        elif predicate_str == "Narrower Term":
                            object_uri = terms_to_uri[object_term]
                            g.add((subject_uri, skos.narrower, object_uri))
                            g.add((object_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))
                        elif predicate_str == "Related Term":
                            object_uri = terms_to_uri[object_term]
                            g.add((subject_uri, skos.related, object_uri))
                            g.add((object_uri, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), skos.Concept))
                        elif predicate_str == "Subject Category":
                            pass
                            
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
    output_ttl_path = "/home/hide/Documents/Heidi2workspace/ttl_publish/gc_thesaurus.ttl"

    convert_csv_to_ttl(input_csv_path, output_ttl_path)