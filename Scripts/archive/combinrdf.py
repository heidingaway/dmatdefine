import os
from rdflib import Graph
rdf_folder = "rdf" # <--- CHANGE THIS TO YOUR FOLDER PATH

# Define the output file name for the combined graph
output_combined_filename = "all_graphs.ttl"

# 1. Create a new Graph
g = Graph()

parsed_files_count = 0

print(f"Starting to combine RDF data from folder: {rdf_folder}")


try:
    # 2. Iterate through all files in the specified folder
    for filename in os.listdir(rdf_folder):
        if filename.endswith(".ttl"):
            file_path = os.path.join(rdf_folder, filename)
            print(f"Parsing file: {file_path}")
            try:
                # 3. Parse each .ttl file and add its triples to the main graph 'g'
                g.parse(file_path, format="turtle")
                parsed_files_count += 1
                print(f"  Successfully parsed {filename}. Current triples in graph: {len(g)}")
            except Exception as e:
                print(f"  Error parsing {filename}: {e}")
        else:
            print(f"Skipping non-TTL file: {filename}")

    if parsed_files_count == 0:
        print(f"No .ttl files found in '{rdf_folder}'. Please ensure the folder exists and contains .ttl files.")
    else:
        print(f"\nFinished parsing {parsed_files_count} .ttl files.")
        print(f"Total triples in the combined graph: {len(g)}")

        # 4. Serialize (save) the combined graph to a new TTL file
        try:
            g.serialize(destination=output_combined_filename, format="turtle")
            print(f"\nCombined graph successfully saved to {output_combined_filename}")
        except Exception as e:
            print(f"An error occurred while saving the combined graph: {e}")
except FileNotFoundError:
    print(f"Error: The folder '{rdf_folder}' was not found.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")