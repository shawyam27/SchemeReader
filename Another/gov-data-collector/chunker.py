from pathlib import Path
import json
import re


DATA_FOLDER = Path("dataV3")
CHUNKS_FOLDER = Path("chunksV3")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def clean_for_chunking(text):
    """
    Remove metadata/header information that we don't
    need repeated in every chunk.
    """

    # Remove our generated metadata header
    text = re.sub(
        r"^# .*?\n\n"
        r"Source URL:.*?\n\n"
        r"Collected At:.*?\n\n"
        r"---\n\n",
        "",
        text,
        flags=re.DOTALL
    )

    return text.strip()


def create_chunks(text):
    """
    Split text into overlapping chunks.
    """

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + CHUNK_SIZE,
            text_length
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - CHUNK_OVERLAP

    return chunks


def process_file(filepath):
    """
    Read one Markdown document and create chunks.
    """

    print(f"Processing: {filepath}")

    text = filepath.read_text(
        encoding="utf-8"
    )

    text = clean_for_chunking(text)

    chunks = create_chunks(text)

    records = []

    for index, chunk in enumerate(chunks):

        record = {
            "chunk_id": f"{filepath.stem}_{index + 1}",
            "source_file": filepath.name,
            "source_path": str(filepath),
            "chunk_index": index,
            "text": chunk
        }

        records.append(record)

    return records


def save_chunks(records, source_name):

    output_folder = CHUNKS_FOLDER / source_name

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = output_folder / "chunks.json"

    output_file.write_text(
        json.dumps(
            records,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        f"Saved {len(records)} chunks → {output_file}"
    )


def main():

    markdown_files = list(
        DATA_FOLDER.rglob("*.md")
    )

    if not markdown_files:

        print("No Markdown files found.")

        return

    for filepath in markdown_files:

        source_name = filepath.parent.name

        records = process_file(filepath)

        save_chunks(
            records,
            source_name
        )


if __name__ == "__main__":
    main()