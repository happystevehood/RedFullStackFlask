import os, sys
from pathlib import Path
import logging
import uuid
import json
from logging.handlers import RotatingFileHandler
import threading
import portalocker  # Cross-platform file locking
from werkzeug.utils import secure_filename
from flask import render_template as flask_render_template

from google.cloud import storage
import csv
import io
import glob # For listing files
import math
from datetime import datetime, timedelta, timezone
import time
from PIL import Image # Import Pillow
from io import BytesIO
import numpy as np

# In your rl_data_gcs.py or rl_data.py

from google.auth import iam as google_auth_iam # Alias to avoid confusion with any 'iam' variable
import google.auth
import google.auth.transport.requests



# file sturcture 'constants'
# static - csv 	- input
#				- generic
#		 - pdf 	- generic
#				- comp
#		 - png	- generic
#				- comp

#APP_ROOT = Path(__file__).resolve().parent.parent # Goes up two levels if rl_data.py is in app/rl/
#APP_STATIC_FOLDER = APP_ROOT / 'static'

CSV_INPUT_DIR    = Path('static') / 'csv' / 'input'
CSV_GENERIC_DIR  = Path('static') / 'csv' / 'generic' 
PDF_COMP_DIR     = Path('static') / 'pdf' / 'comp' 
PDF_GENERIC_DIR  = Path('static') / 'pdf' / 'generic' 
PNG_COMP_DIR     = Path('static') / 'png' / 'comp'
PNG_GENERIC_DIR  = Path('static') / 'png' / 'generic' 
PNG_HTML_DIR     = Path('static') / 'png' / 'html' 

TEMPLATE_FOLDER = Path('templates')

# This data should not be served to the user
LOG_FILE_DIR      = Path('store') / 'logs'
LOG_FILE          = LOG_FILE_DIR / 'activity.log'
LOG_CONFIG_FILE   = LOG_FILE_DIR / 'log_config.json'

CSV_FEEDBACK_DIR  = Path('store') / 'feedback'
FEEDBACK_FILENAME  = 'feedback.csv'
CSV_FEEDBACK_FILEPATH = CSV_FEEDBACK_DIR / FEEDBACK_FILENAME

ENV_PROD_FILENAME = '.env.production'
ENV_PROD_FILE = Path('.') / ENV_PROD_FILENAME
ENV_DEVEL_FILENAME = '.env.development'
ENV_DEVEL_FILE = Path('.') / ENV_DEVEL_FILENAME

BLOG_DATA_DIR =  Path('blog_data')
LOCAL_BLOG_DATA_DIR = BLOG_DATA_DIR
BLOG_CONFIG_FILE = 'blog_config.json'
BLOG_CONFIG_FILE_PATH = BLOG_DATA_DIR / BLOG_CONFIG_FILE # Path to your config file

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGES_PER_POST = 7
THUMBNAIL_SIZE = (500, 500) # Max width, max height for thumbnails
THUMBNAIL_PREFIX = "thumb_" # Prepended to original filename for thumbnail

BASE_URL = "https://redline-results-951032250531.asia-southeast1.run.app"
ROBOTS_DIR       = Path('static') 

BUCKET_NAME = 'redline-fitness-results-feedback'
BLOG_BUCKET_NAME = BUCKET_NAME
BLOG_BLOB_DIR = BLOG_DATA_DIR

FEEDBACK_BUCKET_NAME = BUCKET_NAME
FEEDBACK_BLOB_DIR = Path('feedback')
FEEDBACK_BLOB_FILEPATH = FEEDBACK_BLOB_DIR / FEEDBACK_FILENAME

SERVICE_ACCOUNT_EMAIL = "default@email.com"

TIME_SIMILARITY_PERCENTAGE = 0.05  # e.g., +/- 5% of competitor's net time

#Here are the different logging levels 
# DEBUG 
# INFO 
# WARNING 
# ERROR 


# DEBUG      logger.debug("This is a debug message")    # Typically used for detailed dev info
# INFO       logger.info("This is an info message")     # General application info
# WARNING    logger.warning("This is a warning")        # Something unexpected, but not fatal
# ERROR      logger.error("This is an error message")   # Serious problem, app still running
# CRITICAL    logger.critical("This is critical") 


DEFAULT_LOG_LEVEL = logging.DEBUG #INFO # Anything LOWER than this will be filtered out.
DEFAULT_LOG_FILE_LEVEL = logging.DEBUG #INFO # This level or higher will be written to the log file
DEFAULT_LOG_CONSOLE_LEVEL = logging.DEBUG #ERROR # This level or higher will be written to the console/terminal

#The 2023 Events Lists
STATIONLIST23 =      [         'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']
STATIONLISTSTART23 = ['Start', 'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']

#The 2024 Events Lists
STATIONLIST24 =      [         'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']
STATIONLISTSTART24 = ['Start', 'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']

#The 2025 Events Lists
STATIONLIST25 =      [         'RUN', 'SKI', 'DEADBALL BURPEES', 'BIKE', 'FARMER\'S CARRY', 'SHUTTLE RUNS', 'RUSSIAN TWISTS', 'SANDBAG GAUNTLET', 'ROW', 'SQUAT THRUSTS', 'THE MULE', 'SLED PUSH & PULL']
STATIONLISTSTART25 = ['Start', 'RUN', 'SKI', 'DEADBALL BURPEES', 'BIKE', 'FARMER\'S CARRY', 'SHUTTLE RUNS', 'RUSSIAN TWISTS', 'SANDBAG GAUNTLET', 'ROW', 'SQUAT THRUSTS', 'THE MULE', 'SLED PUSH & PULL']


# Your data for filtering purposes
EVENT_DATA_LIST = [
    #2025
    #["WomensSinglesInterKL2025", "REDLINE Fitness Games '25 KL Womens Singles Inter.", "2025", "WOMENS", "SINGLES_INTERMEDIATE", "KL", "YES_CAT"],
    #["WomensSinglesAdvKL2025", "REDLINE Fitness Games '25 KL Womens Singles Adv.", "2025", "WOMENS", "SINGLES_ADVANCED", "KL", "YES_CAT"],
    #["MensSinglesAdvKL2025", "REDLINE Fitness Games '25 KL Mens Singles Adv.", "2025", "MENS", "SINGLES_ADVANCED", "KL", "YES_CAT"],
    #["MixedDoublesKL2025", "REDLINE Fitness Games '25 KL Mixed Doubles", "2025", "MIXED", "DOUBLES", "KL", "NO_CAT"],
    #["MensDoublesKL2025", "REDLINE Fitness Games '25 KL Mens Doubles", "2025", "MENS", "DOUBLES", "KL", "NO_CAT"],
    #["WomensBeginnersKL2025", "REDLINE Fitness Games '25 KL Singles Beginners", "2025", "MIXED", "SINGLES_BEGINNERS", "KL", "NO_CAT"],
    #["MensBeginnersKL2025", "REDLINE Fitness Games '25 KL Singles Beginners", "2025", "MIXED", "SINGLES_BEGINNERS", "KL", "NO_CAT"],
    #["MensSinglesInterKL2025", "REDLINE Fitness Games '25 KL Mens Singles Inter.", "2025", "MENS", "SINGLES_INTERMEDIATE", "KL", "YES_CAT"],
    #["WomensDoublesKL2025", "REDLINE Fitness Games '25 KL Womens Doubles", "2025", "WOMENS", "DOUBLES", "KL", "NO_CAT"],
    #["TeamRelayWomenKL2025", "REDLINE Fitness Games '25 KL Womens Team Relay", "2025", "WOMENS", "RELAY", "KL", "NO_CAT"],
    #["TeamRelayMenKL2025", "REDLINE Fitness Games '25 KL Mens Team Relay", "2025", "MENS", "RELAY", "KL", "NO_CAT"],
    #["TeamRelayMixedKL2025", "REDLINE Fitness Games '25 KL Mixed Team Relay", "2025", "MIXED", "RELAY", "KL", "NO_CAT"],
    #2024
    ["WomensSinglesCompetitive2024", "REDLINE Fitness Games '24 Womens Singles Comp.", "2024", "WOMENS", "SINGLES_COMPETITIVE", "KL", "YES_CAT"],
    ["MensSinglesCompetitive2024", "REDLINE Fitness Games '24 Mens Singles Comp.", "2024", "MENS", "SINGLES_COMPETITIVE", "KL", "YES_CAT"],
    ["WomensSinglesOpen2024", "REDLINE Fitness Games '24 Womens Singles Open", "2024", "WOMENS", "SINGLES_OPEN", "KL", "NO_CAT"],
    ["MensSinglesOpen2024", "REDLINE Fitness Games '24 Mens Singles Open", "2024", "MENS", "SINGLES_OPEN", "KL", "NO_CAT"],
    ["WomensDoubles2024", "REDLINE Fitness Games '24 Womens Doubles", "2024", "WOMENS", "DOUBLES", "KL", "YES_CAT"],
    ["MensDoubles2024", "REDLINE Fitness Games '24 Mens Doubles", "2024", "MENS", "DOUBLES", "KL", "YES_CAT"],
    ["MixedDoubles2024", "REDLINE Fitness Games '24 Mixed Doubles", "2024", "MIXED", "DOUBLES", "KL", "YES_CAT"],
    ["TeamRelayWomen2024", "REDLINE Fitness Games '24 Womens Team Relay", "2024", "WOMENS", "RELAY", "KL", "YES_CAT"],
    ["TeamRelayMen2024", "REDLINE Fitness Games '24 Mens Team Relay", "2024", "MENS", "RELAY", "KL", "YES_CAT"],
    ["TeamRelayMixed2024", "REDLINE Fitness Games '24 Mixed Team Relay", "2024", "MIXED", "RELAY", "KL", "YES_CAT"],
    #2023
    ["WomensSinglesCompetitive2023", "REDLINE Fitness Games '23 Womens Singles Comp.", "2023", "WOMENS", "SINGLES_COMPETITIVE", "KL", "YES_CAT"],
    ["MensSinglesCompetitive2023", "REDLINE Fitness Games '23 Mens Singles Comp.", "2023", "MENS", "SINGLES_COMPETITIVE", "KL", "YES_CAT"],
    ["WomensSinglesOpen2023", "REDLINE Fitness Games '23 Womens Singles Open", "2023", "WOMENS", "SINGLES_OPEN", "KL", "NO_CAT"],
    ["MensSinglesOpen2023", "REDLINE Fitness Games '23 Mens Singles Open", "2023", "MENS", "SINGLES_OPEN", "KL", "NO_CAT"],
    ["WomensDoubles2023", "REDLINE Fitness Games '23 Womens Doubles", "2023", "WOMENS", "DOUBLES", "KL", "NO_CAT"],
    ["MensDoubles2023", "REDLINE Fitness Games '23 Mens Doubles", "2023", "MENS", "DOUBLES", "KL", "NO_CAT"],
    ["MixedDoubles2023", "REDLINE Fitness Games '23 Mixed Doubles", "2023", "MIXED", "DOUBLES", "KL", "NO_CAT"],
    ["TeamRelayWomen2023", "REDLINE Fitness Games '23 Womens Team Relay", "2023", "WOMENS", "RELAY", "KL", "NO_CAT"],
    ["TeamRelayMen2023", "REDLINE Fitness Games '23 Mens Team Relay", "2023", "MENS", "RELAY", "KL", "NO_CAT"],
    ["TeamRelayMixed2023", "REDLINE Fitness Games '23 Mixed Team Relay", "2023", "MIXED", "RELAY", "KL", "NO_CAT"],
]

