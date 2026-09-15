from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from routes import (
    subject_router,
    document_router,
    search_router,
    chat_router,
    jobs_router,
    documents_upload_router
)
from config import settings
from database import Base, engine, SessionLocal
from models.subject import Subject
from utils.logging import setup_logging, get_logger, log_api_request, log_error
import time

# Set up logging
setup_logging(
    log_level="INFO",
    log_file="logs/app.log"
)
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Subject-Aware Educational Information Retrieval",
    description="Subject-Aware Educational Search & RAG System for course materials.",
    version="1.0.0"
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        log_api_request(
            logger,
            method=request.method,
            endpoint=str(request.url.path),
            duration=process_time
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        log_error(logger, e, {
            "method": request.method,
            "endpoint": str(request.url.path),
            "duration": process_time
        })
        raise

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(subject_router)
app.include_router(document_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(documents_upload_router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Home page for Subject-Aware Educational Information Retrieval.
    """
    db = SessionLocal()
    subjects = []
    try:
        subjects = db.query(Subject).all()
    finally:
        db.close()
    
    return get_home_page_html(subjects)


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify system configuration.
    """
    config_status = {
        "gemini_configured": bool(settings.gemini_api_key),
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "database_configured": bool(settings.database_url),
    }
    
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        config_status["database_connected"] = True
    except Exception as e:
        config_status["database_connected"] = False
        config_status["database_error"] = str(e)
    
    all_configured = all([config_status["gemini_configured"], config_status["database_connected"]])
    
    return {
        "status": "healthy" if all_configured else "configuration_needed",
        "config": config_status
    }


def get_home_page_html(subjects: list = []):
    """
    Generate the home page HTML for Subject-Aware Search.
    """
    subject_list_items = ""
    if subjects:
        for subject in subjects:
            subject_list_items += f"""
            <li class='subject-item'>
                <a href='/subjects/{subject.id}/dashboard' class='subject-link'>
                    <strong>📚 {subject.name}</strong>: {subject.description or 'No description'}
                </a>
            </li>
            """
    else:
        subject_list_items = "<p style='color: #6c757d;'>No subjects created yet. Add one below!</p>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Subject-Aware Educational Information Retrieval</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background-color: #f0f2f5;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                width: 100%;
                max-width: 900px;
                margin: 20px;
                padding: 40px;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            h1 {{
                color: #2c3e50;
                margin-top: 0;
            }}
            .subtitle {{
                color: #6c757d;
                font-size: 16px;
                margin-bottom: 30px;
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
            .subjects-section, .create-subject-form {{
                margin-bottom: 30px;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }}
            .subject-list {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .subject-item {{
                padding: 10px 0;
                border-bottom: 1px solid #eeeeee;
            }}
            .subject-item:last-child {{
                border-bottom: none;
            }}
            .subject-link {{
                color: #007bff;
                text-decoration: none;
                display: block;
                padding: 10px;
                border-radius: 4px;
                transition: background-color 0.2s;
            }}
            .subject-link:hover {{
                background-color: #e9ecef;
            }}
            .create-subject-form input[type="text"] {{
                width: 100%;
                padding: 10px;
                margin-bottom: 10px;
                border: 1px solid #cccccc;
                border-radius: 5px;
                box-sizing: border-box;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 Subject-Aware Educational Information Retrieval</h1>
            <div class="subtitle">
                Select a subject to upload course materials and perform strict subject-isolated question answering.
            </div>

            <div class="subjects-section">
                <h3>📖 Select a Subject</h3>
                <label for="subjectDropdown">Search subject</label>
                <select id="subjectDropdown" onchange="if (this.value) window.location.href='/subjects/' + this.value + '/dashboard'">
                    <option value="">Choose a subject...</option>
                    {''.join(f"<option value='{subject.id}'>{subject.name}</option>" for subject in subjects)}
                </select>
                <ul class="subject-list">
                    {subject_list_items}
                </ul>
            </div>

            <div class="create-subject-form">
                <h3>➕ Add a New Subject</h3>
                <form action="/subjects/create" method="post">
                    <input type="text" name="name" placeholder="Subject Name (e.g., Operating Systems, Data Structures)" required>
                    <input type="text" name="description" placeholder="Subject Description (e.g., Course CS301 Fall 2026)" required>
                    <button type="submit" class="btn btn-primary">Create Subject</button>
                </form>
            </div>
        </div>
        <script>
            fetch('/subjects/')
                .then(response => response.json())
                .then(subjects => {{
                    const dropdown = document.getElementById('subjectDropdown');
                    subjects.forEach(subject => {{
                        if (![...dropdown.options].some(option => option.value === subject.id)) {{
                            dropdown.add(new Option(subject.name, subject.id));
                        }}
                    }});
                }});
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug
    )
