# ==============================================================================
# SCRIPT CONFIGURATION BLOCK
# Change these variables to adapt the script for other articles or text.
# ==============================================================================

# Required: The text content to process.
# Replace this with the article content you want to convert.
PASTED_TEXT = """Policy on Service and Digital has supporting instruments.
Policy on Service and Digital serves as an integrated set of rules on service and digital.
"""

# Required: The filename for the Turtle (.ttl) output.
OUTPUT_FILENAME = "test.ttl"

# Optional: A title for the source when using pasted text.
# This will appear in the generated TTL as the dcterms:title for the source.
PASTED_TEXT_SOURCE_TITLE = "Policy on Service and Digital"

# Optional: A URL to associate with the pasted text as its source.
# This will appear in the generated TTL as the dcterms:source URI.
PASTED_TEXT_SOURCE_URL = "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32603"

# Optional: A publish date for the pasted text source (YYYY-MM-DD format).
# This will appear in the generated TTL as the dcterms:date for the source.
# If set to None, no date will be added.
PASTED_TEXT_SOURCE_DATE = "2025-08-05" # Example: datetime(2024, 8, 5) or "2024-08-05"

# Optional/Advanced: Adjust these for fine-tuning the REBEL model.
# The length of the text chunks processed by the model.
SPAN_LENGTH = 128

# The number of relation candidates the model should return per span.
NUM_RETURN_SEQUENCES = 3

# The name of the REBEL model to use from Hugging Face.
MODEL_NAME = "Babelscape/rebel-large"

# ==============================================================================
# END OF CONFIGURATION BLOCK
# ==============================================================================

# needed to load the REBEL model
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import math
import torch
import warnings
import re 
from datetime import datetime

# wrapper for wikipedia API
import wikipedia
# Suppress the GuessedAtParserWarning from the wikipedia library
try:
    from bs4 import GuessedAtParserWarning
    warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
except ImportError:
    pass

# scraping of web articles (still imported, but not used for main input)
from newspaper import Article, ArticleException

# google news scraping (not used in this version)
from GoogleNews import GoogleNews

# graph visualization (not directly used in this script's output, but part of original intent)
from pyvis.network import Network

# show HTML in notebook (not directly used in this script's output)
import IPython

# RDFLib for serializing to Turtle format
import rdflib
from rdflib import Graph, Literal, RDF, URIRef, BNode
from rdflib.namespace import FOAF, XSD, Namespace, RDFS, DCTERMS

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

def extract_relations_from_model_output(text):
    """
    Parses the output of the REBEL model to extract triplets of subject,
    relation, and object.
    """
    relations = []
    relation, subject, relation, object_ = '', '', '', ''
    text = text.strip()
    current = 'x'
    text_replaced = text.replace("<s>", "").replace("<pad>", "").replace("</s>", "")
    for token in text_replaced.split():
        if token == "<triplet>":
            current = 't'
            if relation != '':
                relations.append({
                    'head': subject.strip(),
                    'type': relation.strip(),
                    'tail': object_.strip()
                })
                relation = ''
            subject = ''
        elif token == "<subj>":
            current = 's'
            if relation != '':
                relations.append({
                    'head': subject.strip(),
                    'type': relation.strip(),
                    'tail': object_.strip()
                })
            object_ = ''
        elif token == "<obj>":
            current = 'o'
            relation = ''
        else:
            if current == 't':
                subject += ' ' + token
            elif current == 's':
                object_ += ' ' + token
            elif current == 'o':
                relation += ' ' + token
    if subject != '' and relation != '' and object_ != '':
        relations.append({
            'head': subject.strip(),
            'type': relation.strip(),
            'tail': object_.strip()
        })
    return relations

