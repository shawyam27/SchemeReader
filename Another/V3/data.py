from pathlib import Path
import json
import re


OUTPUT_FOLDER = Path("scrapedV3")


def safe_filename(text):
    text = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        text
    )

    text = re.sub(
        r"_+",
        "_",
        text
    )

    return text.strip("_")


def save_category_data(
    category_name,
    category_url,
    schemes
):
    """
    Save the schemes for one ministry/category.
    """

    folder = (
        OUTPUT_FOLDER
        / "categories"
        / safe_filename(category_name)
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = folder / "schemes.json"

    data = {
        "category": category_name,
        "category_url": category_url,
        "scheme_count": len(schemes),
        "schemes": schemes
    }

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    print()
    print("=" * 60)
    print("DATA SAVED")
    print("=" * 60)
    print("Category:", category_name)
    print("Schemes:", len(schemes))
    print("File:", output_file.resolve())
    print("=" * 60)

    return output_file