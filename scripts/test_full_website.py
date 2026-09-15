#!/usr/bin/env python3
"""
Full website end-to-end testing script for Subject-Aware Educational Information Retrieval.
"""

import sys
import os

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, Base, engine
from models.subject import Subject
from models.document import Document
from models.chunk import Chunk
from unittest.mock import patch, MagicMock


def test_full_website():
    print("=" * 60)
    print("🎓 FULL WEBSITE END-TO-END AUTOMATED TEST")
    print("=" * 60)
    
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    # 1. Test Home Page
    print("\n1. Testing Home Page (GET /)...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "Subject-Aware Educational Information Retrieval" in res.text
    print("   ✅ Home Page loaded successfully!")
    
    # 2. Test Creating a Subject via Form
    print("\n2. Testing Subject Creation (POST /subjects/create)...")
    res = client.post(
        "/subjects/create",
        data={"name": "Operating Systems", "description": "CS301 Course Material"},
        follow_redirects=False
    )
    assert res.status_code in [302, 303], f"Expected redirect, got {res.status_code}"
    print("   ✅ Subject 'Operating Systems' created successfully via form!")
    
    # Verify subject in DB
    db = SessionLocal()
    subject_os = db.query(Subject).filter(Subject.name == "Operating Systems").first()
    assert subject_os is not None, "Subject 'Operating Systems' not found in database"
    os_id = str(subject_os.id)
    print(f"   ✅ Subject ID: {os_id}")
    
    # 3. Create a second subject for Subject-Isolation Verification
    print("\n3. Creating second Subject for Subject-Isolation Test ('Data Structures')...")
    res = client.post(
        "/subjects/create",
        data={"name": "Data Structures", "description": "CS201 Course Material"},
        follow_redirects=False
    )
    subject_ds = db.query(Subject).filter(Subject.name == "Data Structures").first()
    ds_id = str(subject_ds.id)
    print(f"   ✅ Subject ID ('Data Structures'): {ds_id}")
    
    # 4. Test Subject Dashboard HTML rendering
    print(f"\n4. Testing Subject Dashboard UI (GET /subjects/{os_id}/dashboard)...")
    res = client.get(f"/subjects/{os_id}/dashboard")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "Operating Systems" in res.text
    assert "Covered in Subject Material" in res.text
    print("   ✅ Dashboard HTML rendered successfully with Subject Question Answering UI & Coverage badges!")
    
    # 5. Test Uploading Document to Subject
    print(f"\n5. Testing Document Upload to Operating Systems (POST /subjects/{os_id}/documents/)...")
    doc_content = b"Process Control Block (PCB) contains OS information such as process state, CPU registers, and memory management info."
    
    with patch("rag.processing.get_embeddings") as mock_embed:
        mock_embed.return_value = [[0.1] * 1536]
        
        res = client.post(
            f"/subjects/{os_id}/documents/",
            files={"file": ("process_management.txt", doc_content, "text/plain")}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        doc_data = res.json()
        doc_id = doc_data["id"]
        print(f"   ✅ Document uploaded & chunked successfully! Document ID: {doc_id}")
    
    # 6. Test Document List Endpoint
    print(f"\n6. Testing Document List (GET /subjects/{os_id}/documents/)...")
    res = client.get(f"/subjects/{os_id}/documents/")
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1
    print(f"   ✅ Retrieved {len(docs)} document(s) for subject.")
    
    # 7. Test Subject-Isolated Question Answering & Coverage Flag
    print(f"\n7. Testing Subject-Aware Chat & Coverage Flag (POST /subjects/{os_id}/chat/)...")
    with patch("rag.processing.get_embeddings") as mock_embed, \
         patch("crud.chat_manager.get_completion") as mock_completion:
        
        mock_embed.return_value = [[0.1] * 1536]
        mock_completion.return_value = '{"is_covered": true, "response": "A Process Control Block (PCB) stores process state and CPU registers [Source 1]."}'
        
        res = client.post(
            f"/subjects/{os_id}/chat/",
            json={"text": "What is a Process Control Block?"}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        chat_res = res.json()
        assert chat_res["is_covered"] is True, "Expected is_covered = True"
        assert "Process Control Block" in chat_res["response"]
        assert len(chat_res["sources"]) > 0
        print("   ✅ Chat endpoint returned grounded answer with explicit is_covered: True flag and source citations!")
    
    # 8. Test Question NOT covered by subject material
    print(f"\n8. Testing Un-covered Question Response (POST /subjects/{os_id}/chat/)...")
    with patch("rag.processing.get_embeddings") as mock_embed, \
         patch("crud.chat_manager.get_completion") as mock_completion:
        
        mock_embed.return_value = [[0.1] * 1536]
        mock_completion.return_value = '{"is_covered": false, "response": "The uploaded material for Operating Systems does not cover photosynthesis."}'
        
        res = client.post(
            f"/subjects/{os_id}/chat/",
            json={"text": "How does photosynthesis work in plants?"}
        )
        assert res.status_code == 200
        chat_res = res.json()
        assert chat_res["is_covered"] is False, "Expected is_covered = False"
        print("   ✅ System correctly flagged un-covered question with is_covered: False!")
    
    # 9. Test Strict Subject Isolation (Data Structures vs Operating Systems)
    print(f"\n9. Testing Strict Subject Isolation (Searching 'Data Structures' for 'Operating Systems' material)...")
    res = client.get(f"/subjects/{ds_id}/documents/")
    assert res.status_code == 200
    assert len(res.json()) == 0, "Data Structures should have 0 documents."
    
    res = client.post(
        f"/subjects/{ds_id}/chat/",
        json={"text": "What is a Process Control Block?"}
    )
    assert res.status_code == 200
    chat_res = res.json()
    assert chat_res["is_covered"] is False, "Data Structures material should not cover OS content!"
    assert len(chat_res["sources"]) == 0
    print("   ✅ Strict Subject Isolation verified! Data Structures query retrieved 0 sources from Operating Systems.")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("🎉 ALL FULL-WEBSITE END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_full_website()
    sys.exit(0 if success else 1)