# Generate a unique worker ID that persists for this worker process
WORKER_ID = str(uuid.uuid4())[:8]

# Create a thread-local storage for request context information
thread_local = threading.local()

# --- Custom Filter and Formatter ---
class WorkerInfoFilter(logging.Filter):
    """Filter that adds worker ID and request info to log records during requests."""
    def filter(self, record):
        record.worker_id = WORKER_ID
        record.request_id = getattr(thread_local, 'request_id', '-')
        return True

class SafeFormatter(logging.Formatter):
    """
    A robust Formatter that handles missing keys in the log record gracefully
    by providing default values and manually constructing the final log string.
    This avoids KeyErrors during application startup with Flask/Werkzeug reloader.
    """
    def format(self, record):
        # 1. Manually add standard attributes that might be missing on some records
        record.asctime = self.formatTime(record, self.datefmt)
        
        # 2. Add our custom attributes with defaults if they don't exist
        record.worker_id = getattr(record, 'worker_id', WORKER_ID)
        record.request_id = getattr(record, 'request_id', '-')
        
        # 3. Handle the main message formatting
        # This step is crucial and was part of the problem before.
        # The record.message attribute is not created until format() is called.
        record.message = record.getMessage()

        # 4. Handle potential exception formatting
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.stack_info:
            if not record.stack_text:
                record.stack_text = self.formatStack(record.stack_info)
        
        # 5. Get the format string and format it.
        # Now, all keys in the format string (asctime, worker_id, etc.) are guaranteed
        # to be attributes on the record object.
        s = self.formatMessage(record)
        
        # Append exception text if it exists
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.stack_text
        return s

# --- Custom Handlers ---
class SafeRotatingFileHandler(RotatingFileHandler):
    """
    A RotatingFileHandler that is more robust for multi-process environments,
    especially on Windows, by explicitly closing the stream before rotation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if portalocker is None:
            raise ImportError("portalocker library is required for SafeRotatingFileHandler.")
        self.lock_file = f"{kwargs.get('filename', args[0])}.lock"
    
    def doRollover(self):
        """
        Rotates logs safely. Explicitly closes the stream before renaming
        to release the file handle, which is critical on Windows.
        """
        # Ensure we have the lock before touching any files
        lock_path = str(self.lock_file)
        try:
            with portalocker.Lock(lock_path, 'w', timeout=10):
                # --- This is the key change ---
                if self.stream: # Check if stream is open
                    self.stream.close()
                    self.stream = None # Set to None so it will be reopened on next emit
                
                # Now that our own handle is closed, the parent's rollover has a better chance
                super().doRollover()
                
        except Exception as e:
            # If locking or rollover fails, log the error but don't crash
            print(f"Error during doRollover: {e}", file=sys.stderr)
            # We don't call super().doRollover() again here as it would be redundant and likely fail again
    
    def emit(self, record):
        """Thread and process-safe emit with file locking."""
        try:
            lock_path = str(self.lock_file)
            with portalocker.Lock(lock_path, 'w', timeout=5):
                # The standard handler's emit will call _open() if self.stream is None
                super().emit(record)
        except Exception:
            try:
                super().emit(record)
            except Exception as e2:
                print(f"Error emitting log record: {e2}", file=sys.stderr)


# --- GCS Logging Handler ---
# In rl_data.py or your chosen logging utility file

import logging
import threading
import time
import sys
from datetime import datetime

try:
    from google.cloud import storage
except ImportError:
    storage = None

# This should be defined at the module level
WORKER_ID = str(uuid.uuid4())[:8] # Assuming uuid is imported

class GCSLoggingHandler(logging.Handler):
    """
    A Python logging handler that uploads log records to a unique file per worker
    in Google Cloud Storage. It uses GCS's 'compose' API for efficient and
    atomic appends, making it safe for multi-process environments like Gunicorn.
    """
    def __init__(self, bucket_name, gcs_log_path_template, buffer_capacity=100, upload_interval=30):
        """
        Initializes the GCS logging handler.

        Args:
            bucket_name (str): The name of the GCS bucket.
            gcs_log_path_template (str): A template for the log file path, which should include
                                       placeholders for {date} and {worker_id}.
                                       Example: "logs/deploy/app_{date}_worker_{worker_id}.log"
            buffer_capacity (int): Max number of log records to buffer before forcing an upload.
            upload_interval (int): Max number of seconds to wait before forcing an upload.
        """
        super().__init__()
        
        # Initialize all instance attributes to a safe default state first.
        self.storage_client = None
        self.bucket = None
        self._is_initialized = False # Flag to track if GCS connection was successful
        self.buffer = []
        self.lock = threading.RLock() # Thread-safe lock for buffer operations
        self.uploader_thread = None
        self.upload_interval = upload_interval
        self.last_upload_time = time.time()
        self.buffer_capacity = buffer_capacity
        
        if storage is None:
            print("CRITICAL: google-cloud-storage library not imported. GCSLoggingHandler is disabled.", file=sys.stderr)
            return

        if not bucket_name:
            print("CRITICAL: GCS bucket_name not provided. GCSLoggingHandler is disabled.", file=sys.stderr)
            return

        try:
            # The log path is unique per worker and per day.
            log_date = datetime.utcnow().strftime('%Y-%m-%d')
            self.gcs_log_path = gcs_log_path_template.format(date=log_date, worker_id=WORKER_ID)

            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(bucket_name)
            
            # Start a background thread for periodic uploads if interval is positive
            if self.upload_interval > 0:
                self.uploader_thread = threading.Thread(target=self._periodic_uploader, daemon=True)
                self.uploader_thread.start()
            
            self._is_initialized = True
            # This print goes to stderr, which is visible in Cloud Run logs
            print(f"GCSLoggingHandler initialized for worker {WORKER_ID}, writing to: gs://{bucket_name}/{self.gcs_log_path}", file=sys.stderr)

        except Exception as e:
            print(f"FATAL: Could not initialize GCSLoggingHandler. Error: {e}", file=sys.stderr)
            # self.bucket remains None, and self._is_initialized remains False, effectively disabling the handler.

    def emit(self, record):
        """
        Formats the record and adds it to the buffer. Triggers a flush if the
        buffer exceeds capacity.
        """
        if not self._is_initialized:
            return
        
        log_entry = self.format(record) + "\n"
        
        with self.lock:
            self.buffer.append(log_entry)
            should_flush = len(self.buffer) >= self.buffer_capacity
        
        if should_flush:
            self.flush()

    def flush(self):
        """
        Uploads buffered logs to GCS using the 'compose' method for atomic appends.
        This method is thread-safe.
        """
        if not self._is_initialized or not self.buffer:
            return
        
        with self.lock:
            if not self.buffer:
                return
            # Join all buffered records into a single string and clear the buffer
            records_to_upload_str = "".join(self.buffer)
            self.buffer = []

        # Perform GCS operations outside the lock to avoid holding it during network I/O
        try:
            # A unique name for the temporary object for this specific flush operation
            temp_blob_name = f"{self.gcs_log_path}.{time.time_ns()}.tmp"
            
            main_blob = self.bucket.blob(self.gcs_log_path)
            temp_blob = self.bucket.blob(temp_blob_name)

            # 1. Upload the new content to a temporary blob.
            temp_blob.upload_from_string(records_to_upload_str, content_type='text/plain')

            # 2. Check if the main log file exists. Use reload() for strong consistency.
            try:
                main_blob.reload()
                main_blob_exists = True
            except Exception: # Catches google.api_core.exceptions.NotFound
                main_blob_exists = False

            if main_blob_exists:
                # 3. Atomically compose the main file and the temporary file.
                main_blob.compose([main_blob, temp_blob])
                # Delete the temporary blob. It's good practice to wrap in another try/except.
                try:
                    temp_blob.delete()
                except Exception as e_del:
                    print(f"Warning: Failed to delete temporary log blob {temp_blob_name}: {e_del}", file=sys.stderr)
            else:
                # 4. If the main file doesn't exist, rename the temporary blob to become the main file.
                self.bucket.rename_blob(temp_blob, new_name=self.gcs_log_path)
            
            self.last_upload_time = time.time()
        except Exception as e:
            print(f"CRITICAL ERROR during GCS flush: {e}", file=sys.stderr)
            # Optional: Add records back to the buffer for a retry attempt.
            # Be cautious as this can lead to memory issues if the GCS issue is persistent.
            with self.lock:
                self.buffer.insert(0, records_to_upload_str)

    def _periodic_uploader(self):
        """A background daemon thread that periodically flushes the log buffer."""
        while True:
            time.sleep(self.upload_interval)
            # No need to check time here, just check if there's content in buffer
            if self.buffer:
                self.flush()

    def close(self):
        """
        Ensures any remaining logs in the buffer are flushed before closing.
        """
        # Stop the uploader thread if it exists
        if self.uploader_thread and self.uploader_thread.is_alive():
            # In a real daemon, you would use an event to signal it to stop.
            # For simplicity here, we just flush.
            pass
            
        if self._is_initialized:
            self.flush()
        super().close()
        
def load_log_config():
    """Load logging configuration from file, or create with defaults if doesn't exist"""
    os.makedirs(LOG_FILE_DIR, exist_ok=True)
    
    try:
        with open(LOG_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default config
        config = {
            'global': logging.getLevelName(DEFAULT_LOG_LEVEL),
            'file': logging.getLevelName(DEFAULT_LOG_FILE_LEVEL),
            'console': logging.getLevelName(DEFAULT_LOG_CONSOLE_LEVEL)
        }
        save_log_config(config)
        return config

def save_log_config(config):
    """Save logging configuration to file with cross-platform locking"""
    os.makedirs(LOG_FILE_DIR, exist_ok=True)
    
    lock_path = str(LOG_CONFIG_FILE) + ".lock"
    try:
        # Use portalocker with a file path directly
        with portalocker.Lock(lock_path, 'w', timeout=10):
            with open(LOG_CONFIG_FILE, 'w') as f:
                json.dump(config, f)
    except (portalocker.LockException, IOError, OSError) as e:
        # If locking fails, try without lock
        print(f"Warning: Lock failed during config save: {e}")
        with open(LOG_CONFIG_FILE, 'w') as f:
            json.dump(config, f)

# --- Main Setup and Control Functions ---
# 
# rl/rl_data.py

# ... (keep other functions as they are)

def setup_logger():
    """
    Setup logging. For local dev with the reloader, ONLY log to console to avoid
    file lock issues. For Docker/deploy, add the appropriate file/GCS handler.
    This function is idempotent.
    """
    logger = logging.getLogger() # Get the root logger
    
    if getattr(logger, '_is_rl_configured', False):
        return logger

    # Clear any pre-existing handlers
    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    config = load_log_config()
    global_level = getattr(logging, config.get('global', 'DEBUG'), logging.DEBUG)
    logger.setLevel(global_level)
    
    formatter = SafeFormatter(
        '[%(asctime)s] [W:%(worker_id)s] [R:%(request_id)s] [PID:%(process)d] '
        '%(levelname)s in %(module)s: %(message)s'
    )
    
    logger.addFilter(WorkerInfoFilter())
    
    # --- Always Add Console Handler ---
    console_level = getattr(logging, config.get('console', 'DEBUG'), logging.DEBUG)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
        
    # --- Conditionally Add File/GCS Handler ---
    env_mode = os.environ.get('ENV_MODE', 'development')
    
    # **CRITICAL FIX**: Check if the Flask reloader is active.
    # The 'WERKZEUG_RUN_MAIN' env var is set to 'true' in the reloaded child process.
    is_reloader_active = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

    if env_mode == 'deploy':
        # --- GCS Handler for Deployment ---
        if storage and BLOG_BUCKET_NAME:
            try:
                gcs_log_path_template = "logs/deploy/app_{date}_worker_{worker_id}.log"
                gcs_handler = GCSLoggingHandler(
                    bucket_name=BLOG_BUCKET_NAME,
                    gcs_log_path_template=gcs_log_path_template,
                )
                gcs_handler.setLevel(getattr(logging, config.get('file', 'INFO'), logging.INFO))
                gcs_handler.setFormatter(formatter)
                logger.addHandler(gcs_handler)
            except Exception as e:
                print(f"CRITICAL: Failed to set up GCSLoggingHandler: {e}", file=sys.stderr)
    elif not is_reloader_active:
        # --- Local File Handler for Docker or when reloader is OFF ---
        if portalocker:
            try:
                os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
                file_handler = SafeRotatingFileHandler(
                    str(LOG_FILE), maxBytes=5_000_000, backupCount=3, delay=True
                )
                file_handler.setLevel(getattr(logging, config.get('file', 'INFO'), logging.INFO))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"FATAL ERROR: Failed to setup local log file handler: {e}", file=sys.stderr)
        else:
            print("WARNING: portalocker not installed. Local file logging is disabled.", file=sys.stderr)
    else:
        # --- Reloader is ON, so we do NOT add a file handler ---
        logger.error("Flask reloader is active. Skipping file logging to prevent file lock errors.")


    # Silence Noisy Libraries
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    logger._is_rl_configured = True
    
    logger.info(f"Logger successfully initialized for worker {WORKER_ID} in '{env_mode}' mode.")
    return logger

