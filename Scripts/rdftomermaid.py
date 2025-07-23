from rdflib import Graph, Namespace, RDF, RDFS, OWL
import re

# Load TTL content from file
ttl_file = "CDO\\ochro\\function1.ttl"  # Replace with your TTL file name
g = Graph()
g.parse(ttl_file, format="ttl")

# Define namespaces
OCHRO = Namespace("https://gcxgce.sharepoint.com/teams/10001579/#")
SCHEMA = Namespace("https://schema.org/")

# Extract classes, subclass relationships, properties, and comments
classes = set()
subclasses = []
properties = []
comments = {}

for s, p, o in g:
    # Class declarations
    if p == RDF.type and o in [OWL.Class, RDFS.Class]:
        classes.add(s)

    # Subclass relationships
    elif p == RDFS.subClassOf:
        subclasses.append((s, o))
        classes.add(s)
        classes.add(o)

    # Comments and labels
    elif p in [RDFS.comment, RDFS.label]:
        comments[s] = str(o)

    # Custom properties
    elif p in [OCHRO.performs, OCHRO.produces, OCHRO.defines, SCHEMA.agent, SCHEMA.instrument, SCHEMA.object, SCHEMA.provider, SCHEMA.result]:
        properties.append((s, p, o))
        classes.add(s)
        classes.add(o)

# Generate Mermaid class diagram syntax
mermaid_lines = ["classDiagram"]

# Add subclass relationships
for subclass, superclass in subclasses:
    subclass_label = re.sub(r'.*[#/]', '', str(subclass))
    superclass_label = re.sub(r'.*[#/]', '', str(superclass))
    mermaid_lines.append(f"    {superclass_label} <|-- {subclass_label}")

# Add properties as associations
for subj, pred, obj in properties:
    subj_label = re.sub(r'.*[#/]', '', str(subj))
    pred_label = re.sub(r'.*[#/]', '', str(pred))
    obj_label = re.sub(r'.*[#/]', '', str(obj))
    mermaid_lines.append(f"    {subj_label} --> {obj_label} : {pred_label}")

# Add class declarations and comments
for cls in classes:
    cls_label = re.sub(r'.*[#/]', '', str(cls))
    mermaid_lines.append(f"    class {cls_label}")
    if cls in comments:
        comment_text = comments[cls].replace('\"', '\\\"')
        mermaid_lines.append(f'    {cls_label} : "{comment_text}"')

# Write to output file
with open("mermaid_diagram_with_properties.txt", "w") as f:
    f.write("\n".join(mermaid_lines))

print("Mermaid diagram with properties and comments has been written to mermaid_diagram_with_properties.txt")
