from fastapi import FastAPI
from backend.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)


@app.get("/")
def home():
    return {
        "message": "Project Altron",
        "version": settings.VERSION
    }