def clear_or_rotate_logs():
    """
    Clears logs based on the current environment.
    - 'deploy' mode: Deletes today's GCS log object and triggers its immediate recreation.
    - Other modes: Rotates local files and deletes all old backups.
    
    Returns:
        tuple: A (message, category) tuple for Flask's flash function.
    """
    logger = get_logger() # Assuming get_logger() is defined in the same module
    env_mode = os.environ.get('ENV_MODE', 'development')
    
    if env_mode == 'deploy':
        logger.info(f"Performing GCS log deletion for deploy mode.")
        if not storage or not BLOG_BUCKET_NAME:
            return "GCS logging not configured, cannot clear.", "warning"
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BLOG_BUCKET_NAME)
            # Find ALL log files for today to delete them
            #log_date = datetime.utcnow().strftime('%Y-%m-%d')
            #prefix_to_delete = f"logs/deploy/app_{log_date}_worker_"
            prefix_to_delete = f"logs/deploy/app_"
            
            blobs_to_delete = bucket.list_blobs(prefix=prefix_to_delete)
            
            deleted_count = 0
            for blob in blobs_to_delete:
                blob.delete()
                deleted_count += 1
                logger.info(f"Deleted GCS log object: {blob.name}")
            
            if deleted_count > 0:
                return f"Deleted {deleted_count} GCS log file(s) for today.", "success"
            else:
                return "No GCS log files found for today to delete.", "info"
        except Exception as e:
            return f"Error deleting GCS logs: {e}", "danger"
            
    else:
        # --- Local File Rotation and Cleanup Logic ---
        logger.info("Performing local log rotation and cleanup.")
        root_logger = logging.getLogger()
        handler_actioned = False

        for handler in root_logger.handlers:
            if isinstance(handler, SafeRotatingFileHandler):
                base_filename = handler.baseFilename
                try:
                    # doRollover renames current file (e.g., app.log -> app.log.1)
                    # and makes the handler point to a new empty app.log
                    handler.doRollover()
                    handler_actioned = True
                    logger.info(f"Log file {base_filename} rotated successfully.")
                    
                    # Optional: Aggressively delete ALL numbered backup files
                    backup_file_pattern = f"{base_filename}.*" 
                    backup_files_found = glob.glob(backup_file_pattern)
                    
                    if backup_files_found:
                        logger.info(f"Deleting old log backups: {backup_files_found}")
                        for f in backup_files_found:
                            try:
                                os.remove(f)
                            except OSError as e:
                                logger.error(f"Error deleting old log file {f}: {e}")
                    
                    return "Local logs rotated and all backups cleared.", "success"
                except Exception as e:
                    logger.error(f"Error during manual log rotation/cleanup: {e}", exc_info=True)
                    return f"Error rotating logs: {e}", "danger"

        if not handler_actioned:
            handler_types = [type(h).__name__ for h in root_logger.handlers]
            logger.error(f"No suitable SafeRotatingFileHandler found for local rotation. Active handlers: {handler_types}")
            return "No rotating file handler found to clear/rotate.", "warning"


# rl/rl_data.py

# ... (keep other functions as they are)

def delete_log_file(filename_to_delete):
    """
    Deletes a single, specific log file.
    - 'deploy' mode: Deletes a specific GCS blob.
    - Local mode: Deletes backup files. For the active log file, it will likely
      fail due to the Flask reloader's file lock, which is handled gracefully.
    
    Args:
        filename_to_delete (str): The name of the file to delete.

    Returns:
        tuple: A (success_boolean, message_string) tuple for the flash message.
    """
    logger = get_logger()
    env_mode = os.environ.get('ENV_MODE', 'development')
    
    if env_mode == 'deploy':
        # --- GCS Logic (unchanged) ---
        # ... (This part is correct and remains the same)
        logger.info(f"Attempting to delete GCS log blob: {filename_to_delete}")
        if not storage or not BLOG_BUCKET_NAME:
            return False, "GCS logging not configured, cannot delete."
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BLOG_BUCKET_NAME)
            blob = bucket.blob(filename_to_delete)
            
            if blob.exists():
                blob.delete()
                logger.info(f"DELETED GCS log object: {blob.name}")
                return True, f"Successfully deleted GCS log file: {filename_to_delete}"
            else:
                logger.error(f"GCS log file not found for deletion: {filename_to_delete}")
                return False, f"GCS log file not found: {filename_to_delete}"
        except Exception as e:
            logger.critical(f"Error deleting GCS log file {filename_to_delete}: {e}", exc_info=True)
            return False, f"Error deleting GCS log file: {e}"
            
    else:
        # --- FINAL Local File Deletion Logic ---
        logger.info(f"Processing delete request for local log file: {filename_to_delete}")
        try:
            local_filepath = Path(LOG_FILE_DIR) / Path(filename_to_delete)
            
            if not local_filepath.exists() or not local_filepath.is_file():
                logger.error(f"Local log file not found for deletion: {local_filepath}")
                return False, f"Local log file not found: {filename_to_delete}"

            # We can now simply try to remove the file.
            os.remove(local_filepath)
            logger.info(f"DELETED local backup log file: {local_filepath}")
            return True, f"Successfully deleted local backup log file: {filename_to_delete}"
        
        except PermissionError:
            logger.error(f"PermissionError deleting '{filename_to_delete}'. This is expected for the active log file when using the Flask reloader on Windows.")
            return False, f"Could not delete '{filename_to_delete}'. It is likely locked by the development server. Try deleting backup logs (.log.1, .log.2) instead, or restart the server."
            
        except Exception as e:
            logger.critical(f"Error processing delete for {filename_to_delete}: {e}", exc_info=True)
            return False, f"Error processing log file: {e}"
        
        
def get_logger(name=None):
    """
    Get a logger instance. Ensures setup_logger() has been called at least once
    in the application's lifecycle.
    """
    # This function is mostly a convenience wrapper around logging.getLogger
    # setup_logger should be called once when the application starts up.
    # The filter logic can be simplified if setup_logger handles it definitively.
    if name:
        return logging.getLogger(name)
    else:
        return logging.getLogger() # Get the root logger

def update_log_level(global_level=None, handler_levels=None):
    """
    Update log levels for active handlers and save the new configuration.
    This function will affect the current worker process immediately and
    save the config for future worker processes.
    """
    logger = get_logger()
    config = load_log_config() # Load current config to update it
    
    # Update global log level
    if global_level:
        level = getattr(logging, str(global_level).upper(), None)
        if isinstance(level, int):
            logger.setLevel(level)
            config['global'] = str(global_level).upper()
            logger.info(f"Global log level set to {str(global_level).upper()}")
    
    # Update individual handler levels if a dictionary is provided
    if handler_levels and isinstance(handler_levels, dict):
        for handler in logger.handlers:
            # For the local file handler
            if isinstance(handler, SafeRotatingFileHandler) and 'file' in handler_levels:
                level_str = str(handler_levels['file']).upper()
                level = getattr(logging, level_str, None)
                if isinstance(level, int):
                    handler.setLevel(level)
                    config['file'] = level_str # Update config for persistence
                    logger.info(f"SafeRotatingFileHandler level set to {level_str}")

            # For the GCS handler (also controlled by the 'file' setting from the form)
            elif isinstance(handler, GCSLoggingHandler) and 'file' in handler_levels:
                level_str = str(handler_levels['file']).upper()
                level = getattr(logging, level_str, None)
                if isinstance(level, int):
                    handler.setLevel(level)
                    # The config still uses the 'file' key for the cloud handler's level
                    # This keeps the UI simple with one "File/Cloud Log Level" setting
                    config['file'] = level_str 
                    logger.info(f"GCSLoggingHandler level set to {level_str}")

            # For the console handler
            elif isinstance(handler, logging.StreamHandler) and 'console' in handler_levels:
                level_str = str(handler_levels['console']).upper()
                level = getattr(logging, level_str, None)
                if isinstance(level, int):
                    handler.setLevel(level)
                    config['console'] = level_str
                    logger.info(f"Console StreamHandler level set to {level_str}")
    
    # Save the updated configuration for persistence
    save_log_config(config)
    
    logger.debug("Log levels updated and configuration file saved.")
    return get_log_levels() # Return the new state

