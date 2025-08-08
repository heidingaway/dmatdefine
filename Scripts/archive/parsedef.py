import requests, re
from bs4 import BeautifulSoup
from rdflib import Graph, Literal, URIRef, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

source = "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=28108"


def parse_html_definitions(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        terms = soup.find_all('dt')
        definitions = soup.find_all('dd')
        
        parsed_definitions = []
        for term, definition in zip(terms, definitions):
            english_term = term.strong.get_text(strip=True) if term.strong else term.get_text(strip=True)
            english_term = re.sub(r'\s+', ' ', english_term).strip()
            french_span = term.find('span', lang='fr-CA')
            french_term = french_span.get_text(strip=True) if french_span else None
            if french_term:
                    french_term = re.sub(r'\s+', ' ', french_term).strip()

            definition_text = definition.get_text(strip=True)
            definition_text = re.sub(r'\s+', ' ', definition_text).strip()
            
            parsed_definitions.append({
                'english_term': english_term,
                'french_term': french_term,
                'definition': definition_text
            })
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
    return parsed_definitions

def serialize_to_rdf(definitions_data):

    g = Graph()

    # Define custom namespace for the definitions
    TBS = Namespace("https://www.tbs-sct.canada.ca/pol/#")
    g.bind("tbspol", TBS)
    g.bind("skos", SKOS)
    g.bind("rdfs", RDFS)

    for def_item in definitions_data:
        term_en = def_item['english_term']
        term_fr = def_item['french_term']
        definition_en = def_item['definition']

        # Create a URI for the concept based on the English term
        # Sanitize term for URI (replace spaces with underscores, remove special chars)
        concept_uri_name = re.sub(r'[^a-zA-Z0-9_]', '', term_en.replace(' ', '_'))
        concept_uri = URIRef(TBS[concept_uri_name])

        # Add triples
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, RDFS.label, Literal(term_en, lang='en'))) # English label with @en

        if term_fr:
            g.add((concept_uri, RDFS.label, Literal(term_fr, lang='fr'))) # French label with @fr
        
        g.add((concept_uri, SKOS.definition, Literal(definition_en, lang='en')))


    return g

a = parse_html_definitions(source)
output = "CDO\\directive_opengov"

t = serialize_to_rdf(a).serialize(output, format='turtle')


