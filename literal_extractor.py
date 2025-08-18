"""
Script to extract argumentative components ("literals") from section texts and save them to JSON.

Workflow:
1) Load `initial_files/sections_transformed.json`
2) For each section, iterate over EACH content item where type == 'text'
3) For each 'text' item, call the OpenAI API separately to extract components
4) Merge components in order across the section and save a mapping of
   section_id -> {section_id, literals: {a1: text, ...}, num_literals}
   to `initial_files/literals.json`
5) Print the total number of literals extracted and "Done!"

Environment:
- Requires OPENAI_API_KEY to call the API. If missing or in --dry-run mode, the script will skip the API call and write empty literal objects.

CLI:
- --input: path to transformed sections JSON (default: initial_files/sections_transformed.json)
- --output: path to write literals JSON (default: initial_files/literals.json)
- --model: OpenAI model name (default: the provided fine-tuned model)
- --dry-run: do not call OpenAI; produce empty literal objects
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv

load_dotenv()


def build_default_paths() -> Tuple[str, str]:
    """Return absolute default input and output paths based on the script location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sections_dir = os.path.join(script_dir, "initial_files")
    intermediate_dir = os.path.join(script_dir, "intermediate_files")
    default_input = os.path.join(sections_dir, "sections_transformed.json")
    default_output = os.path.join(intermediate_dir, "literals.json")
    return default_input, default_output


def load_sections(input_path: str) -> Dict[str, Any]:
    """Load the transformed sections JSON file.

    The expected structure is a dict mapping section keys to objects with at least:
      - section_id: str
      - content: list[ {type: 'text'|'reasoning'|..., text?: str, ...} ]
    """
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_section_text_items(content_list: List[Dict[str, Any]]) -> List[str]:
    """Return a list of 'text' fields (each item separately) for items where type == 'text'."""
    if not isinstance(content_list, list):
        return []
    texts: List[str] = []
    for item in content_list:
        if isinstance(item, dict) and item.get("type") == "text":
            text_value = item.get("text", "")
            if isinstance(text_value, str) and text_value.strip():
                texts.append(text_value.strip())
    return texts


def extract_text_items_for_section(section: Dict[str, Any], is_transformed: bool) -> List[str]:
    """Extract text inputs for a section depending on input format.

    - If is_transformed is True, use the existing transformed format where
      section["content"] is a list of objects with type=='text'.
    - Otherwise, support the alternative format where section["content"] is a
      single string containing the section text (as in the attached example).
    """
    if not isinstance(section, dict):
        return []

    if is_transformed:
        return extract_section_text_items(section.get("content", []))

    content_value = section.get("content")
    if isinstance(content_value, str):
        text_value = content_value.strip()
        return [text_value] if text_value else []

    # Fallback: if content is a list, try the transformed extractor anyway
    if isinstance(content_value, list):
        return extract_section_text_items(content_value)

    return []


def create_openai_client(api_key: str | None):
    """Create and return an OpenAI client, supporting both new and legacy SDKs.

    Returns either a new-style client (with chat.completions) or the legacy module object.
    """
    try:
        # New-style client (openai>=1.0)
        from openai import OpenAI  # type: ignore

        return OpenAI(api_key=api_key)
    except Exception:
        # Legacy (openai<1.0)
        try:
            import openai as openai_legacy  # type: ignore

            openai_legacy.api_key = api_key
            return openai_legacy
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Failed to import OpenAI SDK. Please install 'openai' via pip."
            ) from exc


def _parse_literals_from_model_output(output_text: str) -> List[str]:
    """Parse literals from model output, expecting JSON with key 'literals'.

    Accepts either:
      - {"literals": {"a1": "...", "a2": "..."}}
      - {"literals": ["...", "..."]}  (backward compatibility)

    Returns the list of component texts in order of a1..aN when a dict is provided.
    """
    def to_list(parsed_obj: Dict[str, Any]) -> List[str]:
        value = parsed_obj.get("literals", [])
        if isinstance(value, list):
            return [str(x) for x in value]
        if isinstance(value, dict):
            # Sort by numeric suffix if keys follow a\d+; else keep insertion order
            keys = list(value.keys())
            if all(isinstance(k, str) and re.fullmatch(r"a\d+", k) for k in keys):
                def sort_key(k: str) -> int:
                    return int(k[1:])
                ordered_keys = sorted(keys, key=sort_key)
            else:
                ordered_keys = keys
            return [str(value[k]) for k in ordered_keys]
        return []

    output_text = output_text.strip()
    # Try direct JSON first
    try:
        parsed = json.loads(output_text)
        return to_list(parsed)
    except Exception:
        pass

    # Fallback: extract the first {...} block and parse it
    json_obj_match = re.search(r"\{[\s\S]*\}", output_text)
    if json_obj_match:
        try:
            parsed = json.loads(json_obj_match.group(0))
            return to_list(parsed)
        except Exception:
            pass

    # Last resort: return empty list
    return []


def call_openai_extract_literals(
    text: str,
    model_name: str,
    api_key: str | None,
    client_obj: Any | None = None,
) -> List[str]:
    """Call OpenAI to extract literals from the provided text.

    Returns a list of strings named 'literals'.
    """
    if client_obj is None:
        client_obj = create_openai_client(api_key)

    system_prompt = (
        "You are an argument-component extraction assistant. Given an essay, identify every argumentative component, i.e the building blocks of the argument in the essay. Return exactly this JSON:\n{\n  \"literals\": {\n    \"a1\": \"<first component text>\",\n    \"a2\": \"<second component text>\",\n    ...\n  }\n}\nNumber the keys (a1, a2, …) in order of appearance."
    )

    # Detect new-style client via attribute presence
    new_style = hasattr(client_obj, "chat") and hasattr(client_obj.chat, "completions")

    if new_style:
        # openai>=1.0 new client interface
        response = client_obj.chat.completions.create(
            model=model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        content: str = response.choices[0].message.content or ""
        return _parse_literals_from_model_output(content)
    else:
        # Legacy SDK
        # pylint: disable=import-outside-toplevel
        import types

        openai_legacy = client_obj  # module
        if not isinstance(openai_legacy, types.ModuleType):
            raise RuntimeError("Unexpected OpenAI client type for legacy SDK path.")

        completion = openai_legacy.ChatCompletion.create(
            model=model_name,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        content = completion["choices"][0]["message"]["content"]
        return _parse_literals_from_model_output(content)


def main() -> None:
    default_input, default_output = build_default_paths()

    parser = argparse.ArgumentParser(
        description=(
            "Extract literals from transformed section content and write to JSON. "
            "If OPENAI_API_KEY is not set or --dry-run is used, skips API calls."
        )
    )
    parser.add_argument("--input", default=default_input, help="Path to sections_transformed.json")
    parser.add_argument("--output", default=default_output, help="Path to write literals.json")
    parser.add_argument(
        "--model",
        default=os.getenv(
            "OPENAI_MODEL",
            "ft:gpt-4.1-mini-2025-04-14:personal:literal-extractor-mini:C2dwgR7K",
        ),
        help=(
            "OpenAI model to use (default: provided fine-tuned model or env OPENAI_MODEL)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip OpenAI calls; write empty literals for each section.",
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    sections = load_sections(input_path)
    input_basename = os.path.splitext(os.path.basename(input_path))[0]
    is_transformed_input = input_basename.endswith("_transformed")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("OPENAI_API_KEY not set. Running in dry-run mode (no API calls).")
        args.dry_run = True

    client_obj = None if args.dry_run else create_openai_client(api_key)

    results: Dict[str, Dict[str, Any]] = {}
    total_literals = 0
    processed_sections = 0

    total_sections = len(sections)

    for idx, (key, section) in enumerate(sections.items(), start=1):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id") or key)
        print(f"[{idx}/{total_sections}] Processing section: {section_id}", flush=True)
        text_items = extract_text_items_for_section(section, is_transformed=is_transformed_input)
        if not text_items:
            results[section_id] = {"section_id": section_id, "literals": {}, "num_literals": 0}
            processed_sections += 1
            continue

        aggregated_components: List[str] = []

        if args.dry_run:
            # No API calls; keep empty per section
            pass
        else:
            for text in text_items:
                try:
                    # Each call returns list[str] parsed from {"literals": {"a1": "...", ...}}
                    components = call_openai_extract_literals(
                        text=text, model_name=args.model, api_key=api_key, client_obj=client_obj
                    )
                except Exception as exc:  # pragma: no cover
                    print(f"Failed to extract literals for section {section_id} text item: {exc}")
                    components = []

                # components is a list[str] in order as parsed from keys a1, a2, ...
                aggregated_components.extend(
                    [c for c in components if isinstance(c, str) and c.strip()]
                )

        # Build literals object with sequential numbering a1..aN
        literals_obj: Dict[str, str] = {
            f"a{i}": component for i, component in enumerate(aggregated_components, start=1)
        }

        results[section_id] = {
            "section_id": section_id,
            "literals": literals_obj,
            "num_literals": len(literals_obj),
        }
        total_literals += len(literals_obj)
        processed_sections += 1

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Extracted {total_literals} literals from {processed_sections} sections. Done!")


if __name__ == "__main__":
    main()
