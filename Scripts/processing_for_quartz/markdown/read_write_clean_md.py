import re
import yaml

def read_markdown_file(file_path: str) -> tuple[dict, str]:
    """
    Reads a Markdown file, separates the YAML frontmatter from the body,
    and returns them as a dictionary and a string.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    existing_frontmatter = {}
    markdown_body = content
    if content.startswith("---"):
        try:
            yaml_end_index = content.find("---", 3)
            if yaml_end_index != -1:
                yaml_str = content[3:yaml_end_index].strip()
                existing_frontmatter = yaml.safe_load(yaml_str) or {}
                if False in existing_frontmatter:
                    del existing_frontmatter[False]
                markdown_body = content[yaml_end_index + 3:].strip()
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}. Treating as no existing frontmatter.")
            pass
    
    return existing_frontmatter, markdown_body

def write_markdown_file(file_path: str, frontmatter: dict, body: str):
    """
    Combines frontmatter and body, then writes the content to a Markdown file.
    """
    frontmatter_yaml = yaml.dump(frontmatter, sort_keys=False).strip()
    new_content = f"---\n{frontmatter_yaml}\n---\n\n{body}"
    new_content = re.sub(r'\n\n\n+', '\n\n', new_content).strip() + '\n'
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

def clean_markdown_body(body: str, title: str) -> str:
    """
    Removes existing Mermaid and Related Links sections from the body.
    """
    mermaid_block_pattern = re.compile(
        r'(?:\s*^##\s*Semantic\s*Connections\s*$\s*)?^\s*```mermaid\s*$\n.*?\n^\s*```\s*$', re.DOTALL | re.MULTILINE)
    related_links_block_pattern = re.compile(
        r'(?:\s*^##\s*Related\s*Links\s*$\s*)?(?:^\s*-\s*\[\[.*?\]\]\s*$\n)*', re.DOTALL | re.MULTILINE | re.IGNORECASE)
    footnotes_header_pattern = re.compile(r'^\s*#+\s*Footnotes\s*$', re.MULTILINE | re.IGNORECASE)

    if title:
        title_heading_pattern = re.compile(
            r'^\s*#\s*' + re.escape(title) + r'\s*$', 
            re.MULTILINE | re.IGNORECASE
        )
        body = title_heading_pattern.sub('', body, count=1).strip()

    body = mermaid_block_pattern.sub('', body).strip()
    body = related_links_block_pattern.sub('', body).strip()
    body = footnotes_header_pattern.sub('', body).strip()
    body = re.sub(r'\n\s*\n', '\n\n', body).strip()
    
    return body