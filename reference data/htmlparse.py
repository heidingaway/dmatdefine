import requests
import re
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, DCTERMS

sourceURL = "https://www.csps-efpc.gc.ca/tools/jobaids/data-competency-framework-eng.aspx"
output_file = "gc_data_competency_framework_dcterms.ttl"

def parse_competency_definitions(url):
    definitions = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        current_category = ""
        current_sub_category = ""
        current_level = ""

        for tag in soup.find_all(['h2', 'h3', 'summary', 'p']):
            if tag.name == 'h2' and tag.get('id', '').startswith('tb_'):
                current_category = tag.get_text(strip=True)
            elif tag.name == 'h3' and tag.get('id', '').startswith('tb_'):
                current_sub_category = tag.get_text(strip=True)
            elif tag.name == 'summary':
                current_level = tag.get_text(strip=True)
            elif tag.name == 'p':
                match = re.match(r'^(\d+\.\d+\.\d+)\s+(.*)', tag.get_text(strip=True))
                if match:
                    item_id = match.group(1)
                    description = match.group(2)
                    definitions.append({
                        'category': current_category,
                        'sub_category': current_sub_category,
                        'level': current_level,
                        'item_id': item_id,
                        'description': description
                    })
    except Exception as e:
        print(f"Error parsing content: {e}")
    return definitions

def clean_uri_component(text):
    return re.sub(r'_+', '_', re.sub(r'[^a-zA-Z0-9_]', '_', text)).strip('_')

def serialize_to_rdf(definitions):
    g = Graph()
    CSPS = Namespace("https://www.csps-efpc.gc.ca/tools/jobaids/#")
    g.bind("csps", CSPS)
    g.bind("dcterms", DCTERMS)
    g.bind("rdfs", RDFS)

    subject_entities = {}
    subcategory_entities = {}

    # Create top-level framework entity
    framework_uri = URIRef("https://www.csps-efpc.gc.ca/tools/jobaids/#data-competency-framework")
    g.add((framework_uri, RDF.type, URIRef("http://purl.org/dc/terms/Subject")))
    g.add((framework_uri, DCTERMS.title, Literal("GC Data Competency Framework", lang='en')))

    for item in definitions:
        term_id = clean_uri_component(item['item_id'])
        concept_uri = URIRef(CSPS[term_id])
        g.add((concept_uri, RDF.type, RDFS.Resource))
        g.add((concept_uri, DCTERMS.identifier, Literal(item['item_id'])))
        g.add((concept_uri, RDFS.label, Literal(item['description'], lang='en')))

        # Add level as URI in CSPS namespace
        level_id = clean_uri_component(item['level'])
        level_uri = URIRef(CSPS[level_id])
        g.add((concept_uri, DCTERMS.audience, level_uri))

        subject_key = item['category']
        subject_id = clean_uri_component(subject_key)
        subject_uri = URIRef(CSPS[f"{subject_id}"])

        if subject_key not in subject_entities:
            g.add((subject_uri, RDF.type, URIRef("http://purl.org/dc/terms/Subject")))
            g.add((subject_uri, DCTERMS.title, Literal(subject_key, lang='en')))
            g.add((subject_uri, DCTERMS.isPartOf, framework_uri))
            subject_entities[subject_key] = subject_uri

        subcat_key = item['sub_category']
        subcat_id = clean_uri_component(subcat_key)
        subcat_uri = URIRef(CSPS[f"{subcat_id}"])

        if subcat_key not in subcategory_entities:
            g.add((subcat_uri, RDF.type, RDFS.Class))
            g.add((subcat_uri, RDFS.label, Literal(subcat_key, lang='en')))
            g.add((subcat_uri, RDFS.subClassOf, subject_uri))
            subcategory_entities[subcat_key] = subcat_uri

        g.add((concept_uri, DCTERMS.subject, subcat_uri))

    return g

if __name__ == "__main__":
    definitions = parse_competency_definitions(sourceURL)
    rdf_graph = serialize_to_rdf(definitions)
    rdf_graph.serialize(destination=output_file, format='turtle')
    print(f"RDF data saved to {output_file}")
