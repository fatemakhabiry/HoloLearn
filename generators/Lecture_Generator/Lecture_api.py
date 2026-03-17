import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
load_dotenv()

from Config import OPENROUTER_MODEL, FILE_TYPE_SOURCE_LABELS
from Lecture_generator import LectureGenerator


def _validate_sources(sources: Dict[str, List[str]]) -> None:
    for file_type, entries in sources.items():
        if not isinstance(entries, list):
            raise ValueError(
                "sources['" + file_type + "'] must be a list of alternating path/query pairs, "
                "e.g. [path1, query1, path2, query2]. Got: " + str(type(entries))
            )
        if len(entries) % 2 != 0:
            raise ValueError(
                "sources['" + file_type + "'] has an odd number of entries (" + str(len(entries)) + "). "
                "Each file path must be paired with a query string."
            )
        max_resources = 5 if file_type == "image" else 2
        if len(entries) > max_resources * 2:
            raise ValueError(
                "sources['" + file_type + "'] has " + str(len(entries) // 2) + " file(s), "
                "but the maximum allowed is " + str(max_resources) + " for this source type."
            )

# Text loader helper


def load_text(path: str) -> str:
    return open(path, encoding="utf-8", errors="ignore").read()


# Public API

def generate_lecture(
    lecture_topic: str,
    output_pdf_path: str,
    openrouter_api_key: str,
    sources: Dict[str, List[str]],
    model_name: str = OPENROUTER_MODEL,
) -> str:
    print("Starting lecture generation: " + lecture_topic)
    print("=" * 60)

    _validate_sources(sources)
    generator = LectureGenerator(openrouter_api_key=openrouter_api_key, model_name=model_name)

    # ── Separate image entries from text-based sources ──────────────────
    # images list: [{"path": "...", "caption": "..."}, ...]
    # preserved in input order so image[0] maps to section 1, etc.
    image_entries: List[Dict] = []
    image_paths_set: set = set()
    raw_image_entries = sources.get("image", [])
    for i in range(0, len(raw_image_entries), 2):
        img_path    = raw_image_entries[i]
        img_caption = raw_image_entries[i + 1]
        image_entries.append({"path": img_path, "caption": img_caption})
        image_paths_set.add(img_path)
        print(f"   [IMAGE] Registered image: {img_path}  caption: \"{img_caption}\"")

    print("\n[Step 1] Extracting content from each source...")
    extracted_parts = []

    for file_type, entries in sources.items():
        if not entries:
            print("   [SKIP] " + file_type + ": empty list")
            continue
        # Images have no text to extract — they are handled separately above
        if file_type == "image":
            continue
        source_label = FILE_TYPE_SOURCE_LABELS.get(file_type, file_type)
        for i in range(0, len(entries), 2):
            path, query = entries[i], entries[i + 1]
            print("   -> Processing " + file_type + " file: " + path + " ...")
            text = load_text(path)
            content = generator.extract_relevant_content(text=text, query=query, source_type=source_label)
            extracted_parts.append("FROM " + file_type.upper() + " (" + Path(path).name + "):\n" + content)
            print("   [SUCCESS] Extracted " + str(len(content)) + " characters from " + Path(path).name)

    if not extracted_parts:
        raise ValueError(
            "No source content provided. "
            "Please provide at least one source with BOTH a file path AND a query."
        )

    print("\n    Total sources processed: " + str(len(extracted_parts)))

    print("\n [Step 2] Combining all extracted content...")
    combined_content = "\n\n" + "=" * 60 + "\n\n".join(extracted_parts)
    print("   [SUCCESS] Combined content: " + str(len(combined_content)) + " total characters")

    print("\n  [Step 3] Generating lecture from combined content...")
    lecture_data = generator.generate_lecture_structure(
        combined_content=combined_content,
        lecture_topic=lecture_topic,
        image_entries=image_entries if image_entries else None,
    )
    print("   [SUCCESS] Generated lecture: " + lecture_data.get('title', lecture_topic))
    print("   [SUCCESS] Main sections: " + str(len(lecture_data.get('main_sections', []))))
    print("   [SUCCESS] Learning objectives: " + str(len(lecture_data.get('learning_objectives', []))))
    has_derivations = (
        lecture_data.get('mathematical_derivations') and
        len(lecture_data['mathematical_derivations'].strip()) > 0
    )
    print("   [SUCCESS] Mathematical derivations: " + ('Yes' if has_derivations else 'No (omitted)'))
    print("   [SUCCESS] Images to embed: " + str(len(image_entries)))

    print("\n [Step 4] Creating slide-style PDF document...")
    pdf_path = generator.create_pdf(
        lecture_data=lecture_data,
        output_path=output_pdf_path,
        images=image_entries if image_entries else None,
    )
    print("   [SUCCESS] PDF created: " + pdf_path)

    text_output_path = output_pdf_path.rsplit('.', 1)[0] + '.txt'
    print("\n [Step 5] Saving lecture as text file...")
    text_path = generator.save_lecture_to_text(lecture_data=lecture_data, output_path=text_output_path)
    print("   [SUCCESS] Text file created: " + text_path)

    json_output_path = output_pdf_path.rsplit('.', 1)[0] + '.json'
    print("\n [Step 6] Saving lecture data as JSON file...")
    Path(json_output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(lecture_data, f, indent=2, ensure_ascii=False)
    print("   [SUCCESS] JSON file created: " + json_output_path)

    print("\n" + "=" * 60)
    print(" Lecture generation complete!")
    print(" PDF Output:  " + pdf_path)
    print(" Text Output: " + text_path)
    print(" JSON Output: " + json_output_path)
    return pdf_path


# Entry point

# if __name__ == "__main__":
#     pdf = generate_lecture(
#         lecture_topic="Logistic Regression",
#         output_pdf_path="output/Logistic Regression Slides Trinity.pdf",
#         openrouter_api_key=os.getenv("openrouter_lecture"),
#         sources={
#             "pdf": [
#                 r"main_notes_text.txt",
#                 "Explain logistic regression",
#                 r"logistic_rgression_text.txt",
#                 "Summarize the key equations of logistic regression"
#             ],
#                 "image": [
#                     r"LR.png", "Example plot showing logistic regression curve",
#                 ],
#         }
#     )
#     print("\n Generated PDF: " + pdf)