class KB():
    """
    A simple knowledge base class to store and manage extracted relations.
    It handles merging of duplicate relations and tracks sources.
    """
    def __init__(self):
        self.entities = {}
        self.relations = []
        self.sources = {}

    def are_relations_equal(self, r1, r2):
        """Checks if two relations are semantically equal (same head, type, tail)."""
        return all(r1[attr] == r2[attr] for attr in ["head", "type", "tail"])

    def exists_relation(self, r1):
        """Checks if a relation already exists in the KB."""
        return any(self.are_relations_equal(r1, r2) for r2 in self.relations)

    def merge_relations(self, r2):
        """
        Merges a new relation (r2) into an existing one (r1) if they are equal.
        It updates the meta data (spans) for the existing relation.
        """
        r1 = [r for r in self.relations
              if self.are_relations_equal(r2, r)][0]

        # Get the article URL from the new relation's meta
        # r2["meta"] is expected to be a dictionary like {article_url: {"spans": [...]}}
        article_url = next(iter(r2["meta"].keys()))

        if article_url not in r1["meta"]:
            # If the article URL is new for this relation, add its metadata
            r1["meta"][article_url] = r2["meta"][article_url]
        else:
            # If the article URL already exists, merge the spans
            spans_to_add = [span for span in r2["meta"][article_url]["spans"]
                            if span not in r1["meta"][article_url]["spans"]]
            r1["meta"][article_url]["spans"].extend(spans_to_add)

    def add_entity(self, entity_title):
        """
        Adds an entity to the KB if it doesn't already exist,
        using its title as the key. No external validation is performed.
        """
        if entity_title not in self.entities:
            self.entities[entity_title] = {} # Store with an empty dict as no other data is fetched

    def add_relation(self, r, article_url, article_title, article_publish_date):
        """
        Adds a relation to the KB. It uses the provided entity titles directly,
        adds new entities and sources, then adds or merges the relation.
        """
        # Entities are now just strings, no external validation or data fetching
        head_entity_title = r["head"]
        tail_entity_title = r["tail"]

        # Add entities to the KB based on their titles
        self.add_entity(head_entity_title)
        self.add_entity(tail_entity_title)

        # Ensure the relation's head and tail are set to the canonical titles
        # (which are the original strings in this simplified model)
        r["head"] = head_entity_title
        r["tail"] = tail_entity_title

        # Handle source information: add new source if not already present
        if article_url not in self.sources:
            self.sources[article_url] = {
                "article_title": article_title,
                "article_publish_date": article_publish_date
            }
        
        # IMPORTANT FIX: Capture the spans from the *incoming* relation 'r'
        # This assumes the 'r' dictionary passed into add_relation has
        # r["meta"] = {"spans": [...]}.
        current_extraction_spans = r["meta"].get("spans", [])

        # Now, correctly set the 'meta' field of the relation 'r'
        # to the structure expected by merge_relations:
        # { "article_url": { "spans": [...] } }
        # This completely overwrites the initial r["meta"] (which only had "spans").
        r["meta"] = {
            article_url: { "spans": current_extraction_spans }
        }

        if not self.exists_relation(r):
            self.relations.append(r)
        else:
            self.merge_relations(r)

    def print(self):
        """Prints the current state of the Knowledge Base."""
        print("Entities:")
        for e_title, e_data in self.entities.items():
            print(f"  - {e_title}: {e_data}")
        print("\nRelations:")
        for r in self.relations:
            print(f"  - {r}")
        print("\nSources:")
        for s_url, s_data in self.sources.items():
            print(f"  - {s_url}: {s_data}")

    def to_ttl(self, filename):
        """
        Serializes the knowledge base into a Turtle (.ttl) file.
        This version correctly formats datetime objects and handles invalid dates.
        """
        g = Graph()

        # Define custom namespaces
        KG = Namespace("http://example.org/knowledge-graph/")
        REL = Namespace("http://example.org/relationship/")
        
        g.bind("kg", KG)
        g.bind("rel", REL)
        g.bind("foaf", FOAF)
        g.bind("dcterms", DCTERMS)
        g.bind("rdfs", RDFS)

        # Helper function to create safe URIs from strings
        def create_safe_uri(text):
            clean_text = text.strip().replace(' ', '_')
            clean_text = re.sub(r'[^a-zA-Z0-9_]', '', clean_text)
            return URIRef(KG[clean_text])

        # Step 1: Add all entities and their metadata to the graph
        for title, data in self.entities.items():
            subject_uri = create_safe_uri(title)
            
            if any(word in title.lower().split() for word in ["company", "organization"]):
                g.add((subject_uri, RDF.type, FOAF.Organization))
            else:
                g.add((subject_uri, RDF.type, RDFS.Resource))
            
            g.add((subject_uri, RDFS.label, Literal(title)))
            
            # These fields are no longer populated from Wikipedia, so check for existence
            if "summary" in data:
                g.add((subject_uri, RDFS.comment, Literal(data["summary"])))
            if "url" in data:
                g.add((subject_uri, FOAF.page, URIRef(data["url"])))

        # Step 2: Add all relations to the graph
        for relation in self.relations:
            head_uri = create_safe_uri(relation["head"])
            tail_uri = create_safe_uri(relation["tail"])
            relation_uri = create_safe_uri(relation["type"])

            g.add((head_uri, relation_uri, tail_uri))

            # Iterate through all sources associated with this relation
            for article_url in relation["meta"].keys():
                g.add((head_uri, DCTERMS.source, URIRef(article_url)))

        # Step 3: Add all sources as a separate set of triples
        for url, data in self.sources.items():
            source_uri = URIRef(url)
            g.add((source_uri, RDF.type, RDFS.Resource))
            g.add((source_uri, DCTERMS.title, Literal(data["article_title"])))
            
            date_value = data.get("article_publish_date")
            # Ensure date_value is a datetime object before formatting
            if isinstance(date_value, datetime):
                date_str = date_value.strftime('%Y-%m-%d')
                g.add((source_uri, DCTERMS.date, Literal(date_str, datatype=XSD.date)))
            # Handle string dates if provided in YYYY-MM-DD format
            elif isinstance(date_value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_value):
                g.add((source_uri, DCTERMS.date, Literal(date_value, datatype=XSD.date)))
        
        # Serialize and save
        g.serialize(destination=filename, format="turtle", encoding='utf-8')
        print(f"Knowledge graph saved to {filename} in Turtle format.")


