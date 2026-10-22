from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="SmartAttend", version="0.1.0")
app.include_router(auth.router)


@app.get("/health")
def health_check():
    """Simple endpoint to confirm the server is running."""
    return {"status": "ok", "app": "SmartAttend"}