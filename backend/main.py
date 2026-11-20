import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.core.config import settings
from backend.api.routes import router as api_router

app = FastAPI(
    title="AI ATS Resume Scorer & Analyzer API",
    description="Production-grade ATS scoring, semantic job description matching, and PDF diagnostic reports.",
    version="1.0.0"
)

# Enable CORS for Streamlit and Netlify frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Mount netlify-app static frontend if directory exists
netlify_app_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "netlify-app")
if os.path.exists(netlify_app_dir):
    app.mount("/app", StaticFiles(directory=netlify_app_dir, html=True), name="netlify-app")

@app.get("/")
async def root():
    return {
        "message": "AI ATS Resume Scorer API is online.",
        "documentation": "/docs",
        "health": "/api/health",
        "web_app": "/app/"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.FASTAPI_PORT, reload=True)
