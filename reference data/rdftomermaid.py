from rdflib import Graph
from rdflib.namespace import RDF, RDFS, OWL
import re

# Load the TTL file
ttl_file = "ontology.ttl"  # Replace with your TTL file name
g = Graph()
g.parse(ttl_file, format="ttl")

# Extract classes and subclass relationships
classes = set()
subclasses = []

for s, p, o in g:
    if p == RDF.type and o in [OWL.Class, RDFS.Class]:
        classes.add(s)
    elif p == RDFS.subClassOf:
        subclasses.append((s, o))
        classes.add(s)
        classes.add(o)

# Generate Mermaid class diagram syntax
mermaid_lines = ["classDiagram"]

# Add subclass relationships
for subclass, superclass in subclasses:
    subclass_label = re.sub(r'.*[#/]', '', str(subclass))
    superclass_label = re.sub(r'.*[#/]', '', str(superclass))
    mermaid_lines.append(f"    {superclass_label} <|-- {subclass_label}")

# Add standalone classes
for cls in classes:
    cls_label = re.sub(r'.*[#/]', '', str(cls))
    if not any(cls_label in line for line in mermaid_lines):
        mermaid_lines.append(f"    class {cls_label}")

# Write to output file
with open("mermaid_diagram.txt", "w") as f:
    f.write("\n".join(mermaid_lines))

print("Mermaid diagram code has been written to mermaid_diagram.txt")
