import os
import re
import yaml
import glob

from ..rdf.rdf_helpers import get_uri_last_part

def extract_entity_uris_from_markdown_yaml(destination_dir: str, valid_target_basenames: set[str]) -> dict:
    # (Implementation remains the same)
    extracted_data = {}
    yaml_front_matter_regex = re.compile(r"^-{3}\s*\n(.*?)\n-{3}\s*\n", re.DOTALL)
    for root, _, files in os.walk(destination_dir):
        for file_name in files:
            if file_name.endswith(".md"):
                file_path = os.path.join(root, file_name)
                relative_file_path = os.path.relpath(file_path, destination_dir)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = yaml_front_matter_regex.match(content)
                if match:
                    yaml_string = match.group(1)
                    try:
                        data = yaml.safe_load(yaml_string)
                        if data and 'entities' in data and isinstance(data['entities'], list):
                            entities_in_file = []
                            for uri in data['entities']:
                                last_section = get_uri_last_part(uri)
                                if last_section.lower() not in valid_target_basenames:
                                    continue
                                entities_in_file.append({
                                    'uri': uri,
                                    'last_section': last_section
                                })
                            if entities_in_file:
                                extracted_data[relative_file_path] = entities_in_file
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML in {relative_file_path}: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred processing {relative_file_path}: {e}")
    return extracted_data

def update_source_yaml_with_related_entities(source_dir: str, destination_dir: str):
    # (Implementation remains the same, but imports 'get_uri_last_part' from the new location)
    print(f"Step 1: Pre-collecting Markdown basenames from '{destination_dir}' for filtering...")
    all_destination_markdown_basenames_lower = set()
    for md_file_path_in_dest in glob.glob(os.path.join(destination_dir, "**/*.md"), recursive=True):
        filename_no_ext = os.path.splitext(os.path.basename(md_file_path_in_dest))[0].lower()
        all_destination_markdown_basenames_lower.add(filename_no_ext)
    
    print(f"\nStep 2: Extracting entities from Markdown files in '{destination_dir}'...")
    extracted_entities_map = extract_entity_uris_from_markdown_yaml(destination_dir, all_destination_markdown_basenames_lower)
    print(f"Found entities in {len(extracted_entities_map)} files in destination directory (after filtering).")

    yaml_front_matter_and_content_regex = re.compile(r"^-{3}\s*\n(.*?)\n-{3}\s*\n(.*)", re.DOTALL)

    print(f"\nStep 3: Updating YAML in source files in '{source_dir}'...")
    updated_count = 0
    
    for relative_file_path, entities_list in extracted_entities_map.items():
        source_file_path = os.path.join(source_dir, relative_file_path)

        if not os.path.exists(source_file_path):
            print(f"  Warning: Source file not found for '{relative_file_path}'. Skipping.")
            continue

        try:
            with open(source_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = yaml_front_matter_and_content_regex.match(content)
            if not match:
                print(f"  Warning: No YAML front matter found in source file '{relative_file_path}'. Skipping update.")
                continue

            yaml_string = match.group(1)
            remaining_content = match.group(2)

            source_yaml_data = yaml.safe_load(yaml_string)
            if source_yaml_data is None:
                source_yaml_data = {}

            new_related_links_dict = {}
            current_basename_lower = os.path.splitext(os.path.basename(source_file_path))[0].lower()
            
            for entity in entities_list:
                entity_basename_lower = entity['last_section'].lower()
                
                if entity_basename_lower != current_basename_lower:
                    if entity_basename_lower not in new_related_links_dict:
                        formatted_link = f"[[{entity['last_section']}]]"
                        new_related_links_dict[entity_basename_lower] = formatted_link

            final_related_links = sorted(list(new_related_links_dict.values()))
            source_yaml_data['related'] = final_related_links

            updated_yaml_string = yaml.dump(source_yaml_data, sort_keys=False, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{updated_yaml_string}---\n{remaining_content}"

            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated_count += 1

        except yaml.YAMLError as e:
            print(f"  Error parsing YAML in source file '{relative_file_path}': {e}")
        except Exception as e:
            print(f"  An unexpected error occurred while updating '{relative_file_path}': {e}")

    print(f"\nFinished updating. Successfully updated {updated_count} source files.")