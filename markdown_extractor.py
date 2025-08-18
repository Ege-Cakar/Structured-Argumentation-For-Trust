"""
Script to extract argumentative components ("literals") from section texts and save them to JSON.

Works the same as the literal_extractor.py script, but it's for markdown files, and it's a bit more robust.

Workflow:
1) Default mode: Load `initial_files/sections_transformed.json`
2) Plain text mode: Load markdown/text file and chunk it
3) For each section/chunk, call the OpenAI API to extract components
4) Save a mapping of section_id -> {section_id, literals: {a1: text, ...}, num_literals}
   to output JSON file

Environment:
- Requires OPENAI_API_KEY to call the API. If missing or in --dry-run mode, the script will skip the API call and write empty literal objects.

CLI:
- --input: path to input file (JSON or markdown/text)
- --output: path to write literals JSON
- --model: OpenAI model name
- --dry-run: do not call OpenAI; produce empty literal objects
- --plain-text: process input as plain text/markdown instead of JSON
- --chunk-size: approximate size of chunks in characters (default: 1500)
- --chunk-by: how to chunk text: 'paragraphs' or 'chars' (default: 'paragraphs')
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Tuple, Optional

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


def load_plain_text(input_path: str) -> str:
    """Load a plain text or markdown file."""
    with open(input_path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text_by_paragraphs(text: str, max_chunk_size: int = 1500) -> List[Dict[str, Any]]:
    """Chunk text by paragraphs (double line breaks) while respecting max chunk size.
    
    Returns a list of section-like dictionaries compatible with the existing pipeline.
    """
    # Split by double line breaks (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_size = len(para)
        
        # If adding this paragraph would exceed max size and we have content, create a chunk
        if current_size + para_size > max_chunk_size and current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                "section_id": f"chunk_{len(chunks) + 1:03d}",
                "content": [{"type": "text", "text": chunk_text}]
            })
            current_chunk = [para]
            current_size = para_size
        else:
            current_chunk.append(para)
            current_size += para_size + (4 if current_chunk else 0)  # Account for \n\n separator
    
    # Add remaining content
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        chunks.append({
            "section_id": f"chunk_{len(chunks) + 1:03d}",
            "content": [{"type": "text", "text": chunk_text}]
        })
    
    return chunks


def chunk_text_by_chars(text: str, chunk_size: int = 1500) -> List[Dict[str, Any]]:
    """Chunk text by character count, trying to break at sentence boundaries.
    
    Returns a list of section-like dictionaries compatible with the existing pipeline.
    """
    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sent_size = len(sentence)
        
        # If this single sentence is larger than chunk size, split it
        if sent_size > chunk_size:
            # First, save any accumulated content
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    "section_id": f"chunk_{len(chunks) + 1:03d}",
                    "content": [{"type": "text", "text": chunk_text}]
                })
                current_chunk = []
                current_size = 0
            
            # Split the large sentence
            words = sentence.split()
            temp_chunk = []
            temp_size = 0
            
            for word in words:
                word_size = len(word) + 1  # +1 for space
                if temp_size + word_size > chunk_size and temp_chunk:
                    chunk_text = ' '.join(temp_chunk)
                    chunks.append({
                        "section_id": f"chunk_{len(chunks) + 1:03d}",
                        "content": [{"type": "text", "text": chunk_text}]
                    })
                    temp_chunk = [word]
                    temp_size = word_size
                else:
                    temp_chunk.append(word)
                    temp_size += word_size
            
            if temp_chunk:
                current_chunk = temp_chunk
                current_size = temp_size
        # If adding this sentence would exceed chunk size, create a new chunk
        elif current_size + sent_size + 1 > chunk_size and current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "section_id": f"chunk_{len(chunks) + 1:03d}",
                "content": [{"type": "text", "text": chunk_text}]
            })
            current_chunk = [sentence]
            current_size = sent_size
        else:
            current_chunk.append(sentence)
            current_size += sent_size + 1
    
    # Add remaining content
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append({
            "section_id": f"chunk_{len(chunks) + 1:03d}",
            "content": [{"type": "text", "text": chunk_text}]
        })
    
    return chunks


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
            "Extract literals from transformed section content or plain text and write to JSON. "
            "If OPENAI_API_KEY is not set or --dry-run is used, skips API calls."
        )
    )
    parser.add_argument("--input", default=default_input, help="Path to input file (JSON or text/markdown)")
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
    parser.add_argument(
        "--plain-text",
        action="store_true",
        help="Process input as plain text/markdown instead of JSON sections"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1500,
        help="Approximate size of chunks in characters for plain text mode (default: 1500)"
    )
    parser.add_argument(
        "--chunk-by",
        choices=["paragraphs", "chars"],
        default="paragraphs",
        help="How to chunk text in plain text mode: 'paragraphs' (at double line breaks) or 'chars' (by character count)"
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load and process input based on mode
    if args.plain_text:
        print(f"Processing plain text/markdown file: {input_path}")
        text_content = load_plain_text(input_path)
        
        # Chunk the text
        if args.chunk_by == "paragraphs":
            print(f"Chunking by paragraphs (max ~{args.chunk_size} chars per chunk)")
            sections = {f"chunk_{i+1:03d}": section 
                       for i, section in enumerate(chunk_text_by_paragraphs(text_content, args.chunk_size))}
        else:
            print(f"Chunking by character count (~{args.chunk_size} chars per chunk)")
            sections = {f"chunk_{i+1:03d}": section 
                       for i, section in enumerate(chunk_text_by_chars(text_content, args.chunk_size))}
        
        print(f"Created {len(sections)} chunks from input text")
        is_transformed_input = True  # Chunks use transformed format
    else:
        print(f"Processing JSON sections file: {input_path}")
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
        
        # Preview text content in plain text mode
        if args.plain_text and text_items:
            preview = text_items[0][:100] + "..." if len(text_items[0]) > 100 else text_items[0]
            print(f"  Preview: {preview}")
        
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
                    print(f"  Extracted {len(components)} literals from this text item")
                except Exception as exc:  # pragma: no cover
                    print(f"  Failed to extract literals for section {section_id}: {exc}")
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

    print(f"\nExtracted {total_literals} literals from {processed_sections} sections.")
    print(f"Results saved to: {output_path}")
    print("Done!")


if __name__ == "__main__":
    main()