"""
main.py - Root ASGI Proxy for Utility Bot.
Allows running directly from workspace root with:
    python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import importlib.util
import os
import sys

# Ensure python_service is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.join(PROJECT_ROOT, "python_service")

if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

# Switch working directory to python_service
os.chdir(SERVICE_DIR)

# Load the actual service main without circular collision
target_main = os.path.join(SERVICE_DIR, "main.py")
spec = importlib.util.spec_from_file_location("service_main", target_main)
service_main = importlib.util.module_from_spec(spec)
sys.modules["service_main"] = service_main
spec.loader.exec_module(service_main)

# Expose app for Uvicorn ASGI server
app = service_main.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
