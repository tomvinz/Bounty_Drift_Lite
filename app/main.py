import threading
import traceback
import sys

from fastapi import FastAPI
from drift_detector import DriftDetector


app = FastAPI(title="DriftBounty Lite")


def run_detector():
    print("Starting DriftBounty detector thread...", flush=True)

    try:
        detector = DriftDetector()
        detector.run_forever()
    except Exception:
        print("Detector crashed:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()


@app.on_event("startup")
def startup_event():
    print("FastAPI startup event triggered", flush=True)
    thread = threading.Thread(target=run_detector, daemon=True)
    thread.start()