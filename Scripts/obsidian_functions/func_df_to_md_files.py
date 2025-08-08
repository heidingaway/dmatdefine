import pandas as pd
import os
import re

def df_to_md_files(
    df: pd.DataFrame,
    output_dir: str,
    filename_col: str,
    frontmatter_cols: list[str], 
    main_content_col: str = None,
    title_template: str = "# {filename}\n\n",
    link_format: str = "[[{value}]]"
):
    """
    Converts a pandas DataFrame into a set of Markdown files, with configurable structure.

    Args:
        df (pd.DataFrame): The input DataFrame.
        output_dir (str): The directory where the Markdown files will be saved.
        filename_col (str): The name of the DataFrame column to use for generating filenames.
        frontmatter_cols (list[str]): A list of column names to be included in the YAML-like frontmatter.
        main_content_col (str, optional): The name of the column whose content will be the main body of the file. Defaults to None.
        title_template (str, optional): A template for the Markdown title. Uses f-string syntax, e.g., "# {filename}".
        link_format (str, optional): The format for creating internal links in the frontmatter.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    print(f"Saving Markdown files to: {os.path.abspath(output_dir)}")

    for _, row in df.iterrows():
        # --- 1. Generate a clean filename ---
        base_name = str(row[filename_col])
        cleaned_name = re.sub(r'[^a-zA-Z0-9_ -]', '', base_name).strip().replace(' ', '_')
        if not cleaned_name:
            continue
        
        file_path = os.path.join(output_dir, f"{cleaned_name}.md")

        # --- 2. Prepare Markdown content ---
        markdown_content = "---\n"
        for col_name in frontmatter_cols:
            if col_name in row and pd.notna(row[col_name]):
                value = row[col_name]
                if isinstance(value, str):
                    formatted_value = link_format.format(value=value)
                    # Wrap the formatted value in quotes for correct YAML parsing
                    markdown_content += f"{col_name}: \n - \"{formatted_value}\"\n"
                elif isinstance(value, list):
                    markdown_content += f"{col_name}:\n"
                    for item in value:
                        formatted_item = link_format.format(value=item)
                        # Wrap each list item in quotes
                        markdown_content += f" - \"{formatted_item}\"\n"
                else:
                    markdown_content += f"{col_name}: {value}\n"
        markdown_content += "---\n\n"

        # --- 3. Add title and main content ---
        markdown_content += title_template.format(filename=base_name)
        if main_content_col and main_content_col in row and pd.notna(row[main_content_col]):
            markdown_content += str(row[main_content_col])

        # --- 4. Write to file ---
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"Successfully wrote {os.path.basename(file_path)}")
        except IOError as e:
            print(f"Error writing file {file_path}: {e}")