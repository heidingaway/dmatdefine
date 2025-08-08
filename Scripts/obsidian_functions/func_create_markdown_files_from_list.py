import os
import re
import frontmatter

def create_markdown_files_from_list(
    item_list: list[str],
    output_directory: str = "empty_markdown_files"
) -> None:
    """
    Creates empty Markdown files with cleaned filenames based on an input list of strings.
    Each file includes frontmatter with a 'title' key generated from the original string.

    Args:
        item_list (List[str]): A list of strings. Each string will be used to generate
                              a filename and a title for a new Markdown file.
        output_directory (str): The directory where the Markdown files will be saved.
    """
    os.makedirs(output_directory, exist_ok=True)
    print(f"Ensuring output directory exists: {output_directory}")

    for i, item in enumerate(item_list):
        # 1. Normalize the filename
        normalized_name = re.sub(r'[^a-zA-Z0-9_]', '_', item.lower())
        normalized_name = normalized_name.strip('_')
        
        if not normalized_name:
            normalized_name = f"untitled_document_{i + 1}"

        file_path = os.path.join(output_directory, f"{normalized_name}.md")

        # 2. Generate the title for the frontmatter
        title_with_spaces = item.replace('_', ' ').title()
        
        # 3. Create a frontmatter post and write it to the file
        try:
            # Create an empty post object
            post = frontmatter.Post(content="")
            
            # Add the title to the post's metadata
            post.metadata['title'] = title_with_spaces

            # Write the post to the file, which includes the YAML frontmatter
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
                
            print(f"Successfully created file: {file_path}")
            print(f"  Frontmatter title added: '{title_with_spaces}'")
        except IOError as e:
            print(f"Error creating file {file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {file_path}: {e}")