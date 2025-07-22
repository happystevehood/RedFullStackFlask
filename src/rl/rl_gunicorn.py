import os
import sys
import logging
from pathlib import Path
# --- Add src to path to make imports reliable ---
project_src_dir = Path(__file__).resolve().parent.parent
if str(project_src_dir) not in sys.path:
    sys.path.insert(0, str(project_src_dir))
print(f"Added {project_src_dir} to sys.path")

import rl.rl_data as rl_data 

# --- Gunicorn Core Settings ---
# These are read by Gunicorn when it starts.
bind = "0.0.0.0:" + os.environ.get("PORT", "8080")
workers = int(os.environ.get("GUNICORN_WORKERS", 4))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "gthread"
timeout = 120
preload_app = False # Important for multi-worker logging setup

# Set Gunicorn's default log locations to stdout/stderr.
# We will intercept these loggers in the post_fork hook.
accesslog = '-'
errorlog = '-'
loglevel = 'INFO' # Gunicorn's own verbosity, your app can be more verbose (e.g., DEBUG)

# --- Gunicorn Server Hooks ---

def post_fork(server, worker):
    """
    Called after a worker process has been forked from the master.
    This is the perfect place to configure logging for each individual worker.
    """
    server.log.info("Worker forked (PID: %s). Delegating to centralized logger setup.", worker.pid)
    rl_data.setup_logger()
    server.log.info(f"Logging fully configured for worker {worker.pid} via centralized setup.")

