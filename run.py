"""
run.py - Root Entrypoint for Utility Bot Enterprise Server.
Run directly from workspace root:
    python run.py
"""

import os
import sys
import socket
import subprocess
import time

# Ensure UTF-8 output encoding on all terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def free_port_if_busy(port: int) -> int:
    """Checks if port is in use. If so, frees it or finds next open port."""
    def is_port_in_use(p: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', p)) == 0

    if not is_port_in_use(port):
        return port

    print(f"\n[Notice] Port {port} is already in use by an existing process.")
    print("[Action] Attempting to free port automatically...")

    if sys.platform == "win32":
        try:
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            pids = set()
            for line in output.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid.isdigit() and int(pid) != os.getpid():
                        pids.add(int(pid))
            for pid in pids:
                try:
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            time.sleep(1)
        except Exception:
            pass

    if not is_port_in_use(port):
        print(f"[Success] Port {port} freed successfully.\n")
        return port

    # If still busy, find next available port
    for fallback in range(port + 1, port + 20):
        if not is_port_in_use(fallback):
            print(f"[Success] Switched to available port {fallback}.\n")
            return fallback

    return port


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

    requested_port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    port = free_port_if_busy(requested_port)

    print("\n" + "=" * 65)
    print("  UTILITY BOT - ENTERPRISE KYC & VERIFICATION SERVER")
    print("=" * 65)
    print(f"  * Web Dashboard & Unified App : http://localhost:{port}")
    print(f"  * Interactive Swagger API Docs : http://localhost:{port}/docs")
    print("=" * 65 + "\n")

    uvicorn.run(app, host=host, port=port)
