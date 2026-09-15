"""Preload every PDF under study_material/<subject>/ into the existing RAG database."""

import argparse
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from models.subject import Subject
from rag.ingestion import ingest_file


def run(root: Path) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("bulk_ingest")
    subjects = [path for path in root.iterdir() if path.is_dir()]
    files = sorted(path for subject in subjects for path in subject.rglob("*.pdf"))
    summary = {"subjects": len(subjects), "pdfs": 0, "chunks": 0, "skipped": 0, "errors": []}
    db = SessionLocal()
    try:
        for subject_path in sorted(subjects, key=lambda path: path.name.lower()):
            subject = db.query(Subject).filter(Subject.name == subject_path.name).first()
            if not subject:
                subject = Subject(name=subject_path.name, description="Auto-created from study_material")
                db.add(subject)
                db.commit()
                db.refresh(subject)
            logger.info("Found subject: %s", subject_path.name)

            for file_path in sorted(subject_path.rglob("*.pdf"), key=lambda path: str(path).lower()):
                relative_name = file_path.relative_to(root).as_posix()
                logger.info("Found file: %s", relative_name)
                try:
                    result = ingest_file(db, file_path.read_bytes(), file_path.name, subject.id, "site", logger)
                    if result is None:
                        summary["skipped"] += 1
                        logger.info("[SKIP] %s", relative_name)
                        logger.info("Status: SKIPPED (already ingested)")
                        continue
                    summary["pdfs"] += 1
                    summary["chunks"] += result["inserted"]
                    logger.info("[%s] %s", result["action"], relative_name)
                    logger.info("Pages: %s", result["pages"])
                    logger.info("Chunks created: %s", result["chunks"])
                    logger.info("Embeddings generated: %s", result["embeddings"])
                    logger.info("Inserted: %s", result["inserted"])
                    logger.info("Status: SUCCESS")
                except Exception as error:
                    db.rollback()
                    summary["errors"].append({"file": relative_name, "error": str(error)})
                    logger.error("Status: FAILED - %s", error)
    finally:
        db.close()

    logger.info("Detected subjects: %s", summary["subjects"])
    logger.info("PDFs processed: %s", summary["pdfs"])
    logger.info("Chunks inserted: %s", summary["chunks"])
    logger.info("PDFs skipped: %s", summary["skipped"])
    if summary["errors"]:
        logger.error("Errors: %s", summary["errors"])
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "study_material",
        help="Internal lecture root; each immediate child directory is a subject",
    )
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"Study material directory not found: {args.root}")
    run(args.root)