from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # Load .env file

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import engine, Base
from routers import projects, tasks, epics, sprints, labels, github, gmail, whatsapp, ai, logs

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Planner API", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(epics.router, prefix="/api")
app.include_router(sprints.router, prefix="/api")
app.include_router(labels.router, prefix="/api")
app.include_router(github.router, prefix="/api")
app.include_router(gmail.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve index.html for all non-API routes (SPA routing)
        return FileResponse(FRONTEND_DIR / "index.html")
