import pandas as pd
import os 
import re

# define variables

file = "cdsocdo.csv"

outputdir = "heidi2/cdoCDSO"

invalid_chars_pattern = r'[<>:"/\\|?*& ]'

preferred_column = "Title"

# define functions 

def df_to_markdown_files(df: pd.DataFrame, output_dir: str = "markdown_rows"):
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving Markdown files to: {os.path.abspath(output_dir)}")
    
    try:
        df = move_column_to_front(df, preferred_column)
    except ValueError as e:
        print(f"Warning: Could not reorder columns for some files. {e}")

    # Iterate through each row of the DataFrame
    for index, row in df.iterrows():
        # Define the filename for the current row
        # Using the index for the filename, e.g., row_0.md, row_1.md
        file_name = os.path.join(output_dir, f"{index}.md")

        # Prepare the content for the Markdown file
        markdown_content = "---\n" # Horizontal rule for separation

        # Iterate through columns and add them to the Markdown content
        for col_name, value in row.items():
            if col_name != "Specific Accountabilities" and col_name != "Title":
                # Format each key-value pair as a Markdown list item
                markdown_content += f'{col_name}: \n - "[[{value}]]"\n'

        markdown_content += "---\n\n"
 
        for col_name, value in row.items():
            if col_name == "Title" :
                markdown_content += f"# {value}\n\n"
            elif col_name == "Specific Accountabilities" :
                markdown_content += f"{value}"
        
        # Write the content to the Markdown file
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"Successfully wrote {file_name}")
        except IOError as e:
            print(f"Error writing file {file_name}: {e}")

def create_empty_markdown_files(item_list, output_directory="empty_markdown_files"):
    """
    Creates empty Markdown files with cleaned filenames based on an input list of strings,
    using an externally defined invalid filename pattern.

    Args:
        item_list (list): A list of strings. Each string will be used to generate
                          a filename for a new, empty Markdown file.
        output_directory (str): The directory where the Markdown files will be saved.
    """

    # Create the output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    # print(f"Ensuring output directory exists: {output_directory}") # Optional: keep for debugging

    for i, item in enumerate(item_list):
        # 1. Generate a clean filename from the list item
        # Use the externally defined pattern for replacement
        cleaned_name = re.sub(invalid_chars_pattern, "_", item)

        # Remove leading/trailing underscores if any were introduced
        cleaned_name = cleaned_name.strip('_')

        # Handle cases where cleaning results in an empty string
        if not cleaned_name:
            cleaned_name = f"untitled_document_{i+1}"

        # Construct the full filename with .md extension
        base_file_name = f"{cleaned_name}.md"
        file_path = os.path.join(output_directory, base_file_name)

        try:
            # Open in write mode ('w'). If content is empty, it creates an empty file.
            with open(file_path, 'w', encoding='utf-8') as f:
                # No f.write() call means the file will be empty
                pass
            # print(f"Successfully created empty file: {file_path}") # Optional: keep for debugging
        except IOError as e:
            # print(f"Error creating file {file_path}: {e}") # Optional: keep for debugging
            pass # Or handle specific error logging externally
        except Exception as e:
            # print(f"An unexpected error occurred for {file_path}: {e}") # Optional: keep for debugging
            pass # Or handle specific error logging externally


def move_column_to_front(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Moves a specified column to the first position in the DataFrame,
    preserving the relative order of the other columns.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to move to the front.

    Returns:
        pd.DataFrame: A new DataFrame with the specified column at the beginning.

    Raises:
        ValueError: If the specified column_name does not exist in the DataFrame.
    """
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' not found in the DataFrame.")

    # Get a list of all current columns
    cols = df.columns.tolist()

    # Remove the specified column from its current position
    cols.remove(column_name)

    # Insert the specified column at the beginning of the list
    new_column_order = [column_name] + cols

    # Reindex the DataFrame with the new column order
    return df[new_column_order]

# Import data and clean

df = pd.read_csv(file, encoding = "cp1252")

df_cleaned = df.dropna(axis=1, how='all')

columns = df_cleaned.columns

columns_to_clean = columns # Add any other relevant text columns

for col in columns_to_clean:
    if col in df_cleaned.columns:
        df_cleaned[col] = df_cleaned[col].astype(str).str.replace('ï¿½', "'", regex=False)

df_cleaned['file'] = "Accountability"

columns = df_cleaned.columns

df_cleaned['filename'] = df_cleaned[['Position', 'file', 'JD Order']].astype(str).agg("_".join, axis=1)
df_cleaned['subClassOf'] = df_cleaned[['Position', 'Type', 'Label']].astype(str).agg("_".join, axis=1)
df_cleaned['class'] = df_cleaned[['Position', 'Type']].astype(str).agg("_".join, axis=1)

df_cleaned['filename'] = df_cleaned['filename'].str.replace(invalid_chars_pattern, "", regex = True)
df_cleaned['Label'] = df_cleaned['Label'].str.replace(invalid_chars_pattern, "", regex = True)
df_cleaned['Title'] = df_cleaned['filename'].str.replace("_", " ")
df_cleaned['subClassOf'] = df_cleaned['subClassOf'].str.replace(invalid_chars_pattern,"", regex=True)
df_cleaned['class'] = df_cleaned['class'].str.replace(invalid_chars_pattern, "", regex = True)

mdOutput = df_cleaned[['filename', 'Specific Accountabilities', 'class', 'Label', 'Title']].copy().set_index('filename').rename(columns = {'Label': 'subClassOf', 'class': 'acc_type'})

mdOutput_class = df_cleaned[['class', 'Label']].copy()
mdOutput_class.rename(columns= {'Label' : 'filename', 'class': 'subClassOf'}, inplace=True)

mdOutput_class['filename'] = mdOutput_class['filename'].str.replace(invalid_chars_pattern, "", regex = True)
mdOutput_class['Title'] = mdOutput_class['filename'].str.replace("_", " ")
mdOutput_class = mdOutput_class.set_index('filename')


# layer one
df_to_markdown_files(df=mdOutput, output_dir=outputdir)
    
# layer two 
df_to_markdown_files(df=mdOutput_class, output_dir=outputdir)

#layer three
create_empty_markdown_files(df_cleaned['class'], outputdir)