def get_log_levels():
    """
    Get current log levels from the active logger and its handlers.
    Now includes a specific check for GCS handler level.
    """
    logger = get_logger()
    
    levels = {
        'global': logging.getLevelName(logger.level),
        'file': None,      # For local SafeRotatingFileHandler
        'gcs': None,       # For GCSLoggingHandler
        'console': None    # For console StreamHandler
    }
    
    found_file = False
    found_gcs = False
    found_console = False

    for handler in logger.handlers:
        if isinstance(handler, SafeRotatingFileHandler) and not found_file:
            levels['file'] = logging.getLevelName(handler.level)
            found_file = True
        elif isinstance(handler, GCSLoggingHandler) and not found_gcs:
            levels['gcs'] = logging.getLevelName(handler.level)
            found_gcs = True
        elif isinstance(handler, logging.StreamHandler) and not hasattr(handler, '_is_gcs_stream') and not found_console:
            # Check for a property to distinguish it from potential internal stream handlers of other libs
            levels['console'] = logging.getLevelName(handler.level)
            found_console = True
    
    # For display purposes in the admin panel, we can consolidate 'file' and 'gcs'
    # since they are controlled by the same config setting ('file').
    # We can create a new key for the template to use.
    levels['file_or_gcs'] = levels['gcs'] if levels['gcs'] is not None else levels['file']

    return levels

        

#############################
# Non log based helper functions
#############################

def save_feedback_to_gcs(name, email, comments, category, rating):
    # Set up Google Cloud Storage client
    bucket = get_gcs_bucket(FEEDBACK_BUCKET_NAME)

    # Define the GCS object path
    blob = bucket.blob(str(FEEDBACK_BLOB_FILEPATH))
    
    # Prepare the new row (UTC Time.)
    new_row = [datetime.now().isoformat(), name, email, comments, category, rating]
    
    logger = get_logger()
    #logger.debug(f"save_feedback_to_gcs> {', '.join(str(item) for item in new_row)} !")
    
    # We'll handle the data differently based on whether the file exists
    if blob.exists():
        # Download existing content
        existing_content = blob.download_as_string().decode('utf-8')
        
        # Read existing content into a list of rows
        reader = csv.reader(io.StringIO(existing_content))
        rows = list(reader)
        
        # Append our new row
        rows.append(new_row)
        
        # Write all rows back to a new buffer
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        writer.writerows(rows)
        
        # Upload the complete content
        blob.upload_from_string(output_buffer.getvalue(), content_type='text/csv')
    else:
        # If file doesn't exist, create a new one with just our row
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        writer.writerow(new_row)
        
        # Upload the new content
        blob.upload_from_string(output_buffer.getvalue(), content_type='text/csv')

def get_paginated_feedback(page=1, per_page=10):
    # Set up Google Cloud Storage client
    storage_client = storage.Client()
    bucket = storage_client.bucket(FEEDBACK_BUCKET_NAME)
    
    # Define the GCS object path
    blob = bucket.blob(str(FEEDBACK_BLOB_FILEPATH))
    
    feedback_list = []
    
    # Check if file exists in the bucket
    if blob.exists():
        # Download content from GCS
        content = blob.download_as_string().decode('utf-8')
        
        # Parse CSV content
        csv_buffer = io.StringIO(content)
        reader = csv.reader(csv_buffer)
        feedback_list = list(reader)
    
    # Handle pagination
    total = len(feedback_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_feedback = feedback_list[start:end]
    total_pages = math.ceil(total / per_page)
    
    return paginated_feedback, total_pages

def remove_files_from_directory(directory):
    """Removes all files within the specified directory, but leaves the directory untouched."""

    logger = get_logger()
    
    #logger.debug("remove_files_from_directory> %s",str(directory))
    logger.debug("cwd %s",str(os.getcwd()))
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    #logger.debug("remove_files_from_directory<")


def delete_generated_files():
    """Removes all data files generated here included competitor files"""

    logger = get_logger()
    #logger.debug("delete_generated_files>")
    
    remove_files_from_directory(CSV_GENERIC_DIR);
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PDF_GENERIC_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 
    remove_files_from_directory(PNG_GENERIC_DIR);
    
    #logger.debug("delete_generated_files<")

def delete_competitor_files():
    
    logger = get_logger()
    #logger.debug("delete_competitor_files>")
    
    """Removes all competitor data files generated here"""
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PNG_COMP_DIR);
    
    #logger.debug("delete_competitor_files<") 

def handle_rm_error(function, path, excinfo):
    import stat
    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        function(path)
    else:
        raise excinfo
    

#############################
# Helper function to convert seconds to minutes.
#############################

# Helper function to format seconds to mm:ss
def format_time_mm_ss(seconds_total, pos=None): # pos is required by FuncFormatter
    if np.isnan(seconds_total):
        return "N/A"
    seconds_total = int(round(seconds_total)) # Round to nearest second
    minutes = seconds_total // 60
    seconds = seconds_total % 60
    return f"{minutes:02d}:{seconds:02d}"


def convert_to_standard_time(time_str):
    """
    Convert a time string to the standard format "%H:%M:%S.%f" with one decimal place
    
    Parameters:
    -----------
    time_str : str or nan
        Time string in various formats like "%M:%S.%f", "%H:%M:%S", or nan
        
    Returns:
    --------
    str
        Time string in the format "%H:%M:%S.%f" with exactly one decimal place
        Returns "00:00:00.0" if the input is nan or invalid
    """
    # Handle nan or None
    if time_str is None or str(time_str).lower() == 'nan':
        return "" #float("nan")
    
    # Convert to string if not already
    time_str = str(time_str).strip()
    
    # If empty string
    if not time_str:
        return ""
    
    try:
        parts = time_str.split(':')
        
        # Handle %M:%S.%f format (two parts with colon)
        if len(parts) == 2:
            minutes = int(parts[0])
            
            # Check if seconds part has a decimal point
            if '.' in parts[1]:
                seconds_parts = parts[1].split('.')
                seconds = int(seconds_parts[0])
                decimal = float(f"0.{seconds_parts[1]}")
            else:
                seconds = int(parts[1])
                decimal = 0.0
                
            # Calculate hours from minutes if needed
            hours = minutes // 60
            minutes = minutes % 60
            
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{int(decimal * 10):1d}"
        
        # Handle %H:%M:%S format (three parts with colons)
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            
            # Check if seconds part has a decimal point
            if '.' in parts[2]:
                seconds_parts = parts[2].split('.')
                seconds = int(seconds_parts[0])
                decimal = float(f"0.{seconds_parts[1]}")
            else:
                seconds = int(parts[2])
                decimal = 0.0
                
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{int(decimal * 10):1d}"
        
        else:
            # Invalid format
            return ""
            
    except (ValueError, IndexError):
        # Return default for any parsing errors
        return ""


