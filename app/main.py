import threading

from drift_detector import DriftDetector
from fastapi import FastAPI


app = FastAPI(title="DriftBounty Lite")

detector = DriftDetector()


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=detector.run_forever, daemon=True)
    thread.start()


@app.get("/")
def root():
    return {
        "name": "DriftBounty Lite",
        "status": "running",
        "description": "Detects Kubernetes drift and creates GitHub issues.",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
