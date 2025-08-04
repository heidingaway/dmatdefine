# ==============================================================================
# SCRIPT CONFIGURATION BLOCK
# Change these variables to adapt the script for other articles.
# ==============================================================================

# Required: The URL of the article to process.
# This is a placeholder URL for GitHub syncing. In a real application,
# this would be the actual URL of the article you want to process.
ARTICLE_URL = "https://www.tbs-sct.canada.ca/pol/doc-eng.aspx?id=32603"

# Required: The filename for the Turtle (.ttl) output.
OUTPUT_FILENAME = "test_output.ttl"

# Optional/Advanced: Adjust these for fine-tuning.
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

# scraping of web articles
from newspaper import Article, ArticleException

# google news scraping
from GoogleNews import GoogleNews

# graph visualization
from pyvis.network import Network

# show HTML in notebook
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

        article_url = list(r2["meta"].keys())[0]

        if article_url not in r1["meta"]:
            r1["meta"][article_url] = r2["meta"][article_url]
        else:
            spans_to_add = [span for span in r2["meta"][article_url]["spans"]
                            if span not in r1["meta"][article_url]["spans"]]
            r1["meta"][article_url]["spans"] += spans_to_add

    def get_wikipedia_data(self, candidate_entity):
        """
        Fetches data from Wikipedia for a given entity.
        Handles various Wikipedia exceptions.
        """
        try:
            page = wikipedia.page(candidate_entity, auto_suggest=False)
            entity_data = {
                "title": page.title,
                "url": page.url,
                "summary": page.summary
            }
            return entity_data
        except (wikipedia.exceptions.PageError, wikipedia.exceptions.DisambiguationError, wikipedia.exceptions.WikipediaException):
            return None

    def add_entity(self, e):
        """Adds an entity to the KB if it doesn't already exist."""
        self.entities[e["title"]] = {k:v for k,v in e.items() if k != "title"}

    def add_relation(self, r, article_url, article_title, article_publish_date):
        """
        Adds a relation to the KB. It first validates entities against Wikipedia,
        adds new entities and sources, then adds or merges the relation.
        """
        candidate_entities = [r["head"], r["tail"]]
        entities = [self.get_wikipedia_data(ent) for ent in candidate_entities]

        if any(ent is None for ent in entities):
            return

        for e in entities:
            self.add_entity(e)

        r["head"] = entities[0]["title"]
        r["tail"] = entities[1]["title"]

        if article_url not in self.sources:
            self.sources[article_url] = {
                "article_title": article_title,
                "article_publish_date": article_publish_date
            }
        
        r["meta"] = {
            article_url: { "spans": r["meta"]["spans"] }
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

            for article_url in relation["meta"].keys():
                g.add((head_uri, DCTERMS.source, URIRef(article_url)))

        # Step 3: Add all sources as a separate set of triples
        for url, data in self.sources.items():
            source_uri = URIRef(url)
            g.add((source_uri, RDF.type, RDFS.Resource))
            g.add((source_uri, DCTERMS.title, Literal(data["article_title"])))
            
            date_value = data.get("article_publish_date")
            if isinstance(date_value, datetime):
                # Format the datetime object to a simple date string
                date_str = date_value.strftime('%Y-%m-%d')
                g.add((source_uri, DCTERMS.date, Literal(date_str, datatype=XSD.date)))
        
        # Serialize and save
        g.serialize(destination=filename, format="turtle", encoding='utf-8')
        print(f"Knowledge graph saved to {filename} in Turtle format.")


def from_text_to_kb(text, article_url, span_length, article_title=None,
                    article_publish_date=None, verbose=False):
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
                kb.add_relation(relation, article_url, article_title, article_publish_date)

    return kb

def get_article(url):
    """Parses an article from a URL using newspaper3k."""
    # For GitHub syncing, we'll simulate article content for a placeholder URL.
    # In a real scenario, this would download and parse the actual article.
    if url == "https://example.com/news/article-placeholder.html":
        class MockArticle:
            def __init__(self):
                self.title = "Mock Article Title for GitHub Syncing"
                self.url = url
                self.publish_date = datetime(2023, 10, 26) # A dummy date
                self.text = (
                    "This is a mock article text for demonstration purposes. "
                    "It contains some sample entities like MicroStrategy and Bitcoin. "
                    "MicroStrategy is a company that holds a significant amount of Bitcoin. "
                    "Bitcoin is a decentralized digital currency. "
                    "The company CEO, Michael Saylor, is a strong proponent of Bitcoin. "
                    "This article was published on October 26, 2023."
                )
            def download(self):
                pass # No actual download needed for mock
            def parse(self):
                pass # No actual parsing needed for mock
        return MockArticle()
    else:
        # Fallback for actual URLs if the script were run locally with real URLs
        article = Article(url)
        article.download()
        article.parse()
        return article

def from_url_to_kb(url):
    """Extracts text from a URL, extracts relations, and populates a KB."""
    try:
        article = get_article(url)
        config = {
            "article_title": article.title,
            "article_publish_date": article.publish_date if article.publish_date else None
        }
        kb = from_text_to_kb(article.text, article.url, span_length=SPAN_LENGTH, **config)
        return kb
    except ArticleException as e:
        print(f"Error processing URL {url}: {e}")
        return None

# Main execution block
print(f"Processing article from: {ARTICLE_URL}")
kb = from_url_to_kb(ARTICLE_URL)

if kb:
    kb.print()
    kb.to_ttl(filename=OUTPUT_FILENAME)