# --- BLOG Helper Functions ---
def load_global_blog_config():
    """
    Loads the global blog configuration.
    Reads from GCS if ENV_MODE is 'deploy', otherwise from local file.
    Returns default config if not found or error.
    """
    logger = get_logger()
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    default_config = {"max_featured_posts_on_home": 6} # Example defaults

    if env_mode == 'deploy':
        #logger.debug(f"Attempting to load global blog config from GCS.")
        blog_bucket_name =  BLOG_BUCKET_NAME
        bucket = get_gcs_bucket(blog_bucket_name)
        if not bucket:
            logger.critical(f"Could not get GCS bucket '{blog_bucket_name}'.")
            return default_config # Or raise error

        blob = bucket.blob(str(BLOG_CONFIG_FILE_PATH))
        try:
            if blob.exists():
                config_content = blob.download_as_string()
                loaded_config = json.loads(config_content.decode('utf-8'))
                #logger.info(f"Successfully loaded global blog config from GCS: gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}")
                return loaded_config
            else:
                logger.error(f"Global blog config not found in GCS at gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}. Returning default.")
                return default_config
        except json.JSONDecodeError as jde:
            logger.critical(f"Error decoding JSON from GCS config (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {jde}", exc_info=True)
            return default_config
        except Exception as e:
            logger.critical(f"Error loading global blog config from GCS (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {e}", exc_info=True)
            return default_config
    else: # Local development mode
        #logger.debug(f"Attempting to load global blog config from local file: {str(BLOG_CONFIG_FILE_PATH)}")
        try:
            if BLOG_CONFIG_FILE_PATH.exists():
                with open(str(BLOG_CONFIG_FILE_PATH), 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                #logger.info(f"Successfully loaded global blog config from local file: {str(BLOG_CONFIG_FILE_PATH)}")
                return loaded_config
            else:
                logger.error(f"Local global blog config file not found: {str(BLOG_CONFIG_FILE_PATH)}. Returning default.")
                return default_config
        except json.JSONDecodeError as jde:
            logger.critical(f"Error decoding JSON from local config file '{str(BLOG_CONFIG_FILE_PATH)}': {jde}", exc_info=True)
            return default_config
        except IOError as ioe:
            logger.critical(f"IOError reading local config file '{str(BLOG_CONFIG_FILE_PATH)}': {ioe}", exc_info=True)
            return default_config
        except Exception as e: # Catch any other unexpected errors
            logger.critical(f"Unexpected error loading local config file '{str(BLOG_CONFIG_FILE_PATH)}': {e}", exc_info=True)
            return default_config


def save_global_blog_config(config_data):
    """
    Saves the global blog configuration.
    Writes to GCS if ENV_MODE is 'deploy', otherwise to local file.
    """
    logger = get_logger()
    env_mode = os.environ.get('ENV_MODE', 'development').lower()

    if env_mode == 'deploy':
        logger.debug(f"Attempting to save global blog config to GCS.")
        blog_bucket_name = BLOG_BUCKET_NAME

        bucket = get_gcs_bucket(blog_bucket_name)
        if not bucket:
            logger.critical(f"Could not get GCS bucket '{blog_bucket_name}' for save.")
            return False

        blob = bucket.blob(str(BLOG_CONFIG_FILE_PATH))
        try:
            json_string = json.dumps(config_data, indent=4)
            blob.upload_from_string(json_string, content_type='application/json')
            logger.info(f"Successfully saved global blog config to GCS: gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}")
            return True
        except Exception as e:
            logger.critical(f"Error saving global blog config to GCS (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {e}", exc_info=True)
            return False
    else: # Local development mode
        logger.debug(f"Attempting to save global blog config to local file: {str(BLOG_CONFIG_FILE_PATH)}")
        try:
            # Ensure parent directory exists for local file
            BLOG_CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(BLOG_CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            logger.info(f"Successfully saved global blog config to local file: {str(BLOG_CONFIG_FILE_PATH)}")
            return True
        except IOError as ioe:
            logger.critical(f"IOError writing local config file '{str(BLOG_CONFIG_FILE_PATH)}': {ioe}", exc_info=True)
            return False
        except Exception as e: # Catch any other unexpected errors
            logger.critical(f"Unexpected error saving local config file '{str(BLOG_CONFIG_FILE_PATH)}': {e}", exc_info=True)
            return False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_thumbnail(original_path, thumbnail_path, size=THUMBNAIL_SIZE):
    logger = get_logger()
    try:
        img = Image.open(original_path)
        img.thumbnail(size) # Preserves aspect ratio

        # Handle specific modes before saving to avoid errors with some formats (e.g. GIF to JPEG)
        if img.mode in ('P', '1'): # Palette or bilevel
            img = img.convert("RGB")
        elif img.mode in ('LA', 'PA'): # Luminance Alpha or Palette Alpha
             # Convert to RGBA if transparency is needed for PNG thumbs, else RGB
            if thumbnail_path.lower().endswith('.png'):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")
        
        # For JPEGs, ensure no alpha channel
        if thumbnail_path.lower().endswith(('.jpg', '.jpeg')) and img.mode == 'RGBA':
            img = img.convert('RGB')
        
        img.save(thumbnail_path)
        return True
    except IOError as e:
        logger.critical(f"Cannot create thumbnail for {original_path}: {e}")
        return False

def save_uploaded_image_and_thumbnail(post_slug, image_file, unique_base_filename):
    logger = get_logger()
    if image_file and allowed_file(image_file.filename):
        original_extension = os.path.splitext(image_file.filename)[1].lower()
        # Use the provided unique_base_filename and append original extension
        original_filename = f"{secure_filename(unique_base_filename)}{original_extension}"
        
        post_image_dir = os.path.join(BLOG_DATA_DIR, post_slug, 'images')
        os.makedirs(post_image_dir, exist_ok=True)
        
        original_image_path = os.path.join(post_image_dir, original_filename)
        
        try:
            image_file.save(original_image_path)
            thumbnail_filename = f"{THUMBNAIL_PREFIX}{original_filename}"
            thumbnail_image_path = os.path.join(post_image_dir, thumbnail_filename)
            if not create_thumbnail(original_image_path, thumbnail_image_path):
                logger.error(f"Thumbnail creation failed for {original_filename} but original was saved.")
            return original_filename
        except Exception as e:
            logger.critical(f"Error saving image {original_filename} or its thumbnail: {e}")
            if os.path.exists(original_image_path): os.remove(original_image_path) # Clean up
            return None
    return None

def save_uploaded_image_and_thumbnail_to_gcs(slug, image_file_storage, unique_base_name):
    """
    Saves an uploaded image and its thumbnail to GCS.
    - image_file_storage: The FileStorage object from Flask's request.files.
    - unique_base_name: A unique name part, like 'img_timestamp_counter', without extension.
    Returns the final saved base filename (e.g., 'img_timestamp_counter.png') on success, None on failure.
    """
    logger = get_logger()

    if not image_file_storage or not image_file_storage.filename:
        logger.critical(f"No image file provided.")
        return None

    original_filename = secure_filename(image_file_storage.filename)
    if not allowed_file(original_filename):
        logger.critical(f"File type not allowed: {original_filename}")
        return None

    _, extension = os.path.splitext(original_filename)
    extension = extension.lower() # Ensure consistent extension casing

    # Final filenames in GCS (without the "images/" prefix, as that's part of the blob path)
    final_gcs_base_filename = f"{unique_base_name}{extension}"
    final_gcs_thumbnail_filename = f"{THUMBNAIL_PREFIX}{unique_base_name}{extension}"

    # GCS object paths
    gcs_original_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/images/{final_gcs_base_filename}"
    gcs_thumbnail_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/images/{final_gcs_thumbnail_filename}"

    bucket = get_gcs_bucket(BLOG_BUCKET_NAME) # Ensure get_gcs_bucket and BLOG_BUCKET_NAME are accessible
    if not bucket:
        logger.critical(f"Could not get GCS bucket.")
        return None

    try:
        # Read image into memory for processing
        image_bytes = image_file_storage.read()
        image_file_storage.seek(0) # Reset stream pointer if needed elsewhere, though read() consumes it

        # 1. Upload original image
        original_blob = bucket.blob(gcs_original_blob_path)
        # Use BytesIO to upload from memory
        original_blob.upload_from_file(BytesIO(image_bytes), content_type=image_file_storage.mimetype)
        #logger.info(f"Uploaded original image to {gcs_original_blob_path}")

        # 2. Create and upload thumbnail
        try:
            img = Image.open(BytesIO(image_bytes))
            img.thumbnail(THUMBNAIL_SIZE) # Resizes in place, maintaining aspect ratio
            
            thumb_io = BytesIO()
            # Determine format for saving thumbnail (e.g., JPEG for smaller size, or keep original)
            # For simplicity, let's try to save in original format if it's common, else PNG/JPEG.
            save_format = img.format if img.format in ['JPEG', 'PNG', 'GIF'] else 'PNG'
            if save_format == 'JPEG':
                 # Ensure image is RGB before saving as JPEG if it was RGBA (e.g. from PNG)
                if img.mode == 'RGBA' or img.mode == 'LA' or (img.mode == 'P' and 'transparency' in img.info) :
                    img = img.convert('RGB')

            img.save(thumb_io, format=save_format)
            thumb_io.seek(0)

            thumbnail_blob = bucket.blob(gcs_thumbnail_blob_path)
            thumbnail_blob.upload_from_file(thumb_io, content_type=f"image/{save_format.lower()}") # Set appropriate content type
            #logger.info(f"Uploaded thumbnail to {gcs_thumbnail_blob_path}")

        except Exception as e_thumb:
            logger.critical(f"Error creating/uploading thumbnail for {original_filename}: {e_thumb}", exc_info=True)
            # Decide on error handling: proceed without thumbnail, or fail operation?
            # For now, let's consider it a partial success if original uploaded, but log error.
            # If thumbnail is critical, you might want to delete the original_blob and return None here.
            # original_blob.delete() # Cleanup if thumbnail is mandatory
            # return None
            pass # Original image still uploaded

        return final_gcs_base_filename # Return the base name of the original uploaded image

    except Exception as e:
        logger.critical(f"Error during image upload process for {original_filename}: {e}", exc_info=True)
        # Potentially try to delete any partially uploaded files if a multi-step process fails
        try:
            if 'original_blob' in locals() and original_blob.exists():
                 original_blob.delete()
        except Exception as e_cleanup:
            logger.critical(f"Error during cleanup of original blob: {e_cleanup}")
        try:
            if 'thumbnail_blob' in locals() and thumbnail_blob.exists():
                 thumbnail_blob.delete()
        except Exception as e_cleanup_thumb:
            logger.critical(f"Error during cleanup of thumbnail blob: {e_cleanup_thumb}")

        return None

def delete_blog_image_and_thumbnail(post_slug, image_filename):
    logger = get_logger()
    if not image_filename: return
    post_image_dir = os.path.join(BLOG_DATA_DIR, post_slug)
    original_image_path = os.path.join(post_image_dir, image_filename)
    thumbnail_image_path = os.path.join(post_image_dir, f"{THUMBNAIL_PREFIX}{image_filename}")
    try:
        if os.path.exists(original_image_path): os.remove(original_image_path)
        if os.path.exists(thumbnail_image_path): os.remove(thumbnail_image_path)
    except OSError as e:
        logger.critical(f"Error deleting image files for {image_filename} in {post_slug}: {e}")


def delete_blog_image_and_thumbnail_from_gcs(slug, original_image_filename):
    """
    Deletes an original image and its corresponding thumbnail from GCS.

    Args:
        slug (str): The slug of the blog post (used as a folder prefix in GCS).
        original_image_filename (str): The filename of the original (full-sized) image
                                       (e.g., "img_timestamp_0.png"). The thumbnail name
                                       is derived by prepending THUMBNAIL_PREFIX.

    Returns:
        bool: True if both blobs were successfully deleted or did not exist initially.
              False if an error occurred during an attempted deletion of an existing blob.
    """
    logger = get_logger()   

    if not slug or not original_image_filename:
        logger.critical(f"Slug or original_image_filename not provided.")
        return False

    if original_image_filename.startswith(os.environ.get("THUMBNAIL_PREFIX", "thumb_")):
        logger.error(
            f"'{original_image_filename}' appears to be a thumbnail name. "
            "This function expects the original image filename to derive both paths. "
            "Proceeding, but ensure calling code provides the original filename."
        )
        # Optionally, you could try to derive the original name, but it's better if the caller is correct.
        # original_image_filename = original_image_filename[len(os.environ.get("THUMBNAIL_PREFIX", "thumb_")):]


    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket:
        logger.critical(f"Could not get GCS bucket '{blog_bucket_name}'.")
        return False

    thumbnail_prefix = os.environ.get("THUMBNAIL_PREFIX", "thumb_")

    # Construct GCS object paths
    gcs_original_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/images/{original_image_filename}"
    gcs_thumbnail_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/images/{thumbnail_prefix}{original_image_filename}"

    paths_to_delete_and_log_names = {
        gcs_original_blob_path: "Original Image",
        gcs_thumbnail_blob_path: "Thumbnail Image"
    }

    all_clear_or_nonexistent = True # Assume success unless an error occurs on an existing blob

    for gcs_path, log_name in paths_to_delete_and_log_names.items():
        blob_to_delete = bucket.blob(gcs_path)
        try:
            if blob_to_delete.exists(): # Check if it exists before trying to delete
                blob_to_delete.delete()
                logger.info(f"Successfully deleted {log_name} from gs://{bucket.name}/{gcs_path}")
            else:
                logger.info(f"{log_name} gs://{bucket.name}/{gcs_path} did not exist. No deletion needed.")
        except Exception as e:
            logger.critical(f"Error deleting {log_name} gs://{bucket.name}/{gcs_path}: {e}", exc_info=True)
            all_clear_or_nonexistent = False # Mark as failed if any GCS API error occurs during deletion

    return all_clear_or_nonexistent



def get_post_config_from_gcs(slug):
    """
    Fetches and parses thecontent.json for a given slug from GCS.
    Returns the post data dictionary or None if not found or error.
    """
    logger = get_logger()

    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket:
        logger.critical(f"Could not get GCS bucket '{blog_bucket_name}'.")
        return None

    config_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/content.json" # Assuming config file name
    blob = bucket.blob(config_blob_path)

    try:
        if blob.exists():
            config_content = blob.download_as_string()
            post_data = json.loads(config_content.decode('utf-8'))
            post_data['slug'] = slug # Ensure slug is part of the returned data
            #logger.debug(f"Successfully fetched config for slug '{slug}' from GCS.")
            return post_data
        else:
            logger.error(f"Post config not found in GCS: gs://{bucket.name}/{config_blob_path}")
            return None
    except json.JSONDecodeError as jde:
        logger.critical(f"Error decoding JSON for slug '{slug}' from GCS (gs://{bucket.name}/{config_blob_path}): {jde}", exc_info=True)
        return None
    except Exception as e:
        logger.critical(f"Error fetching post config for slug '{slug}' from GCS (gs://{bucket.name}/{config_blob_path}): {e}", exc_info=True)
        return None

def save_post_config_to_gcs(slug, post_data):
    """Saves the post_data dictionary ascontent.json for a slug in GCS."""
    logger = get_logger()
    log_prefix = "GCS_SAVE_POST_CONFIG_V1"
    # ... (similar bucket setup as above) ...
    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket: # ... handle error ...
        return False

    config_blob_path = f"{str(BLOG_BLOB_DIR)}/{slug}/content.json"
    blob = bucket.blob(config_blob_path)
    try:
        blob.upload_from_string(json.dumps(post_data, indent=4), content_type='application/json')
        logger.info(f"Post config for '{slug}' saved to GCS: gs://{bucket.name}/{config_blob_path}")
        return True
    except Exception as e:
        logger.critical(f"Error saving post config for '{slug}' to GCS: {e}", exc_info=True)
        return False
    

# In your main rl_data.py

def get_all_posts(published_only=True, sort_key='published_at', reverse_sort=True):
    """
    Gets all blog posts, either from local files or GCS.
    Filters by published status and sorts.
    """
    logger = get_logger()
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    all_posts_data = []

    if published_only==False and sort_key == 'published_at' : # Don't filter by published status if not requested.
        use_sort_key='created_at' # Use 'created_at' if not filtering by published status
    else:
        use_sort_key=sort_key # Use sort_key as selected by user

    if env_mode == 'deploy':
        #logger.debug("get_all_posts: Fetching all posts from GCS (deploy mode).")
        blog_bucket_name = BLOG_BUCKET_NAME
        bucket = get_gcs_bucket(blog_bucket_name)
        if not bucket:
            logger.critical(f"get_all_posts: Could not get GCS bucket '{blog_bucket_name}'.")
            return []

        # GCS lists objects flatly. We need to find all 'content.json' files.
        # A common prefix for posts can help, e.g., if all posts are under 'posts/'
        # For now, assume slugs are top-level "directories".
        # Listing by delimiter '/' can simulate directories.
        
        # Efficiently get slugs by looking forcontent.json markers
        slugs_in_gcs = set()
        blobs = bucket.list_blobs(prefix=f'') # Or a more specific prefix if your posts are nested
        for blob_item in blobs:
            # Assuming path is like "my-slug/content.json" or "my-slug/images/..."
            parts = blob_item.name.split('/')
            #logger.debug(f"get_all_posts: Checking {parts}")
            if len(parts) > 1: # It's in a "folder"
                if parts[-1] == 'content.json': # Found a config file
                    #logger.debug(f"get_all_posts:content.json found in {parts}")
                    slugs_in_gcs.add(parts[1]) # parts[0] is 'blog_data'
        
        #logger.info(f"get_all_posts: Found {len(slugs_in_gcs)} potential post slugs in GCS.")

        for slug_from_gcs in slugs_in_gcs:
            post_content = get_post_config_from_gcs(slug_from_gcs) # Fetch individual config
            if post_content:
                if published_only and not post_content.get('is_published', False):
                    continue
                all_posts_data.append(post_content)
    
    else: # Local development mode
        #logger.debug("get_all_posts: Fetching all posts from local filesystem (dev mode).")
        if not os.path.exists(LOCAL_BLOG_DATA_DIR): # Ensure LOCAL_BLOG_DATA_DIR is correct
            logger.critical(f"get_all_posts: Local blog data directory not found: {LOCAL_BLOG_DATA_DIR}")
            return []
            
        for slug_folder_name in os.listdir(LOCAL_BLOG_DATA_DIR):
            post_dir = os.path.join(LOCAL_BLOG_DATA_DIR, slug_folder_name)
            if os.path.isdir(post_dir):
                config_path = os.path.join(post_dir, 'content.json') # or content.json
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            post_data = json.load(f)
                        post_data['slug'] = slug_folder_name # Use folder name as slug
                        if published_only and not post_data.get('is_published', False):
                            continue
                        all_posts_data.append(post_data)
                    except Exception as e:
                        logger.critical(f"get_all_posts: Error reading local post '{slug_folder_name}': {e}", exc_info=True)
    
    # Sort posts
    if use_sort_key:
        # Handle posts that might be missing the use_sort_key or have None for date fields
        def get_sort_value(post):
            val = post.get(use_sort_key)
            if isinstance(val, str): # Attempt to parse if it's a date string
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00"))
                except ValueError:
                    return datetime.min.replace(tzinfo=datetime.timezone.utc) # Fallback for unparseable strings
            elif val is None and use_sort_key.endswith('_at'): # Default for missing dates
                return datetime.min.replace(tzinfo=datetime.timezone.utc)
            elif val is None: # Default for other missing keys
                return 0 # Or some other sensible default
            return val

        try:
            all_posts_data.sort(key=get_sort_value, reverse=reverse_sort)
        except Exception as e_sort:
            logger.critical(f"get_all_posts: Error sorting posts by '{use_sort_key}': {e_sort}", exc_info=True)
            # Proceed with unsorted data or handle as critical error

    # Convert date strings to datetime objects for template consistency if needed
    # for post in all_posts_data:
    #     for key in ['created_at', 'updated_at', 'published_at']:
    #         if post.get(key) and isinstance(post[key], str):
    #             try:
    #                 post[key] = datetime.fromisoformat(post[key].replace("Z", "+00:00"))
    #             except ValueError:
    #                 pass # Keep as string if parsing fails
                        
    #logger.info(f"get_all_posts: Returning {len(all_posts_data)} posts.")
    return all_posts_data

def get_post(slug, increment_view_count=False):
    """
    Gets a single blog post by slug, either from local files or GCS.
    Handles view count increment.
    """
    logger = get_logger()
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    post_data = None

    if env_mode == 'deploy':
        #logger.debug(f"get_post: Fetching post '{slug}' from GCS (deploy mode).")
        post_data = get_post_config_from_gcs(slug) # Uses the GCS helper
        if post_data and increment_view_count and post_data.get('is_published', False):
            post_data['view_count'] = post_data.get('view_count', 0) + 1
            post_data['updated_at'] = datetime.now().isoformat() # View count is an update
            #logger.debug(f"get_post: incrementing view count {post_data['view_count']} for '{slug}' to GCS.")
            if not save_post_config_to_gcs(slug, post_data): # Save updated data back to GCS
                logger.critical(f"get_post: Failed to save updated view count for '{slug}' to GCS.")
                # Decide how to handle: return old data, or None? For now, return potentially stale data.
    else: # Local development mode
        #logger.debug(f"get_post: Fetching post '{slug}' from local filesystem (dev mode).")
        # --- This needs to be your existing local file reading logic ---
        post_dir_path = os.path.join(LOCAL_BLOG_DATA_DIR, slug) # Ensure LOCAL_BLOG_DATA_DIR is correct
        config_path = os.path.join(post_dir_path, 'content.json') # or content.json
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r+', encoding='utf-8') as f: # Open r+ for read/write
                    post_data = json.load(f)
                    post_data['slug'] = slug # Ensure slug is present
                    if increment_view_count and post_data.get('is_published', False):
                        post_data['view_count'] = post_data.get('view_count', 0) + 1
                        post_data['updated_at'] = datetime.now().isoformat()
                        f.seek(0) # Go to the beginning of the file
                        json.dump(post_data, f, indent=4)
                        f.truncate() # Remove trailing old content if new content is shorter
            except Exception as e:
                logger.critical(f"get_post: Error reading/updating local post '{slug}': {e}", exc_info=True)
                post_data = None # Ensure post_data is None on error
        # --- End of local file logic ---

    if not post_data:
        logger.error(f"get_post: Post '{slug}' not found in mode '{env_mode}'.")
        return None

    return post_data

def get_static_page_lastmod(template_name):
    logger = get_logger()
    try:
        filepath = os.path.join(TEMPLATE_FOLDER, template_name)
        if os.path.exists(filepath):
            mod_time = os.path.getmtime(filepath)
            return datetime.fromtimestamp(mod_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception as e:
        logger.critical(f"Error getting lastmod for {template_name}: {e}")
    return None

def format_iso_datetime_for_sitemap(iso_string):
    """Converts ISO string (potentially with microseconds) to sitemap's lastmod format."""
    logger = get_logger()
    if not iso_string:
        return None
    try:
        # Try parsing with microseconds first
        dt_obj = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except ValueError:
        try:
            # Try parsing without microseconds if the first attempt fails
            dt_obj = datetime.strptime(iso_string.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S+00:00")
        except ValueError:
            logger.error(f"Could not parse datetime string for sitemap: {iso_string}")
            return None

    # Ensure it's timezone-aware (UTC)
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    else:
        dt_obj = dt_obj.astimezone(timezone.utc)

    return dt_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def get_gcs_bucket(bucket_name):
    logger = get_logger()
    storage_client = storage.Client()
    if not storage_client:
        logger.critical("GCS client not initialized.")
        return None
    return storage_client.bucket(bucket_name)


def list_blog_slugs_from_gcs(gcs_object_prefix=''): # Renamed for clarity from the method's 'prefix'
    logger = get_logger()
    slugs = set()
    log_prefix_func = "LIST_GCS_SLUGS_V1" # For this function's logs

    #logger.info(f"{log_prefix_func} :: Listing slugs with GCS object prefix: '{gcs_object_prefix}'")
    
    bucket = get_gcs_bucket(BLOG_BUCKET_NAME) # Ensure BLOG_BUCKET_NAME is accessible
    if not bucket:
        logger.critical(f"{log_prefix_func} :: Bucket not available.")
        return list(slugs) # Return empty list on error

    # Call list_blobs using the 'prefix' keyword argument
    try:
        blobs_iterator = bucket.list_blobs(prefix=gcs_object_prefix)
        
        # Logging the iterator itself won't show contents immediately
        #logger.info(f"{log_prefix_func} :: Blobs iterator: {blobs_iterator}") 

        processed_blob_names = 0
        for blob in blobs_iterator:
            processed_blob_names += 1
            #logger.debug(f"{log_prefix_func} :: Processing GCS blob: {blob.name}")    
            
            # Make sure gcs_object_prefix is handled correctly for splitting
            # If gcs_object_prefix is "posts/", and blob.name is "posts/my-slug/content.json"
            # then relevant_path = "my-slug/content.json"
            relevant_path = blob.name
            if gcs_object_prefix and blob.name.startswith(gcs_object_prefix):
                relevant_path = blob.name[len(gcs_object_prefix):].lstrip('/') # Remove prefix and leading slash

            parts = relevant_path.split('/')
            #logger.debug(f"{log_prefix_func} :: Relevant path parts: {parts} (from {blob.name})")
                    
            # We are looking for "slug/content.json" structure after the gcs_object_prefix
            if len(parts) >= 2 and parts[-1] == 'content.json': # Or your content.json
                slug = parts[-2] # The directory name containing content.json is the slug
                #logger.debug(f"{log_prefix_func} :: Adding slug: {slug}")
                slugs.add(slug)
            #else:
                #logger.debug(f"{log_prefix_func} :: len(parts): {len(parts)}, parts[-1]: {parts[-1]}")
            #elif len(parts) == 1 and parts[0].endswith('content.json'): # Case: prefix="foo/bar/content.json"
                # This case is less likely if gcs_object_prefix is a "directory"
                #logger.debug(f"{log_prefix_func} :: Adding slug V2: {slug}")
                #slug = parts[0][:-len('/content.json')]
                #slugs.add(slug)


        #if processed_blob_names == 0:
        #    logger.info(f"{log_prefix_func} :: No blobs found matching prefix '{gcs_object_prefix}'.")
        #else:
        #    logger.info(f"{log_prefix_func} :: Processed {processed_blob_names} blobs from GCS matching prefix.")

    except Exception as e_list:
        logger.critical(f"{log_prefix_func} :: Error during bucket.list_blobs or iteration: {e_list}", exc_info=True)
        return list(slugs) # Return empty list on error

    #logger.info(f"{log_prefix_func} :: Returning {len(slugs)} slugs: {slugs if len(slugs) < 10 else str(list(slugs)[:10]) + '...'}")
    return list(slugs)

# In rl_data_gcs.py
def check_if_post_slug_exists_in_gcs(slug_to_check):
    logger = get_logger()
    
    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name) # Your existing helper
    if not bucket:
        logger.critical(f"Could not get GCS bucket for slug check.")
        return True # Fail safe

    # Check for the existence of the content.json file for that slug
    config_blob_path = f"{slug_to_check}/content.json"
    blob = bucket.blob(config_blob_path)
    
    try:
        if blob.exists():
            #logger.info(f"Slug '{slug_to_check}' (content.json) FOUND in GCS.")
            return True
    except Exception as e:
        logger.critical(f"Error checking GCS for slug '{slug_to_check}': {e}", exc_info=True)
        return True # Fail safe

    logger.info(f"Slug '{slug_to_check}' (content.json) NOT FOUND in GCS.")
    return False

def save_post_to_gcs(slug, post_data):
    logger = get_logger()
    bucket = get_gcs_bucket(BLOG_BUCKET_NAME)
    if not bucket:
        return False
    blob_name = f"{str(BLOG_BLOB_DIR)}/{slug}/content.json"
    blob = bucket.blob(blob_name)
    try:
        # Update 'updated_at' and ensure 'published_at' logic here if not done before calling
        post_data['updated_at'] = datetime.now().isoformat()
        # published_at logic should be handled in the route before this function

        blob.upload_from_string(json.dumps(post_data, indent=4), content_type='application/json')
        #logger.info(f"Post {slug} saved to GCS: {blob_name}")
        return True
    except Exception as e:
        logger.critical(f"Error saving post {slug} to GCS: {e}")
        return False



def get_blog_image_url_from_gcs(slug, filename):
    logger = get_logger()
    
    #try:
    #    logger.info(f" :: For {str(BLOG_BLOB_DIR)}/{slug}/{filename}. GCS Lib: {google.cloud.storage.__version__}, GAuth Lib: {google.auth.__version__}")
    #except Exception: pass # Best effort logging

    bucket = get_gcs_bucket(BLOG_BUCKET_NAME)
    if not bucket:
        logger.critical(f"Failed to get GCS bucket object for '{BLOG_BUCKET_NAME}'.")
        return None

    base_filename = filename.split('/')[-1]
    is_thumbnail_in_name = base_filename.startswith("thumb_")
    actual_filename_part = base_filename[len("thumb_"):] if is_thumbnail_in_name else base_filename
    path_in_bucket = f"{str(BLOG_BLOB_DIR)}/{slug}/images/{'thumb_' if is_thumbnail_in_name else ''}{actual_filename_part}"

    #logger.info(f"Attempting to sign for object: gs://{bucket.name}/{path_in_bucket}") #

    blob = bucket.blob(path_in_bucket)

    # --- Determine which credentials to use ---
    signing_credentials = None
    credentials_method_used = "None"

    #logger.info(f" :: Attempting to use iam.Signer (for Cloud Run or local ADC).")
    try:
        # Credentials for calling the IAM Credentials API:
        # - Cloud Run: Metadata server credentials for the service's SA.
        # - Local: ADC (e.g., user creds via gcloud auth app-default login).
        credentials_for_iam_api_call, project_id = google.auth.default(
            scopes=['https://www.googleapis.com/auth/iam']
        )
        #logger.debug(f" :: Credentials for IAM API call type: {type(credentials_for_iam_api_call)}, Project: {project_id}")

        # The SA that will perform the signing (via IAM Credentials API).
        # In Cloud Run, this *is* credentials_for_iam_api_call.service_account_email (or should be).
        # Locally, credentials_for_iam_api_call (user ADC) needs 'Service Account Token Creator' on this target SA.
        target_sa_email_for_signing = os.environ.get("GCP_SERVICE_ACCOUNT_EMAIL", SERVICE_ACCOUNT_EMAIL)
        #logger.debug(f" :: Target SA for signing via IAM API: {target_sa_email_for_signing}")

        http_request_transport = google.auth.transport.requests.Request()
        
        signing_credentials = google_auth_iam.Signer(
            request=http_request_transport,
            credentials=credentials_for_iam_api_call,
            service_account_email=target_sa_email_for_signing
        )
        credentials_method_used = f"iam.Signer (Target SA: {target_sa_email_for_signing}, Caller Creds: {type(credentials_for_iam_api_call)})"
        #logger.debug(f" :: iam.Signer object created: {type(signing_credentials)}")
    except Exception as e_iam_signer:
        logger.critical(f" :: Failed to create iam.Signer: {e_iam_signer}", exc_info=True)
        return None # Cannot proceed if iam.Signer creation fails

    if not signing_credentials:
        logger.critical(f" :: No valid signing credentials could be established.")
        return None

    # --- Generate the Signed URL using the 'credentials' kwarg ---
    try:
        #logger.info(f" :: Attempting generate_signed_url for 'gs://{BLOG_BUCKET_NAME}/{path_in_bucket}' using method: {credentials_method_used}")
        
        credentials, project_id = google.auth.default()

        # Perform a refresh request to get the access token of the current credentials (Else, it's None)
        http_request_transport = google.auth.transport.requests.Request()
        credentials.refresh(http_request_transport)

        client = storage.Client()
        expires = timedelta(minutes=60)

        # In case of user credential use, define manually the service account to use (for development purpose only)
        target_sa_email_for_signing = os.environ.get("GCP_SERVICE_ACCOUNT_EMAIL", SERVICE_ACCOUNT_EMAIL)

        # If you use a service account credential, you can use the embedded email
        if hasattr(credentials, "service_account_email"):
            service_account_email = credentials.service_account_email

        signed_url = blob.generate_signed_url(
            expiration=expires,
            service_account_email=target_sa_email_for_signing, 
            access_token=credentials.token)       
    
        #logger.info(f" :: Successfully generated signed URL.")
        return signed_url
    except AttributeError as ae: # "need private key"
         logger.critical(f" :: AttributeError (likely 'need private key') with '{credentials_method_used}': {ae}", exc_info=True)
         if isinstance(signing_credentials, google_auth_iam.Signer):
             logger.critical(f" :: This confirms the issue: iam.Signer passed to 'credentials' kwarg is not being handled as expected by GCS lib {google.cloud.storage.__version__} when backed by token-based credentials.")
         return None
    except google.auth.exceptions.RefreshError as re: # For ADC/metadata issues if iam.Signer fails during its own auth
        logger.critical(f" :: Google Auth RefreshError with '{credentials_method_used}': {re}", exc_info=True)
        return None
    except Exception as e: # Catch-all for other unexpected errors
        logger.critical(f" :: General error generating signed URL with '{credentials_method_used}': {e}", exc_info=True)
        return None


def delete_blog_post_from_gcs(slug):
    """
    Deletes all GCS objects associated with a blog post slug
    under the configured BLOG_BLOB_DIR in the BLOG_BUCKET_NAME.
    Effectively removes the "slug directory" and its contents.
    """
    logger = get_logger()

    if not slug:
        logger.critical(f"Slug not provided for deletion.")
        return False

    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket:
        logger.critical(f"Could not get GCS bucket '{blog_bucket_name}'.")
        return False

    # Construct the prefix for objects to delete
    # BLOG_BLOB_DIR is an optional top-level "folder" like "posts" or "blog_content"
    # If BLOG_BLOB_DIR is empty, posts are at the bucket root.
    blog_base_dir = BLOG_BLOB_DIR

    # Ensure the prefix correctly forms "base_dir/slug/"
    # Using f-string directly is fine as GCS paths are forward-slash separated
    prefix_to_delete = f"{blog_base_dir}/{slug}/"
    
    logger.info(f"Attempting to delete all objects with prefix 'gs://{bucket.name}/{prefix_to_delete}'")

    # List all blobs with this prefix.
    # list() materializes the iterator, useful for counting or if you need the full list.
    # For very many objects, you might process the iterator directly without list().
    blobs_to_delete_iterator = bucket.list_blobs(prefix=prefix_to_delete)
    
    deleted_count = 0
    errors_encountered = False

    # Iterate and delete each blob
    # This is robust as it attempts to delete each one individually.
    for blob_item in blobs_to_delete_iterator:
        try:
            #(f"Deleting blob: gs://{bucket.name}/{blob_item.name}")
            blob_item.delete()
            deleted_count += 1
        except Exception as e:
            logger.critical(f"Failed to delete blob gs://{bucket.name}/{blob_item.name}: {e}", exc_info=True)
            errors_encountered = True
            # Decide if you want to continue deleting others or stop on first error.
            # This loop continues by default.

    # Delete the image folder and slug folder
    folders_to_try_delete = [
        f"{str(BLOG_BLOB_DIR)}/{slug}/images",          # image folder
        f"{str(BLOG_BLOB_DIR)}/{slug}"                  # slug folder
    ]
    for path_to_delete in folders_to_try_delete:
        folder_blob = bucket.blob(path_to_delete)
        try:
            if folder_blob.exists():
                folder_blob.delete()
                logger.info(f"Deleted image {path_to_delete} from GCS for post {slug}.")
        except Exception as e:
            logger.critical(f"Error deleting image {path_to_delete} from GCS for post {slug}: {e}")

    if errors_encountered:
        logger.error(f"Finished deletion attempt for prefix 'gs://{bucket.name}/{prefix_to_delete}' with errors. Deleted {deleted_count} objects.")
        return False # Indicate that not everything went smoothly
    else:
        if deleted_count > 0:
            logger.info(f"Successfully deleted {deleted_count} objects for prefix 'gs://{bucket.name}/{prefix_to_delete}'.")
        else:
            logger.info(f"No objects found to delete for prefix 'gs://{bucket.name}/{prefix_to_delete}'. (Considered successful)")
        return True

def delete_blog_image_from_gcs(slug, filename):
    logger = get_logger()
    # filename might be like "img_timestamp.png" or "images/img_timestamp.png"
    # or "thumb_img_timestamp.png" or "images/thumb_img_timestamp.png"
    bucket = get_gcs_bucket(BLOG_BUCKET_NAME)
    if not bucket: return False

    base_filename = filename.split('/')[-1] # Get "img_..." or "thumb_..."
    
    # Construct full and thumb paths based on the base filename
    if base_filename.startswith("thumb_"):
        # If deleting a thumbnail, also try to delete the full image
        full_img_base = base_filename[len("thumb_"):]
        paths_to_try_delete = [
            f"{str(BLOG_BLOB_DIR)}/{slug}/images/{base_filename}",          # The thumb itself
            f"{str(BLOG_BLOB_DIR)}/{slug}/images/{full_img_base}"           # The corresponding full image
        ]
    else:
        # If deleting a full image, also try to delete the thumbnail
        paths_to_try_delete = [
            f"{str(BLOG_BLOB_DIR)}/{slug}/images/{base_filename}",          # The full image itself
            f"{str(BLOG_BLOB_DIR)}/{slug}/images/thumb_{base_filename}"     # The corresponding thumbnail
        ]
    
    deleted_any = False
    for path_to_delete in paths_to_try_delete:
        blob = bucket.blob(path_to_delete)
        try:
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted image {path_to_delete} from GCS for post {slug}.")
                deleted_any = True
        except Exception as e:
            logger.critical(f"Error deleting image {path_to_delete} from GCS for post {slug}: {e}")
    return deleted_any


def sync_local_blogs_to_gcs():
    """
    Synchronizes blog posts from the local directory inside docker to GCS.
    Only syncs posts (slugs) that exist locally but not in GCS.
    Assumes local directory names are the slugs.
    Returns a dictionary with sync status and counts.
    """
    logger = get_logger()
    #logger.info(f"Starting sync of local blog posts to GCS...")

    # --- Configuration - ensure these are correctly fetched ---
    local_blog_data_path = LOCAL_BLOG_DATA_DIR
    blog_bucket_name_from_env = BLOG_BUCKET_NAME
    blog_gcs_base_prefix = "blog_data" #if change this to a path then seems to be a problem.

    # --- GCS Client and Slug Listing ---
    # list_blog_slugs_from_gcs should use a properly initialized client
    # and account for blog_gcs_base_prefix.
    try:
        gcs_slugs = set(list_blog_slugs_from_gcs(gcs_object_prefix=blog_gcs_base_prefix))
        logger.info(f"{len(gcs_slugs)} slugs found in GCS under prefix '{blog_gcs_base_prefix}'.")
    except Exception as e_gcs_list:
        logger.critical(f"Failed to list slugs from GCS: {e_gcs_list}", exc_info=True)
        return {"status": "error", "message": "Failed to list GCS slugs.", "synced_count": 0, "failed_count": 0, "skipped_count": 0}

    if not local_blog_data_path.exists() or not local_blog_data_path.is_dir():
        logger.info(f"Local blog data directory not found: {local_blog_data_path}. No local posts to sync.")
        return {"status": "no_local_data", "message": "Local blog data directory not found.", "synced_count": 0, "failed_count": 0, "skipped_count": 0}

    synced_this_run_count = 0
    failed_this_run_slugs = []
    skipped_this_run_count = 0
    config_file_name = "content.json" # As per your original code

    for local_slug_folder_name in os.listdir(local_blog_data_path):
        local_post_full_path = local_blog_data_path / local_slug_folder_name
        if local_post_full_path.is_dir():
            slug_to_sync = local_slug_folder_name # Assuming folder name is the slug
            
            if slug_to_sync not in gcs_slugs: # Core logic: only sync if not already in GCS
                #logger.info(f"New local post '{slug_to_sync}' not in GCS. Attempting sync.")
                config_file_local_path = local_post_full_path / config_file_name
                
                if config_file_local_path.exists() and config_file_local_path.is_file():
                    current_post_fully_synced = True # Assume success for this post initially
                    try:
                        with open(config_file_local_path, 'r', encoding='utf-8') as f_local:
                            post_data = json.load(f_local)
                        
                        if post_data.get('slug') != slug_to_sync:
                            #logger.error(f"Slug in '{config_file_name}' ('{post_data.get('slug')}') for '{slug_to_sync}' doesn't match folder. Using folder name.")
                            post_data['slug'] = slug_to_sync 
                        
                        # save_post_config_to_gcs should handle blog_gcs_base_prefix internally
                        if save_post_config_to_gcs(slug_to_sync, post_data):
                            logger.info(f"Synced '{config_file_name}' for '{slug_to_sync}' to GCS.")
                            
                            local_images_path = local_post_full_path / 'images'
                            if local_images_path.exists() and local_images_path.is_dir():
                                images_synced_for_this_post = 0
                                bucket_for_img_upload = get_gcs_bucket(blog_bucket_name_from_env) # Get bucket once per post
                                if not bucket_for_img_upload:
                                    logger.critical(f"Could not get GCS bucket for image upload of '{slug_to_sync}'. Skipping image sync for this post.")
                                    current_post_fully_synced = False
                                else:
                                    for img_filename in os.listdir(local_images_path):
                                        local_img_full_path = local_images_path / img_filename
                                        if local_img_full_path.is_file():
                                            # Construct GCS object name for the image
                                            gcs_img_path_parts = [slug_to_sync, "images", img_filename]
                                            if blog_gcs_base_prefix: # Add base prefix if it exists
                                                gcs_img_path_parts.insert(0, blog_gcs_base_prefix)
                                            gcs_img_blob_name = "/".join(gcs_img_path_parts)
                                            
                                            img_blob = bucket_for_img_upload.blob(gcs_img_blob_name)
                                            try:
                                                # Determine content type (optional but good)
                                                content_type_guess = None
                                                if '.' in img_filename:
                                                    ext_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}
                                                    content_type_guess = ext_map.get(img_filename.rsplit('.', 1)[1].lower())

                                                img_blob.upload_from_filename(str(local_img_full_path), content_type=content_type_guess)
                                                #logger.info(f"Synced image '{img_filename}' for '{slug_to_sync}' to gs://{bucket_for_img_upload.name}/{gcs_img_blob_name}")
                                                images_synced_for_this_post += 1
                                            except Exception as e_img:
                                                logger.critical(f"Failed to upload image '{img_filename}' for '{slug_to_sync}': {e_img}", exc_info=True)
                                                current_post_fully_synced = False
                                    #logger.info(f"For post '{slug_to_sync}', attempted to sync {images_synced_for_this_post} images.")
                            else:
                                logger.info(f"No 'images' directory found for local post '{slug_to_sync}'.")
                        else:
                             logger.critical(f"Failed to save '{config_file_name}' for '{slug_to_sync}' to GCS.")
                             current_post_fully_synced = False
                        
                        if current_post_fully_synced:
                            synced_this_run_count += 1
                        else:
                            failed_this_run_slugs.append(slug_to_sync)

                    except json.JSONDecodeError as jde:
                        logger.critical(f"Error decoding JSON from '{config_file_local_path}': {jde}", exc_info=True)
                        failed_this_run_slugs.append(slug_to_sync)
                    except Exception as e_sync_post:
                        logger.critical(f"General error syncing post '{slug_to_sync}': {e_sync_post}", exc_info=True)
                        failed_this_run_slugs.append(slug_to_sync)
                else:
                    logger.error(f"'{config_file_name}' not found for local post '{slug_to_sync}'. Skipping sync.")
                    # Not necessarily a failure of the overall sync process, just this item.
                    # You could add it to a list of "skipped_no_config_slugs" if needed.
            else:
                #logger.debug(f"Post '{slug_to_sync}' already exists in GCS. Skipping sync.")
                skipped_this_run_count += 1
        # else: item is not a directory
    
    final_message = f"Sync complete. New posts synced: {synced_this_run_count}. Posts skipped (already in GCS): {skipped_this_run_count}. Posts failed to sync fully: {len(failed_this_run_slugs)}."
    logger.info(f"{final_message}")
    if failed_this_run_slugs:
        logger.error(f"Slugs that failed to sync completely: {failed_this_run_slugs}")
        return {"status": "partial_success", "message": final_message, "synced": synced_this_run_count, "failed": len(failed_this_run_slugs), "skipped": skipped_this_run_count}
    
    return {"status": "success", "message": final_message, "synced": synced_this_run_count, "failed": 0, "skipped": skipped_this_run_count}
