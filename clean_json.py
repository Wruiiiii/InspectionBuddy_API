#!/usr/bin/env python3
import json
import unicodedata
import re
import sys

def clean_text(s: str) -> str:
    # 1. Unicode NFKC normalization (ﬂ → fl, ﬁ → fi, etc.)
    s = unicodedata.normalize("NFKC", s)

    # 2. Remove control-category characters except newline
    s = "".join(ch for ch in s if ch == "\n" or unicodedata.category(ch)[0] != "C")

    # 3. Split into lines, keep only those with at least one letter
    lines = [line for line in s.splitlines()
             if re.search(r"[A-Za-z]", line)]

    # 4. Collapse runs of blank lines
    cleaned_lines = []
    blank = False
    for line in lines:
        if line.strip() == "":
            if not blank:
                cleaned_lines.append("")  # keep one blank
            blank = True
        else:
            cleaned_lines.append(line)
            blank = False

    return "\n".join(cleaned_lines)

def main(input_path: str, output_path: str):
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    for doc in data.get("results", []):
        raw = doc.get("text", "") or ""
        doc["text"] = clean_text(raw)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Cleaned JSON written to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: clean_json.py <input.json> <output.json>")
    else:
        main(sys.argv[1], sys.argv[2])