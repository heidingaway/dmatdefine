import os
import re
import frontmatter

def normalize_rename_update_aliases(directory_path: str):
    """
    Walks through a directory, renames .md files to a normalized format,
    and adds the original file name to the frontmatter's 'aliases' list.

    Args:
        directory_path (str): The path to the directory to process.
    """
    print(f"Starting to process files in '{directory_path}'...")
    renamed_count = 0
    updated_count = 0
    
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if not filename.endswith(".md"):
                continue

            # Step 1: Normalize the filename
            name_without_ext = os.path.splitext(filename)[0]
            normalized_name_without_ext = re.sub(r'[^a-zA-Z0-9_]', '_', name_without_ext.lower())
            normalized_filename = f"{normalized_name_without_ext}.md"

            old_path = os.path.join(root, filename)
            new_path = os.path.join(root, normalized_filename)
            
            # Step 2: Only proceed if a rename is needed
            if old_path != new_path:
                try:
                    # Read the file and update its frontmatter
                    with open(old_path, 'r', encoding='utf-8') as f:
                        post = frontmatter.load(f)

                    # Ensure the aliases key exists and is a list
                    aliases = post.metadata.get('aliases', [])
                    if not isinstance(aliases, list):
                        aliases = [str(aliases)]  # Convert to a list if it's a single string
                    
                    # Add the original filename if it's not already in the list
                    if name_without_ext not in aliases:
                        aliases.append(name_without_ext)
                        post.metadata['aliases'] = aliases
                        
                        # Write the changes back to the original file
                        with open(old_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))
                        print(f"  Updated frontmatter for: '{filename}'")
                        updated_count += 1
                        
                    # Step 3: Rename the file
                    os.rename(old_path, new_path)
                    print(f"  Renamed: '{filename}' -> '{normalized_filename}'")
                    renamed_count += 1
                    
                except Exception as e:
                    print(f"  Error processing '{old_path}': {e}")
                    
    print(f"\nFinished processing '{directory_path}'.")
    print(f"  Files renamed: {renamed_count}")
    print(f"  Files with frontmatter updated: {updated_count}")