import pandas as pd 
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDFS, RDF, OWL, DCTERMS
from urllib.parse import quote
import re

data = "open_datasets\\department_names.csv"

df = pd.read_csv(data)

# Create an RDFLib Graph
g = Graph()

# Define a base URI for your entities
base_uri = "https://www.canada.ca/#"

# Clean URI

def clean_for_uri(text):
    """
    Cleans a string to be more suitable for a URI part by:
    - Converting to lowercase
    - Replacing spaces and common separators with underscores
    - Removing any character not alphanumeric or underscore
    - Stripping leading/trailing underscores
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special characters with underscores
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    # Remove consecutive underscores
    text = re.sub(r'_{2,}', '_', text)
    return text

# Iterate through entities and create RDF triples

for index, row in df.iterrows():
    entitydf_uri = URIRef(base_uri + clean_for_uri(row['harmonized_name']))
    g.add((entitydf_uri, SKOS.prefLabel, Literal(row['harmonized_name'], lang = 'en')))
    g.add((entitydf_uri, SKOS.prefLabel, Literal(row['nom_harmonisé'], lang = 'fr')))
    g.add((entitydf_uri, RDFS.seeAlso, Literal(row['website'])))
    g.add((entitydf_uri, DCTERMS.identifier, Literal(row['gc_orgID']) ))

# Serialize the graph to Turtle format
GC = base_uri
g.bind("gc", GC)

# Serialize the graph to a Turtle file

output_file = "git\\dmatdefine\\ttl\\Source files\\dept_names.ttl"

try:
    g.serialize(destination=output_file, format='turtle')
    print(f"Graph successfully saved to {output_file}")
except Exception as e:
    print(f"An error occurred: {e}")

