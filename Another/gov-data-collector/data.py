from pathlib import Path
from datetime import datetime
import json
import re


# ---------------------------------------------------------
# FOLDERS
# ---------------------------------------------------------

SCRAPED_FOLDER = Path("scraped")
RAG_FOLDER = Path("rag_data")


# ---------------------------------------------------------
# SAFE FILENAME
# ---------------------------------------------------------

def safe_filename(name):
    """
    Convert a name into a safe filename.
    """

    name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        name
    )

    return name.strip("_")


# ---------------------------------------------------------
# CLEAN TEXT
# ---------------------------------------------------------

def clean_text(content):
    """
    Clean scraped Markdown while preserving useful information.
    """

    if not content:
        return ""

    # Normalize line endings
    content = content.replace("\r\n", "\n")
    content = content.replace("\r", "\n")

    # Remove excessive spaces
    content = re.sub(
        r"[ \t]+",
        " ",
        content
    )

    # Remove excessive blank lines
    content = re.sub(
        r"\n{3,}",
        "\n\n",
        content
    )

    lines = []

    previous_line = None

    # Common website navigation noise
    noise = [
        "skip to main content",
        "skip to navigation",
        "back to top",
        "click here to login",
        "home |",
        "sign in",
        "register"
    ]

    for line in content.splitlines():

        line = line.strip()

        if not line:
            continue

        line_lower = line.lower()

        # Remove obvious navigation noise
        if any(
            item in line_lower
            for item in noise
        ):
            continue

        # Remove consecutive duplicates
        if line == previous_line:
            continue

        lines.append(line)

        previous_line = line

    return "\n".join(lines).strip()


# ---------------------------------------------------------
# SAVE SCRAPED PAGE
# ---------------------------------------------------------

def save_scraped_page(
    source,
    page_name,
    url,
    content,
    page_type="page"
):
    """
    Save the scraped page in the scraped/ directory.
    """

    source_id = source["id"]

    folder_name = safe_filename(
        source_id
    )

    page_filename = safe_filename(
        page_name
    )

    output_folder = (
        SCRAPED_FOLDER /
        folder_name
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Clean the scraped content
    cleaned_content = clean_text(
        content
    )

    collected_at = datetime.now().isoformat(
        timespec="seconds"
    )

    final_content = f"""# {page_name}

Source URL: {url}

Source ID: {source_id}

Page Type: {page_type}

Collected At: {collected_at}

---

{cleaned_content}
"""

    output_file = (
        output_folder /
        f"{page_filename}.md"
    )

    output_file.write_text(
        final_content,
        encoding="utf-8"
    )

    print(
        f"Saved scraped page: "
        f"{output_file}"
    )

    return output_file


# ---------------------------------------------------------
# SAVE RAG DOCUMENT
# ---------------------------------------------------------

def save_rag_document(
    source,
    page_name,
    url,
    content,
    category="general"
):
    """
    Create a cleaner document for the future RAG pipeline.
    """

    source_id = source["id"]

    source_folder = safe_filename(
        source_id
    )

    category_folder = safe_filename(
        category
    )

    output_folder = (
        RAG_FOLDER /
        category_folder /
        source_folder
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    cleaned_content = clean_text(
        content
    )

    if not cleaned_content:
        print(
            f"Skipped empty RAG document: "
            f"{page_name}"
        )

        return None

    final_content = f"""# {page_name}

## Source Information

Source: {source["name"]}

Source URL: {url}

Source ID: {source_id}

Category: {category}

---

## Content

{cleaned_content}
"""

    filename = safe_filename(
        page_name
    )

    output_file = (
        output_folder /
        f"{filename}.md"
    )

    output_file.write_text(
        final_content,
        encoding="utf-8"
    )

    print(
        f"Saved RAG document: "
        f"{output_file}"
    )

    return output_file


# ---------------------------------------------------------
# SAVE METADATA
# ---------------------------------------------------------

def save_metadata(
    source,
    page_name,
    url,
    scraped_file,
    rag_file=None,
    page_type="page"
):
    """
    Save metadata describing the scraped document.
    """

    source_id = source["id"]

    output_folder = (
        SCRAPED_FOLDER /
        safe_filename(source_id)
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata = {

        "source_id": source_id,

        "source_name": source["name"],

        "page_name": page_name,

        "url": url,

        "page_type": page_type,

        "scraped_file": str(
            scraped_file
        ),

        "rag_file": (
            str(rag_file)
            if rag_file
            else None
        ),

        "scraped_at": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    metadata_file = (
        output_folder /
        f"{safe_filename(page_name)}_metadata.json"
    )

    metadata_file.write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    return metadata