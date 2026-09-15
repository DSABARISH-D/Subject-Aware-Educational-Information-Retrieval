from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from crud.subject_manager import create_subject as create_subject_crud, get_subjects as get_subjects_crud
from database import get_db
from models.subject import Subject as SubjectModel
from schemas import Subject, SubjectCreate
from typing import List

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.post("/", response_model=Subject)
def create_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new subject.
    """
    return create_subject_crud(db=db, subject=subject)


@router.post("/create")
def create_subject_form(
    name: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Create a new subject from HTML form submission.
    """
    subject_data = SubjectCreate(name=name, description=description)
    create_subject_crud(db=db, subject=subject_data)
    return RedirectResponse(url="/", status_code=302)


@router.get("/", response_model=List[Subject])
def get_subjects(
    db: Session = Depends(get_db),
):
    """
    Get all subjects.
    """
    return get_subjects_crud(db=db)


@router.get("/{subject_id}/dashboard", response_class=HTMLResponse)
def get_subject_dashboard(
    subject_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the subject-specific dashboard for document upload and chat.
    """
    subject = get_subjects_crud(db)
    from crud.subject_manager import get_subject
    subject = get_subject(db, subject_id)
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    return get_subject_dashboard_html(subject)


@router.get("/{subject_id}/documents/{document_id}/chunks", response_class=HTMLResponse)
def get_document_chunks(
    subject_id: str,
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the chunks view for a specific document.
    """
    from models.document import Document
    from models.chunk import Chunk as ChunkModel
    from crud.subject_manager import get_subject
    from database import IS_SQLITE
    
    subject = get_subject(db, subject_id)
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    doc_id_val = document_id if IS_SQLITE else document_id
    sub_id_val = subject_id if IS_SQLITE else subject_id
    
    document = db.query(Document).filter(
        Document.id == doc_id_val,
        Document.subject_id == sub_id_val
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = db.query(ChunkModel).filter(
        ChunkModel.document_id == doc_id_val
    ).all()
    
    return get_document_chunks_html(subject, document, chunks)


def get_subject_dashboard_html(subject: SubjectModel):
    """
    Generate the HTML for the subject dashboard.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{subject.name} - Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 30px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e9ecef;
            }}
            .subject-info h1 {{
                color: #2c3e50;
                margin: 0;
            }}
            .subject-info p {{
                color: #6c757d;
                margin: 5px 0 0 0;
            }}
            .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }}
            .btn-primary {{
                background-color: #007bff;
                color: white;
            }}
            .btn-secondary {{
                background-color: #6c757d;
                color: white;
            }}
            .dashboard-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin-top: 30px;
            }}
            .card {{
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                border: 1px solid #e9ecef;
            }}
            .card h2 {{
                color: #2c3e50;
                margin-top: 0;
                margin-bottom: 15px;
            }}
            .card p {{
                color: #6c757d;
                margin-bottom: 20px;
            }}
            .upload-area {{
                border: 2px dashed #007bff;
                border-radius: 8px;
                padding: 40px;
                text-align: center;
                margin-bottom: 20px;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            .upload-area:hover {{
                background-color: #f0f8ff;
            }}
            .upload-area input[type="file"] {{
                display: none;
            }}
            .file-list {{
                margin-top: 15px;
                margin-bottom: 20px;
            }}
            .file-item {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px;
                background: #e9ecef;
                border-radius: 4px;
                margin: 5px 0;
            }}
            .file-info {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .file-icon {{
                font-size: 18px;
            }}
            .file-name {{
                font-weight: 500;
                color: #2c3e50;
            }}
            .file-size {{
                color: #6c757d;
                font-size: 14px;
            }}
            .remove-file {{
                background: #dc3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                cursor: pointer;
                font-size: 12px;
            }}
            .remove-file:hover {{
                background: #c82333;
            }}
            .toast {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 5px;
                color: white;
                font-weight: 500;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 1000;
                min-width: 300px;
            }}
            .toast.show {{
                transform: translateX(0);
            }}
            .toast-success {{
                background-color: #28a745;
            }}
            .toast-error {{
                background-color: #dc3545;
            }}
            .toast-info {{
                background-color: #17a2b8;
            }}
            .progress-container {{
                display: none;
                margin-top: 20px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #17a2b8;
            }}
            .progress-bar {{
                width: 100%;
                height: 20px;
                background-color: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }}
            .progress-fill {{
                height: 100%;
                background-color: #007bff;
                transition: width 0.3s ease;
            }}
            .progress-text {{
                text-align: center;
                margin: 10px 0;
                font-weight: 500;
            }}
            .progress-details {{
                font-size: 14px;
                color: #6c757d;
                margin-top: 10px;
            }}
            .chat-area {{
                border: 1px solid #dee2e6;
                border-radius: 8px;
                height: 400px;
                display: flex;
                flex-direction: column;
            }}
            .chat-messages {{
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                background-color: #fff;
            }}
            .chat-input {{
                display: flex;
                padding: 15px;
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }}
            .chat-input input {{
                flex: 1;
                padding: 10px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                margin-right: 10px;
            }}
            .document-list {{
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
            }}
            .document-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 15px;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            }}
            .document-item:hover {{
                background-color: #f8f9fa;
            }}
            .document-item:last-child {{
                border-bottom: none;
            }}
            .document-info {{
                display: flex;
                flex-direction: column;
                flex: 1;
                cursor: pointer;
            }}
            .document-info:hover .document-name {{
                color: #007bff;
                text-decoration: underline;
            }}
            .document-name {{
                font-weight: 500;
                color: #2c3e50;
                margin-bottom: 4px;
            }}
            .document-meta {{
                font-size: 12px;
                color: #6c757d;
            }}
            .document-actions {{
                display: flex;
                gap: 8px;
            }}
            .btn-delete {{
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 12px;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            .btn-delete:hover {{
                background-color: #c82333;
            }}
            .btn-refresh {{
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 12px;
                font-size: 14px;
                cursor: pointer;
                transition: background-color 0.2s;
                margin-bottom: 15px;
            }}
            .btn-refresh:hover {{
                background-color: #138496;
            }}
            .no-documents {{
                text-align: center;
                padding: 40px 20px;
                color: #6c757d;
            }}
            @media (max-width: 768px) {{
                .dashboard-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="subject-info">
                    <h1>📚 {subject.name}</h1>
                    <p>{subject.description}</p>
                </div>
                <div class="nav-buttons">
                    <a href="/" class="btn btn-secondary">← Back to Subjects</a>
                </div>
            </div>
            
            <!-- Chat Section - Full Width -->
            <div class="chat-section">
                <div class="card">
                    <h2>💬 Subject Question Answering</h2>
                    <p>Ask questions about uploaded materials for <strong>{subject.name}</strong></p>
                    
                    <div class="chat-area">
                        <div class="chat-messages" id="chatMessages">
                            <p style="text-align: center; color: #6c757d; margin-top: 50px;">
                                Upload course materials to start searching and asking questions!
                            </p>
                        </div>
                        <div class="chat-input">
                            <input type="text" id="chatInput" placeholder="Ask a question about {subject.name}...">
                            <button class="btn btn-primary" onclick="sendMessage()">Ask</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Upload and Library Section - Two Columns -->
            <div class="dashboard-grid">
                <div class="card">
                    <h2>📁 Upload Subject Material</h2>
                    <p>Upload slides, notes, or textbooks for this subject</p>
                    
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" multiple accept=".pdf,.doc,.docx,.txt,.md">
                        <p>📄 Click to upload files</p>
                        <p>Supported formats: PDF, DOC, DOCX, TXT, MD</p>
                    </div>
                    
                    <div id="fileList" class="file-list"></div>
                    <button class="btn btn-primary" onclick="uploadFiles()" id="uploadButton" style="display: none;">Upload Material</button>
                    
                    <div id="progressContainer" class="progress-container">
                        <h4>Processing Materials...</h4>
                        <div class="progress-bar">
                            <div id="progressFill" class="progress-fill" style="width: 0%"></div>
                        </div>
                        <div id="progressText" class="progress-text">0% Complete</div>
                        <div id="progressDetails" class="progress-details">
                            Processed: <span id="processedCount">0</span> / <span id="totalCount">0</span> files
                            <span id="failedCount" style="display: none;"> • Failed: <span>0</span></span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>📚 Subject Materials Library</h2>
                    <p>Manage documents uploaded to {subject.name}</p>
                    
                    <button class="btn-refresh" onclick="loadDocuments()">🔄 Refresh</button>
                    
                    <div id="documentLibrary" class="document-list">
                        <div class="no-documents">
                            <p>📂 No materials uploaded yet</p>
                            <p>Upload materials to get started!</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const subjectId = "{subject.id}";
            
            let selectedFiles = [];
            let currentJobId = null;
            let pollInterval = null;
            
            function showToast(message, type = 'info') {{
                const toast = document.createElement('div');
                toast.className = `toast toast-${{type}}`;
                toast.textContent = message;
                document.body.appendChild(toast);
                
                setTimeout(() => {{
                    toast.classList.add('show');
                }}, 100);
                
                setTimeout(() => {{
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 300);
                }}, 4000);
            }}
            
            function uploadFiles() {{
                if (selectedFiles.length === 0) {{
                    showToast('Please select files to upload', 'error');
                    return;
                }}
                
                const formData = new FormData();
                selectedFiles.forEach(file => {{
                    formData.append('files', file);
                }});
                
                document.getElementById('uploadButton').disabled = true;
                document.getElementById('uploadButton').textContent = 'Uploading...';
                
                fetch(`/documents/upload/${{subjectId}}`, {{
                    method: 'POST',
                    body: formData
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.job_id) {{
                        currentJobId = data.job_id;
                        showToast(`Upload started! Processing ${{data.total_files}} files...`, 'success');
                        
                        selectedFiles = [];
                        document.getElementById('fileInput').value = '';
                        document.getElementById('fileList').innerHTML = '';
                        document.getElementById('uploadButton').style.display = 'none';
                        
                        showProgressUI(data.total_files);
                        startPollingJobStatus(currentJobId);
                    }} else {{
                        throw new Error('No job ID received');
                    }}
                }})
                .catch(error => {{
                    showToast('Upload failed: ' + error.message, 'error');
                    resetUploadButton();
                }});
            }}
            
            function resetUploadButton() {{
                document.getElementById('uploadButton').disabled = false;
                document.getElementById('uploadButton').textContent = 'Upload Material';
            }}
            
            function showProgressUI(totalFiles) {{
                const container = document.getElementById('progressContainer');
                const totalCount = document.getElementById('totalCount');
                
                totalCount.textContent = totalFiles;
                container.style.display = 'block';
                container.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}
            
            function hideProgressUI() {{
                document.getElementById('progressContainer').style.display = 'none';
                resetUploadButton();
            }}
            
            function updateProgressUI(status) {{
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');
                const processedCount = document.getElementById('processedCount');
                const failedCountElement = document.getElementById('failedCount');
                const failedCountSpan = failedCountElement.querySelector('span');
                
                const percentage = status.progress.percentage;
                progressFill.style.width = percentage + '%';
                progressText.textContent = percentage + '% Complete';
                processedCount.textContent = status.progress.processed_files;
                
                if (status.progress.failed_files > 0) {{
                    failedCountSpan.textContent = status.progress.failed_files;
                    failedCountElement.style.display = 'inline';
                }} else {{
                    failedCountElement.style.display = 'none';
                }}
            }}
            
            function startPollingJobStatus(jobId) {{
                pollInterval = setInterval(async () => {{
                    try {{
                        const response = await fetch(`/jobs/${{jobId}}/status`);
                        const status = await response.json();
                        
                        updateProgressUI(status);
                        
                        if (status.status === 'completed') {{
                            clearInterval(pollInterval);
                            const successCount = status.progress.processed_files - status.progress.failed_files;
                            let message = `Processing complete! ${{successCount}} files processed successfully.`;
                            
                            if (status.progress.failed_files > 0) {{
                                message += ` ${{status.progress.failed_files}} files failed.`;
                                showToast(message, 'info');
                            }} else {{
                                showToast(message, 'success');
                            }}
                            
                            setTimeout(() => {{
                                hideProgressUI();
                                refreshDocumentsAfterUpload();
                            }}, 3000);
                            
                        }} else if (status.status === 'failed') {{
                            clearInterval(pollInterval);
                            showToast('Processing failed: ' + (status.error_message || 'Unknown error'), 'error');
                            hideProgressUI();
                        }}
                    }} catch (error) {{
                        clearInterval(pollInterval);
                        showToast('Error checking status: ' + error.message, 'error');
                        hideProgressUI();
                    }}
                }}, 2000);
            }}
            
            function removeFile(index) {{
                selectedFiles.splice(index, 1);
                updateFileList();
            }}
            
            function getFileIcon(filename) {{
                const extension = filename.split('.').pop().toLowerCase();
                switch(extension) {{
                    case 'pdf': return '📄';
                    case 'doc':
                    case 'docx': return '📝';
                    case 'txt': return '📰';
                    case 'md': return '📋';
                    default: return '📄';
                }}
            }}
            
            function formatFileSize(bytes) {{
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            }}
            
            function updateFileList() {{
                const fileList = document.getElementById('fileList');
                const uploadButton = document.getElementById('uploadButton');
                
                if (selectedFiles.length === 0) {{
                    fileList.innerHTML = '';
                    uploadButton.style.display = 'none';
                    return;
                }}
                
                fileList.innerHTML = selectedFiles.map((file, index) => {{
                    return `
                        <div class="file-item">
                            <div class="file-info">
                                <span class="file-icon">${{getFileIcon(file.name)}}</span>
                                <div>
                                    <div class="file-name">${{file.name}}</div>
                                    <div class="file-size">${{formatFileSize(file.size)}}</div>
                                </div>
                            </div>
                            <button class="remove-file" onclick="removeFile(${{index}})">Remove</button>
                        </div>
                    `;
                }}).join('');
                
                uploadButton.style.display = 'block';
            }}
            
            function sendMessage() {{
                const input = document.getElementById('chatInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                const messagesDiv = document.getElementById('chatMessages');
                messagesDiv.innerHTML += `<div style="margin-bottom: 10px;"><strong>You:</strong> ${{message}}</div>`;
                
                input.value = '';
                
                const typingIndicator = `<div id="typingIndicator" style="margin-bottom: 10px; color: #6c757d; font-style: italic;">System searching subject material...</div>`;
                messagesDiv.innerHTML += typingIndicator;
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
                
                fetch(`/subjects/${{subjectId}}/chat/`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ text: message }})
                }})
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    const typingDiv = document.getElementById('typingIndicator');
                    if (typingDiv) typingDiv.remove();
                    
                    const badge = data.is_covered
                        ? '<span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-bottom: 6px; display: inline-block;">Covered in Subject Material: YES</span>'
                        : '<span style="background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-bottom: 6px; display: inline-block;">Covered in Subject Material: NO</span>';
                    
                    let responseHtml = `<div style="margin-bottom: 12px; padding: 12px; background: #f0f8ff; border-radius: 6px; border-left: 4px solid ${{data.is_covered ? '#28a745' : '#dc3545'}};">${{badge}}<br><strong>Assistant:</strong> ${{data.response}}`;
                    
                    if (data.sources && data.sources.length > 0) {{
                        responseHtml += `<br><small style="color: #6c757d; margin-top: 8px; display: block;"><strong>Sources:</strong></small>`;
                            data.sources.forEach((source, index) => {{
                            const page = source.page_number ? ` - page ${{source.page_number}}` : '';
                            responseHtml += `<small style="color: #6c757d; display: block;">• ${{source.document_name}}${{page}} (Score: ${{source.relevance_score.toFixed(2)}})</small>`;
                        }});
                    }}
                    
                    responseHtml += `</div>`;
                    messagesDiv.innerHTML += responseHtml;
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }})
                .catch(error => {{
                    const typingDiv = document.getElementById('typingIndicator');
                    if (typingDiv) typingDiv.remove();
                    
                    messagesDiv.innerHTML += `<div style="margin-bottom: 10px; color: red; padding: 10px; background: #ffe6e6; border-radius: 4px;"><strong>Error:</strong> ${{error.message}}</div>`;
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }});
            }}
            
            document.getElementById('fileInput').addEventListener('change', function(e) {{
                selectedFiles = Array.from(e.target.files);
                updateFileList();
            }});
            
            document.getElementById('chatInput').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    sendMessage();
                }}
            }});
            
            async function loadDocuments() {{
                try {{
                    const response = await fetch(`/subjects/${{subjectId}}/documents/`);
                    const documents = await response.json();
                    
                    displayDocuments(documents);
                }} catch (error) {{
                    showToast('Error loading documents: ' + error.message, 'error');
                }}
            }}
            
            function displayDocuments(documents) {{
                const library = document.getElementById('documentLibrary');
                
                if (!documents || documents.length === 0) {{
                    library.innerHTML = `
                        <div class="no-documents">
                            <p>📂 No materials uploaded yet</p>
                            <p>Upload materials to get started!</p>
                        </div>
                    `;
                    return;
                }}
                
                library.innerHTML = documents.map(doc => {{
                    const uploadDate = new Date(doc.created_at).toLocaleDateString();
                    
                    return `
                        <div class="document-item">
                            <div class="document-info" onclick="viewDocumentChunks('${{doc.id}}')">
                                <div class="document-name">${{doc.name}}</div>
                                <div class="document-meta">Uploaded on ${{uploadDate}}</div>
                            </div>
                            <div class="document-actions">
                                <button class="btn-delete" onclick="deleteDocument('${{doc.id}}', '${{doc.name}}')">Delete</button>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}
            
            function viewDocumentChunks(documentId) {{
                window.location.href = `/subjects/${{subjectId}}/documents/${{documentId}}/chunks`;
            }}
            
            async function deleteDocument(documentId, documentName) {{
                if (!confirm(`Are you sure you want to delete "${{documentName}}"?`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/subjects/${{subjectId}}/documents/${{documentId}}`, {{
                        method: 'DELETE'
                    }});
                    
                    if (response.ok) {{
                        showToast(`Deleted "${{documentName}}"`, 'success');
                        loadDocuments();
                    }} else {{
                        const error = await response.json();
                        showToast('Failed to delete document: ' + (error.detail || 'Unknown error'), 'error');
                    }}
                }} catch (error) {{
                    showToast('Error deleting document: ' + error.message, 'error');
                }}
            }}
            
            function refreshDocumentsAfterUpload() {{
                loadDocuments();
            }}
            
            loadDocuments();
        </script>
    </body>
    </html>
    """
    return html_content


def get_document_chunks_html(subject: SubjectModel, document, chunks):
    """
    Generate HTML view for document chunks.
    """
    chunks_html = ""
    for i, chunk in enumerate(chunks):
        chunks_html += f"""
        <div style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 15px; margin-bottom: 15px;">
            <div style="font-weight: 500; color: #007bff; margin-bottom: 8px;">Chunk #{i+1} (ID: {chunk.id})</div>
            <div style="white-space: pre-wrap; font-family: monospace; font-size: 14px; background: #fff; padding: 10px; border-radius: 4px; border: 1px solid #dee2e6;">{chunk.content}</div>
        </div>
        """
    
    if not chunks:
        chunks_html = "<p style='color: #6c757d;'>No chunks found for this document.</p>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{document.name} - Chunks</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 30px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e9ecef;
            }}
            .btn {{
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                background-color: #6c757d;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>📄 Document Chunks: {document.name}</h1>
                    <p style="color: #6c757d;">Subject: {subject.name} | Total Chunks: {len(chunks)}</p>
                </div>
                <div>
                    <a href="/subjects/{subject.id}/dashboard" class="btn">← Back to Dashboard</a>
                </div>
            </div>
            <div>
                {chunks_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html_content
