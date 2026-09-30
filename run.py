"""
run.py - Root Entrypoint for Utility Bot Enterprise Server.
Run directly from workspace root:
    python run.py
"""

import os
import sys

# Ensure python_service is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.join(PROJECT_ROOT, "python_service")

if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

# Switch working directory to python_service so model files and data are found
os.chdir(SERVICE_DIR)

if __name__ == "__main__":
    import uvicorn
    from main import app

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print("\n" + "=" * 65)
    print("  UTILITY BOT - ENTERPRISE KYC & VERIFICATION SERVER")
    print("=" * 65)
    print(f"  • Web Dashboard & Unified App : http://localhost:{port}")
    print(f"  • Interactive Swagger API Docs : http://localhost:{port}/docs")
    print("=" * 65 + "\n")

    uvicorn.run(app, host=host, port=port)