def from_text_to_kb(text, source_url, span_length, source_title=None,
                    source_publish_date=None, verbose=False):
    """
    Extracts relations from a given text using the REBEL model in a batched fashion.
    """
    words = text.split()
    num_words = len(words)
    if verbose:
        print(f"Input has {num_words} words")
    
    num_spans = math.ceil(num_words / span_length)
    if verbose:
        print(f"Input has {num_spans} spans")
    
    overlap_words = 0
    if num_spans > 1:
        overlap_words = 20
    
    spans_text = []
    start = 0
    for i in range(num_spans):
        start_index = start + (span_length - overlap_words) * i
        end_index = start_index + span_length
        spans_text.append(" ".join(words[start_index:end_index]))
    
    if verbose:
        print(f"Created {len(spans_text)} text spans")

    inputs_list = []
    for span_text in spans_text:
        inputs_list.append(tokenizer([span_text], return_tensors="pt"))

    all_generated_tokens = []
    for inputs in inputs_list:
        gen_kwargs = {
            "max_length": 256,
            "length_penalty": 0,
            "num_beams": NUM_RETURN_SEQUENCES,
            "num_return_sequences": NUM_RETURN_SEQUENCES
        }
        generated_tokens = model.generate(
            **inputs,
            **gen_kwargs,
        )
        all_generated_tokens.append(generated_tokens)

    kb = KB()
    for i, generated_tokens in enumerate(all_generated_tokens):
        decoded_preds = tokenizer.batch_decode(generated_tokens,
                                               skip_special_tokens=False)
        for sentence_pred in decoded_preds:
            relations = extract_relations_from_model_output(sentence_pred)
            for relation in relations:
                relation["meta"] = { "spans": [i] } 
                kb.add_relation(relation, source_url, source_title, source_publish_date)

    return kb

# Removed get_article and from_url_to_kb as they are not needed for pasted text input.
# If you need to process URLs in the future, you can re-add them or create a separate script.

# Main execution block
print("Processing pasted text...")

# Convert PASTED_TEXT_SOURCE_DATE to datetime object if it's a string
parsed_date = None
if PASTED_TEXT_SOURCE_DATE:
    try:
        parsed_date = datetime.strptime(PASTED_TEXT_SOURCE_DATE, '%Y-%m-%d')
    except ValueError:
        print(f"Warning: Could not parse PASTED_TEXT_SOURCE_DATE '{PASTED_TEXT_SOURCE_DATE}'. Date will not be added to graph.")
        parsed_date = None

kb = from_text_to_kb(
    PASTED_TEXT,
    source_url=PASTED_TEXT_SOURCE_URL,
    span_length=SPAN_LENGTH,
    source_title=PASTED_TEXT_SOURCE_TITLE,
    source_publish_date=parsed_date
)

if kb:
    kb.print()
    kb.to_ttl(filename=OUTPUT_FILENAME)