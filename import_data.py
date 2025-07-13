import json
import unicodedata
from database import HistoricalDocument, SessionLocal, populate_fts, create_tables
from sqlalchemy import text

def import_json_file(filepath):
    # Set up DB and session
    create_tables()
    session = SessionLocal()

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    documents = data.get('results', [])
    imported_count = 0

    for doc in documents:
        doc_type = doc.get('doc_type')
        year = doc.get('year')
        # Normalize text and remove control characters
        raw_text = doc.get('text') or ""
        text_content = unicodedata.normalize("NFKC", raw_text)
        text_content = "".join(
            ch for ch in text_content
            if ch == "\n" or unicodedata.category(ch)[0] != "C"
        )
        raw_date = doc.get('effective_date')
        effective_date = raw_date if raw_date and raw_date.strip() else None

        if not text_content.strip():
            continue  # skip blank records

        # Extract title from the text: find the line after “release” header or fallback to first non-empty line
        lines = [line.strip() for line in text_content.split("\n") if line.strip()]
        title_line = ""
        if let_index := next((i for i, l in enumerate(lines) if "release" in l.lower()), None):
            if let_index + 1 < len(lines):
                title_line = lines[let_index + 1]
        if not title_line and lines:
            title_line = lines[0]

        historical_doc = HistoricalDocument(
            doc_type=doc_type,
            year=year,
            title=title_line,
            text=text_content,
            effective_date=effective_date
        )
        session.add(historical_doc)
        session.flush()
        imported_count += 1

    session.commit()
    populate_fts(session)
    session.close()
    print(f"✅ Imported {imported_count} documents and updated FTS index from {filepath}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python import_data.py <path_to_json_file>")
    else:
        import_json_file(sys.argv[1])
