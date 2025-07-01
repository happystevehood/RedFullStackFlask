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
    server.log.info("Worker forked (PID: %s). Configuring worker-specific logging.", worker.pid)

    # 1. Get all relevant loggers
    root_logger = logging.getLogger()
    gunicorn_error_logger = logging.getLogger('gunicorn.error')
    gunicorn_access_logger = logging.getLogger('gunicorn.access')
    flask_app_logger = logging.getLogger('app') # Corresponds to app = Flask(__name__) where __name__ is 'app'

    # 2. Clear any existing handlers inherited from the master process
    gunicorn_error_logger.handlers = []
    gunicorn_access_logger.handlers = []
    # Clear root handlers to ensure no duplicates from default setup
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 3. Create your shared, custom formatter
    formatter = rl_data.SafeFormatter( # Use the SafeFormatter class from rl_data
        '[%(asctime)s] [W:%(worker_id)s] [R:%(request_id)s] [PID:%(process)d] '
        '%(levelname)s in %(module)s: %(message)s'
    )

    # 4. Add your custom filter to the root logger
    # Any child logger (like 'app') will inherit this filter.
    root_logger.addFilter(rl_data.WorkerInfoFilter())
    
    # 5. Load log level configuration from your JSON file
    log_config = rl_data.load_log_config() # Assuming this function exists and works
    
    # --- Create and Add Handlers ---
    
    # Add a Console Handler (writes to stdout/stderr, visible in Cloud Run Logs)
    console_level = log_config.get('console', 'DEBUG').upper()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    
    # Add GCS or Local File Handler based on environment
    env_mode = os.environ.get('ENV_MODE', 'development')
    file_level = log_config.get('file', 'INFO').upper()
    active_file_handler = None
    
    if env_mode == 'deploy':
        if rl_data.storage and rl_data.BLOG_BUCKET_NAME:
            try:
                gcs_log_path_template = "logs/deploy/app_{date}_worker_{worker_id}.log"
                active_file_handler = rl_data.GCSLoggingHandler(
                    bucket_name=rl_data.BLOG_BUCKET_NAME,
                    gcs_log_path_template=gcs_log_path_template
                )
                active_file_handler.setLevel(file_level)
                active_file_handler.setFormatter(formatter)
                server.log.info(f"GCSLoggingHandler configured for worker {worker.pid}")
            except Exception as e:
                server.log.error(f"Failed to configure GCSLoggingHandler for worker {worker.pid}: {e}", exc_info=True)
        else:
            server.log.warning("GCS logging disabled: 'storage' module not loaded or BLOG_BUCKET_NAME not set.")
    else: # For 'development' or any other non-deploy mode
        if rl_data.portalocker:
            try:
                os.makedirs(os.path.dirname(rl_data.LOG_FILE), exist_ok=True)
                active_file_handler = rl_data.SafeRotatingFileHandler(
                    str(rl_data.LOG_FILE), maxBytes=5_000_000, backupCount=3, delay=True
                )
                active_file_handler.setLevel(file_level)
                active_file_handler.setFormatter(formatter)
                server.log.info(f"SafeRotatingFileHandler configured for worker {worker.pid}")
            except Exception as e:
                server.log.error(f"Failed to configure SafeRotatingFileHandler for worker {worker.pid}: {e}", exc_info=True)
        else:
            server.log.warning("portalocker not installed. Local file logging will not be process-safe.")

    # 6. Add the configured handlers to all loggers
    handlers_to_add = [console_handler]
    if active_file_handler:
        handlers_to_add.append(active_file_handler)

    for logger in [root_logger, gunicorn_error_logger, gunicorn_access_logger, flask_app_logger]:
        # logger.handlers = handlers_to_add # Replace handlers
        for h in handlers_to_add:
            logger.addHandler(h)
        
        logger.setLevel(log_config.get('global', 'DEBUG').upper())
        logger.propagate = False # IMPORTANT: Stop messages from being handled twice

    # --- Silence noisy libraries ---
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    server.log.info(f"Logging fully configured for worker {worker.pid}")
