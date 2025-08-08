import pandas as pd
import os 

def df_to_markdown_files(df: pd.DataFrame, output_dir: str = "markdown_rows"):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving Markdown files to: {os.path.abspath(output_dir)}")

    # Iterate through each row of the DataFrame
    for index, row in df.iterrows():
        # Define the filename for the current row
        # Using the index for the filename, e.g., row_0.md, row_1.md
        file_name = os.path.join(output_dir, f"{index}.md")

        # Prepare the content for the Markdown file
        markdown_content = "---\n" # Horizontal rule for separation

        # Iterate through columns and add them to the Markdown content
        for col_name, value in row.items():
            if col_name != "Specific Accountabilities":
                # Format each key-value pair as a Markdown list item
                markdown_content += f'{col_name}: \n - "[[{value}]]"\n'

        markdown_content += "---\n\n"

        for col_name, value in row.items():
            markdown_content += f"# {index}\n\n"
            if col_name == "Specific Accountabilities" :
                markdown_content += f"> {value}"
        
        # Write the content to the Markdown file
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"Successfully wrote {file_name}")
        except IOError as e:
            print(f"Error writing file {file_name}: {e}")