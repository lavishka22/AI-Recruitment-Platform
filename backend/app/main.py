from fastapi import FastAPI
from app.core.supabase_client import supabase
from app.api.upload import router as upload_router
from app.api.resume import router as resume_router
from app.api.evaluation import router as evaluation_router
from app.api.github import router as github_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Recruitment Platform",
    version="1.0.0",
    description="AI-powered candidate screening platform."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(resume_router)
app.include_router(evaluation_router)
app.include_router(github_router)

@app.get("/")
def root():
    return {
        "message": "AI Recruitment Platform Backend is Running!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.get("/health/database")
def database_health():
    try:
        supabase.table("candidates").select("id").limit(1).execute()

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as exc:
        return {
            "status": "configuration_loaded",
            "database": "table_not_ready",
            "detail": str(exc)
        }