from fastapi import FastAPI
from backend.config import settings
from backend.database import engine, Base
from backend.routers import interviews

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

app.include_router(interviews.router)

@app.get("/")
def home():
    return {
        "message": "Project Altron",
        "version": settings.VERSION
    }