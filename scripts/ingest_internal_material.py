"""
Bulk ingestion script for internal lecture material.

Scans the `leacher matial/` directory and ingests all PDFs into the database,
creating Subject records from folder names and Document/Chunk records from PDFs.

Usage:
    python scripts/ingest_internal_material.py
"""
import os
import sys
import time
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from database import SessionLocal, Base, engine, ensure_sqlite_schema
from models.subject import Subject
from models.document import Document
from models.chunk import Chunk
from rag.ingestion import ingest_file
from config import settings

# Path to internal lecture material (relative to project root)
MATERIAL_DIR = os.path.join(PROJECT_ROOT, "leacher matial")


def get_or_create_subject(db, name: str) -> Subject:
    """Get existing subject by name or create a new one."""
    subject = db.query(Subject).filter(Subject.name == name).first()
    if subject:
        return subject
    subject = Subject(name=name, description=f"Internal course material for {name}")
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def collect_pdfs(base_dir: str) -> list:
    """Collect all PDF files grouped by subject (parent folder)."""
    results = []
    if not os.path.isdir(base_dir):
        print(f"[ERROR] Material directory not found: {base_dir}")
        return results

    for subject_folder in sorted(os.listdir(base_dir)):
        subject_path = os.path.join(base_dir, subject_folder)
        if not os.path.isdir(subject_path):
            continue
        for filename in sorted(os.listdir(subject_path)):
            if filename.lower().endswith(".pdf"):
                filepath = os.path.join(subject_path, filename)
                results.append({
                    "subject_name": subject_folder,
                    "filename": filename,
                    "filepath": filepath,
                })
    return results


def main():
    print("=" * 70)
    print("  Subject-Aware Educational Information Retrieval")
    print("  Internal Lecture Material Ingestion")
    print("=" * 70)

    # Check Gemini API key
    if not settings.gemini_api_key:
        print("\n[ERROR] GEMINI_API_KEY is not set!")
        print("Please set it in your .env file or as an environment variable.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema()

    # Collect PDF files
    pdfs = collect_pdfs(MATERIAL_DIR)
    if not pdfs:
        print(f"\n[ERROR] No PDF files found in: {MATERIAL_DIR}")
        sys.exit(1)

    print(f"\nFound {len(pdfs)} PDF files in {MATERIAL_DIR}")

    # Group by subject for display
    subjects_found = {}
    for pdf in pdfs:
        subj = pdf["subject_name"]
        subjects_found.setdefault(subj, []).append(pdf["filename"])

    print(f"Subjects: {len(subjects_found)}")
    for subj_name, files in subjects_found.items():
        print(f"  [DIR] {subj_name}: {len(files)} PDFs")

    # Create database session
    db = SessionLocal()

    total = len(pdfs)
    ingested = 0
    skipped = 0
    failed = 0
    start_time = time.time()

    try:
        for i, pdf in enumerate(pdfs, 1):
            subject_name = pdf["subject_name"]
            filename = pdf["filename"]
            filepath = pdf["filepath"]

            print(f"\n[{i}/{total}] Processing: {subject_name}/{filename}")

            # Get or create subject
            subject = get_or_create_subject(db, subject_name)

            # Read file content
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
            except Exception as e:
                print(f"  [FAIL] Cannot read file: {e}")
                failed += 1
                continue

            # Ingest through the shared pipeline
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = ingest_file(
                        db=db,
                        content=content,
                        filename=filename,
                        subject_id=subject.id,
                        source_type="site",
                    )

                    if result is None:
                        print(f"  [SKIP] Already indexed (identical content)")
                        skipped += 1
                    else:
                        action = result.get("action", "INGEST")
                        pages = result.get("pages", 0)
                        chunks = result.get("chunks", 0)
                        print(f"  [{action}] OK {pages} pages -> {chunks} chunks embedded")
                        ingested += 1
                    break # Success
                except Exception as e:
                    error_msg = str(e)
                    db.rollback()
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        if attempt < max_retries - 1:
                            delay = 45 # Wait 45 seconds to reset minute quota
                            print(f"  [RATE LIMIT] Quota exceeded. Waiting {delay}s (Attempt {attempt+1}/{max_retries})...")
                            time.sleep(delay)
                        else:
                            print(f"  [FAIL] ERROR: Max retries reached after rate limit. {e}")
                            failed += 1
                    else:
                        print(f"  [FAIL] ERROR: {e}")
                        failed += 1
                        break

    finally:
        db.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  Ingestion Complete in {elapsed:.1f}s")
    print(f"  Ingested: {ingested}  |  Skipped: {skipped}  |  Failed: {failed}")
    print("=" * 70)

    # Verify final state
    db2 = SessionLocal()
    try:
        subject_count = db2.query(Subject).count()
        doc_count = db2.query(Document).count()
        chunk_count = db2.query(Chunk).count()
        print(f"\n  Database State:")
        print(f"    Subjects: {subject_count}")
        print(f"    Documents: {doc_count}")
        print(f"    Chunks: {chunk_count}")
    finally:
        db2.close()


if __name__ == "__main__":
    main()
