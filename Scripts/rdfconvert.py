from rdflib import Graph

# 1. Create a new Graph
g = Graph()

try:
    g.parse("rdf/french.ttl", format="turtle")
    for s, p, o in g:
        print(s, p, o)
except Exception as e:
    print(f"Failed to parse remote TTL file: {e}")

output_filename = "french.ttl"

try:
    g.serialize(destination=output_filename, format="turtle")
    print(f"Graph successfully saved to {output_filename}")
except Exception as e:
    print(f"An error occurred while saving the graph: {e}")