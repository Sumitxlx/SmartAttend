from fastapi import FastAPI

app = FastAPI(title="SmartAttend", version="0.1.0")


@app.get("/health")
def health_check():
    """Simple endpoint to confirm the server is running."""
    return {"status": "ok", "app": "SmartAttend"}