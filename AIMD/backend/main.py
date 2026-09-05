from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.upload import router as upload_router
from origin.routes import router as origin_router


app = FastAPI(
    title="AIMD Forensic Engine",
    description="AI-generated and AI-altered media forensic analysis platform",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload_router)
app.include_router(origin_router)


@app.get("/")
def root():
    return {
        "project": "AIMD",
        "status": "running",
        "message": "AIMD Forensic Engine is online"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }