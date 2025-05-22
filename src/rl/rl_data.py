import os
from pathlib import Path
import logging
import uuid
import json
from logging.handlers import RotatingFileHandler
import threading
import portalocker  # Cross-platform file locking
from werkzeug.utils import secure_filename
from flask import g, render_template as flask_render_template

from google.cloud import storage
import csv
import io
import math
from datetime import datetime, timedelta, timezone
import sys
from PIL import Image # Import Pillow
from io import BytesIO

# In your rl_data_gcs.py or rl_data.py
from google.cloud import storage
from google.auth import iam as google_auth_iam # Alias to avoid confusion with any 'iam' variable
import google.auth
import google.auth.transport.requests
import inspect

# file sturcture 'constants'
# static - csv 	- input
#				- generic
#		 - pdf 	- generic
#				- comp
#		 - png	- generic
#				- comp

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
MAX_IMAGES_PER_POST = 6
THUMBNAIL_SIZE = (400, 400) # Max width, max height for thumbnails
THUMBNAIL_PREFIX = "thumb_" # Prepended to original filename for thumbnail

BASE_URL = "https://redline-results-951032250531.asia-southeast1.run.app"
ROBOTS_DIR       = Path('static') 

BUCKET_NAME = 'redline-fitness-results-feedback'
BLOG_BUCKET_NAME = BUCKET_NAME
BLOG_BLOB_DIR = BLOG_DATA_DIR

FEEDBACK_BUCKET_NAME = BUCKET_NAME
FEEDBACK_BLOB_DIR = Path('feedback')
FEEDBACK_BLOB_FILEPATH = FEEDBACK_BLOB_DIR / FEEDBACK_FILENAME

SERVICE_ACCOUNT_EMAIL = "951032250531-compute@developer.gserviceaccount.com"

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
EVENTLIST23 =      [         'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']
EVENTLISTSTART23 = ['Start', 'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']

#The 2024 Events Lists
EVENTLIST24 =      [         'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']
EVENTLISTSTART24 = ['Start', 'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']

# Your data for filtering purposes
EVENT_DATA_LIST = [
    #2024
    ["WomensSinglesCompetitive2024", "REDLINE Fitness Games '24 Womens Singles Comp.", "2024", "WOMENS", "SINGLES_COMPETITIVE", "KL"],
    ["MensSinglesCompetitive2024", "REDLINE Fitness Games '24 Mens Singles Comp.", "2024", "MENS", "SINGLES_COMPETITIVE", "KL"],
    ["WomensSinglesOpen2024", "REDLINE Fitness Games '24 Womens Singles Open", "2024", "WOMENS", "SINGLES_OPEN", "KL"],
    ["MensSinglesOpen2024", "REDLINE Fitness Games '24 Mens Singles Open", "2024", "MENS", "SINGLES_OPEN", "KL"],
    ["WomensDoubles2024", "REDLINE Fitness Games '24 Womens Doubles", "2024", "WOMENS", "DOUBLES", "KL"],
    ["MensDoubles2024", "REDLINE Fitness Games '24 Mens Doubles", "2024", "MENS", "DOUBLES", "KL"],
    ["MixedDoubles2024", "REDLINE Fitness Games '24 Mixed Doubles", "2024", "MIXED", "DOUBLES", "KL"],
    ["TeamRelayWomen2024", "REDLINE Fitness Games '24 Womens Team Relay", "2024", "WOMENS", "RELAY", "KL"],
    ["TeamRelayMen2024", "REDLINE Fitness Games '24 Mens Team Relay", "2024", "MENS", "RELAY", "KL"],
    ["TeamRelayMixed2024", "REDLINE Fitness Games '24 Mixed Team Relay", "2024", "MIXED", "RELAY", "KL"],
    #2023
    ["WomensSinglesCompetitive2023", "REDLINE Fitness Games '23 Womens Singles Comp.", "2023", "WOMENS", "SINGLES_COMPETITIVE", "KL"],
    ["MensSinglesCompetitive2023", "REDLINE Fitness Games '23 Mens Singles Comp.", "2023", "MENS", "SINGLES_COMPETITIVE", "KL"],
    ["WomensSinglesOpen2023", "REDLINE Fitness Games '23 Womens Singles Open", "2023", "WOMENS", "SINGLES_OPEN", "KL"],
    ["MensSinglesOpen2023", "REDLINE Fitness Games '23 Mens Singles Open", "2023", "MENS", "SINGLES_OPEN", "KL"],
    ["WomensDoubles2023", "REDLINE Fitness Games '23 Womens Doubles", "2023", "WOMENS", "DOUBLES", "KL"],
    ["MensDoubles2023", "REDLINE Fitness Games '23 Mens Doubles", "2023", "MENS", "DOUBLES", "KL"],
    ["MixedDoubles2023", "REDLINE Fitness Games '23 Mixed Doubles", "2023", "MIXED", "DOUBLES", "KL"],
    ["TeamRelayWomen2023", "REDLINE Fitness Games '23 Womens Team Relay", "2023", "WOMENS", "RELAY", "KL"],
    ["TeamRelayMen2023", "REDLINE Fitness Games '23 Mens Team Relay", "2023", "MENS", "RELAY", "KL"],
    ["TeamRelayMixed2023", "REDLINE Fitness Games '23 Mixed Team Relay", "2023", "MIXED", "RELAY", "KL"],
]

pngStringEventBarCorr = "Below is a correlation bar chart, which provides a picture that uses bars to show how strongly two things are connected — here we are looking at how well Overall Time is linked to each challenge finishing Position"
pngStringEventHeatCorr = "Below is an event Correlation heat chart, which uses a colorful grid that shows how often different events happen together, using colors to show how strong the connection is"
pngStringEventHistogram = "Below is an event histogram, which is a simple bar chart that shows how often something happens; here we are counting how many people finish between certain times and showing it with bars."
pngStringEventBarChart = "Below is a stacked bar chart, which is a bar chart where each bar is split into colored sections to show parts of a whole, here we show how many people finish each challenge between certain times using different colours."
pngStringEventViolinChart = "Below is a Violin Chart, which is a fancy graph that looks like a stretched-out violin and shows how data is spread out, like showing how long challenges take, with the wide parts meaning that most people finished at that time."
pngStringEventBarChartCutoff = "Below is a a Bar Chart, which shows how many people miss the 7 minute event cut off mark."
pngStringEventPieChart = "Below is a Pie Chart, which is a circle divided into slices to show parts of a whole, like a pizza showing how much each friend ate."
pngStringEventScatterPlot = "Below is a scatter chart, which is a graph with dots that show where two things happen together, here we  put a dot for each competitors overall postion and their statation finish time."

pngStringEventBarChartCompetitor = "Below is a Competitor stacked bar chart, which is a bar chart where each bar is split into colored sections to show parts of a whole, here we show how many people finish each challenge between certain times using different colours. Note the competitor is highlighted."
pngStringEventViolinChartCompetitor = "Below is a Competitor Violin Chart, which is a fancy graph that looks like a stretched-out violin and shows how data is spread out, like showing how long challenges take, with the wide parts meaning that most people finished at that time. Note the competitor is highlighted."
pngStringEventPieChartCompetitor = "Below is a Competitor Pie Chart, which is a circle divided into slices to show parts of a whole, like a pizza showing how much each friend ate. "
pngStringEventScatterPlotCompetitor = "Below is a Competitor scatter chart, which is a graph with dots that show where two things happen together, here we  put a dot for each competitors overall postion and their statation finish time."


# Generate a unique worker ID that persists for this worker process
WORKER_ID = str(uuid.uuid4())[:8]

# Create a thread-local storage for request context information
thread_local = threading.local()


"""
Improved logging implementation for Flask with multiple workers
- Uses a central log configuration file
- Adds worker ID for better tracking
- Uses file locks to prevent race conditions
- Supports graceful reloading
"""
class WorkerInfoFilter(logging.Filter):
    """Filter that adds worker ID and request info to log records"""
    def filter(self, record):
         
        # Add worker_id attribute to the record
        if not hasattr(record, 'worker_id'):
            record.worker_id = WORKER_ID
                    
        # Add request info if available
        if not hasattr(record, 'request_id'):
            if hasattr(thread_local, 'request_id'):
                record.request_id = thread_local.request_id
            else:
                record.request_id = '-'

        return True

class SafeRotatingFileHandler(RotatingFileHandler):
    """Thread and process-safe RotatingFileHandler using cross-platform file locking"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock_file = f"{kwargs.get('filename', args[0])}.lock"
    
    def _open(self):
        """Open the file with exclusive creation to avoid race conditions"""
        return open(self.baseFilename, self.mode)
    
    def doRollover(self):
        """Use file locking to safely rotate logs across processes"""
        lock_path = str(self.lock_file)
        try:
            # Use portalocker with a file path, not a file object
            with portalocker.Lock(lock_path, 'w', timeout=10):
                super().doRollover()
        except (portalocker.LockException, IOError, OSError) as e:
            # If locking fails, try without locking
            print(f"Warning: Lock failed during log rotation: {e}")
            super().doRollover()
    
    def emit(self, record):
        import sys # Import here to avoid circular imports

        """Thread and process-safe emit with file locking"""
        # So replaced with the follwoing 2 if statements. ones.....

        # Add worker_id attribute to the record
        if not hasattr(record, 'worker_id'):
            record.worker_id = WORKER_ID
                    
        # Add request info if available
        if not hasattr(record, 'request_id'):
            if hasattr(thread_local, 'request_id'):
                record.request_id = thread_local.request_id
            else:
                record.request_id = '-'
        try:
            # Use portalocker with a file path, not a file object
            lock_path = str(self.lock_file)
            with portalocker.Lock(lock_path, 'w', timeout=5):
                super().emit(record)
        except (portalocker.LockException, IOError, OSError) as e:
            # If locking fails, still try to emit without lock
            try:
                super().emit(record)
            except Exception as e2:
                # Last resort - print to stderr
                print(f"Error emitting log record: {e2}", file=sys.stderr)

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

def get_logger(name=None):
    """Get a properly configured logger instance"""
    if name:
        logger = logging.getLogger(name)
    else:
        logger = logging.getLogger()
    
    # Ensure the logger has our filter
    has_worker_filter = False
    for filter in logger.filters:
        if isinstance(filter, WorkerInfoFilter):
            has_worker_filter = True
            break
    
    if not has_worker_filter:
        logger.addFilter(WorkerInfoFilter())
    
    return logger

def setup_logger():
    """Setup logging with proper configuration for multiple workers"""
    import sys  # Import here to avoid circular imports
    
    os.makedirs(LOG_FILE_DIR, exist_ok=True)
    
    # Get the root logger
    logger = logging.getLogger()
    
    # Check if the logger is already configured properly
    if logger.handlers:
        for handler in logger.handlers:
            # Check if our custom formatter is already there
            if hasattr(handler, 'formatter') and hasattr(handler.formatter, '_fmt'):
                if 'worker_id' in handler.formatter._fmt:
                    # Logger already set up, just ensure the filter is there
                    logger.addFilter(WorkerInfoFilter())
                    logger.debug(f"Logger already configured with {len(logger.handlers)} handlers. Skipping setup.")
                    return logger
        
        # No handler has our custom formatter, remove all handlers to reconfigure
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Load configuration from file
    config = load_log_config()
    
    # Set global level
    global_level = getattr(logging, config['global'], DEFAULT_LOG_LEVEL)
    logger.setLevel(global_level)
    
    # Create formatter with worker ID and request ID
    formatter = logging.Formatter(
        '[%(asctime)s] [W:%(worker_id)s] [R:%(request_id)s] [PID:%(process)d] '
        '%(levelname)s in %(module)s: %(message)s'
    )

    # Add worker ID filter to all log records
    logger.addFilter(WorkerInfoFilter())
    
    # File handler with safe rotation
    file_level = getattr(logging, config['file'], DEFAULT_LOG_FILE_LEVEL)
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        file_handler = SafeRotatingFileHandler(
            str(LOG_FILE),  # Convert to string for Windows compatibility
            maxBytes=5_000_000, 
            backupCount=3,
            delay=True  # Don't open the file until first emit
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file handler: {e}", file=sys.stderr)
    
    # Console handler
    try:
        console_level = getattr(logging, config['console'], DEFAULT_LOG_CONSOLE_LEVEL)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Error setting up console handler: {e}", file=sys.stderr)
    
    #too many output messaes DEBUG messates
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
    logging.getLogger('google.auth').setLevel(logging.WARNING)
    logging.getLogger('google_auth_httplib2').setLevel(logging.WARNING) # If using httplib2 transport
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('urllib3.util').setLevel(logging.WARNING)

    logger.info(f"Logger initialized for worker {WORKER_ID}")
    return logger

def update_log_level(global_level=None, handler_levels=None):
    """Update log levels and save to config file"""
    logger = get_logger()
    #logger.debug(f"update_log_level> {global_level}, {handler_levels}")
    
    # Load current config
    config = load_log_config()
    
    # Update global level if specified
    if global_level:
        level = getattr(logging, global_level.upper(), None)
        if isinstance(level, int):
            logger.setLevel(level)
            config['global'] = global_level.upper()
    
    # Update handler levels if specified
    if handler_levels:
        for handler in logger.handlers:
            if isinstance(handler, (SafeRotatingFileHandler, RotatingFileHandler)) and 'file' in handler_levels:
                level = getattr(logging, handler_levels['file'].upper(), None)
                if isinstance(level, int):
                    handler.setLevel(level)
                    config['file'] = handler_levels['file'].upper()
            elif isinstance(handler, logging.StreamHandler) and 'console' in handler_levels:
                level = getattr(logging, handler_levels['console'].upper(), None)
                if isinstance(level, int):
                    handler.setLevel(level)
                    config['console'] = handler_levels['console'].upper()
    
    # Save updated config
    save_log_config(config)
    
    logger.debug("Log levels updated and saved to config file")
    return get_log_levels()

def get_log_levels():
    """Get current log levels from the active logger"""
    logger = get_logger()
    #logger.debug("get_log_levels>")
    
    levels = {
        'global': logging.getLevelName(logger.level),
        'file': None,
        'console': None
    }
    
    for handler in logger.handlers:
        if isinstance(handler, (SafeRotatingFileHandler, RotatingFileHandler)):
            levels['file'] = logging.getLevelName(handler.level)
        elif isinstance(handler, logging.StreamHandler):
            levels['console'] = logging.getLevelName(handler.level)
    
    #logger.debug("get_log_levels<")
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

#############################
# Helper function to convert seconds to minutes.
#############################

def format_seconds(seconds):
    
    logger = get_logger()

    #logger.debug("format_seconds>")
    minutes = int(seconds // 60)
    sec = round(seconds % 60, 1)
    return f"{minutes}m {sec:.1f}s"

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
    logger = app.logger
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    default_config = {"max_featured_posts_on_home": 6} # Example defaults

    if env_mode == 'deploy':
        #logger.debug(f"Attempting to load global blog config from GCS.")
        blog_bucket_name =  BLOG_BUCKET_NAME
        bucket = get_gcs_bucket(blog_bucket_name)
        if not bucket:
            logger.error(f"Could not get GCS bucket '{blog_bucket_name}'.")
            return default_config # Or raise error

        blob = bucket.blob(str(BLOG_CONFIG_FILE_PATH))
        try:
            if blob.exists():
                config_content = blob.download_as_string()
                loaded_config = json.loads(config_content.decode('utf-8'))
                #logger.info(f"Successfully loaded global blog config from GCS: gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}")
                return loaded_config
            else:
                logger.warning(f"Global blog config not found in GCS at gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}. Returning default.")
                return default_config
        except json.JSONDecodeError as jde:
            logger.error(f"Error decoding JSON from GCS config (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {jde}", exc_info=True)
            return default_config
        except Exception as e:
            logger.error(f"Error loading global blog config from GCS (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {e}", exc_info=True)
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
                logger.warning(f"Local global blog config file not found: {str(BLOG_CONFIG_FILE_PATH)}. Returning default.")
                return default_config
        except json.JSONDecodeError as jde:
            logger.error(f"Error decoding JSON from local config file '{str(BLOG_CONFIG_FILE_PATH)}': {jde}", exc_info=True)
            return default_config
        except IOError as ioe:
            logger.error(f"IOError reading local config file '{str(BLOG_CONFIG_FILE_PATH)}': {ioe}", exc_info=True)
            return default_config
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error loading local config file '{str(BLOG_CONFIG_FILE_PATH)}': {e}", exc_info=True)
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
            logger.error(f"Could not get GCS bucket '{blog_bucket_name}' for save.")
            return False

        blob = bucket.blob(str(BLOG_CONFIG_FILE_PATH))
        try:
            json_string = json.dumps(config_data, indent=4)
            blob.upload_from_string(json_string, content_type='application/json')
            logger.info(f"Successfully saved global blog config to GCS: gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}")
            return True
        except Exception as e:
            logger.error(f"Error saving global blog config to GCS (gs://{bucket.name}/{str(BLOG_CONFIG_FILE_PATH)}): {e}", exc_info=True)
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
            logger.error(f"IOError writing local config file '{str(BLOG_CONFIG_FILE_PATH)}': {ioe}", exc_info=True)
            return False
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error saving local config file '{str(BLOG_CONFIG_FILE_PATH)}': {e}", exc_info=True)
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
        logger.error(f"Cannot create thumbnail for {original_path}: {e}")
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
                logger.warning(f"Thumbnail creation failed for {original_filename} but original was saved.")
            return original_filename
        except Exception as e:
            logger.error(f"Error saving image {original_filename} or its thumbnail: {e}")
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
        logger.error(f"No image file provided.")
        return None

    original_filename = secure_filename(image_file_storage.filename)
    if not allowed_file(original_filename):
        logger.error(f"File type not allowed: {original_filename}")
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
        logger.error(f"Could not get GCS bucket.")
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
            logger.error(f"Error creating/uploading thumbnail for {original_filename}: {e_thumb}", exc_info=True)
            # Decide on error handling: proceed without thumbnail, or fail operation?
            # For now, let's consider it a partial success if original uploaded, but log error.
            # If thumbnail is critical, you might want to delete the original_blob and return None here.
            # original_blob.delete() # Cleanup if thumbnail is mandatory
            # return None
            pass # Original image still uploaded

        return final_gcs_base_filename # Return the base name of the original uploaded image

    except Exception as e:
        logger.error(f"Error during image upload process for {original_filename}: {e}", exc_info=True)
        # Potentially try to delete any partially uploaded files if a multi-step process fails
        try:
            if 'original_blob' in locals() and original_blob.exists():
                 original_blob.delete()
        except Exception as e_cleanup:
            logger.error(f"Error during cleanup of original blob: {e_cleanup}")
        try:
            if 'thumbnail_blob' in locals() and thumbnail_blob.exists():
                 thumbnail_blob.delete()
        except Exception as e_cleanup_thumb:
            logger.error(f"Error during cleanup of thumbnail blob: {e_cleanup_thumb}")

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
        logger.error(f"Error deleting image files for {image_filename} in {post_slug}: {e}")


import os
from google.cloud import storage
from flask import current_app as app # Or your logger

# Assume BLOG_BUCKET_NAME is defined (e.g., from os.environ)
# Assume THUMBNAIL_PREFIX is defined (e.g., THUMBNAIL_PREFIX = "thumb_")
# Assume get_gcs_bucket(bucket_name_str) helper function is defined and works

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
        logger.error(f"Slug or original_image_filename not provided.")
        return False

    if original_image_filename.startswith(os.environ.get("THUMBNAIL_PREFIX", "thumb_")):
        logger.warning(
            f"'{original_image_filename}' appears to be a thumbnail name. "
            "This function expects the original image filename to derive both paths. "
            "Proceeding, but ensure calling code provides the original filename."
        )
        # Optionally, you could try to derive the original name, but it's better if the caller is correct.
        # original_image_filename = original_image_filename[len(os.environ.get("THUMBNAIL_PREFIX", "thumb_")):]


    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket:
        logger.error(f"Could not get GCS bucket '{blog_bucket_name}'.")
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
            logger.error(f"Error deleting {log_name} gs://{bucket.name}/{gcs_path}: {e}", exc_info=True)
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
        logger.error(f"Could not get GCS bucket '{blog_bucket_name}'.")
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
            logger.warning(f"Post config not found in GCS: gs://{bucket.name}/{config_blob_path}")
            return None
    except json.JSONDecodeError as jde:
        logger.error(f"Error decoding JSON for slug '{slug}' from GCS (gs://{bucket.name}/{config_blob_path}): {jde}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error fetching post config for slug '{slug}' from GCS (gs://{bucket.name}/{config_blob_path}): {e}", exc_info=True)
        return None

def save_post_config_to_gcs(slug, post_data):
    """Saves the post_data dictionary ascontent.json for a slug in GCS."""
    logger = app.logger
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
        logger.error(f"Error saving post config for '{slug}' to GCS: {e}", exc_info=True)
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
            logger.error(f"get_all_posts: Could not get GCS bucket '{blog_bucket_name}'.")
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
            logger.error(f"get_all_posts: Local blog data directory not found: {LOCAL_BLOG_DATA_DIR}")
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
                        logger.error(f"get_all_posts: Error reading local post '{slug_folder_name}': {e}", exc_info=True)
    
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
            logger.error(f"get_all_posts: Error sorting posts by '{use_sort_key}': {e_sort}", exc_info=True)
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
                logger.error(f"get_post: Failed to save updated view count for '{slug}' to GCS.")
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
                logger.error(f"get_post: Error reading/updating local post '{slug}': {e}", exc_info=True)
                post_data = None # Ensure post_data is None on error
        # --- End of local file logic ---

    if not post_data:
        logger.warning(f"get_post: Post '{slug}' not found in mode '{env_mode}'.")
        return None

    # Convert date strings to datetime objects if your templates expect them
    # This should ideally be done consistently or handled by template filters
    # for key in ['created_at', 'updated_at', 'published_at']:
    #     if post_data.get(key):
    #         try:
    #             post_data[key] = datetime.fromisoformat(post_data[key].replace("Z", "+00:00"))
    #         except (ValueError, TypeError):
    #             logger.warning(f"get_post: Could not parse date string for '{key}' in post '{slug}'.")
    #             pass # Keep as string if parsing fails

    return post_data

def get_static_page_lastmod(template_name):
    logger = get_logger()
    try:
        filepath = os.path.join(TEMPLATE_FOLDER, template_name)
        if os.path.exists(filepath):
            mod_time = os.path.getmtime(filepath)
            return datetime.fromtimestamp.fromtimestamp(mod_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception as e:
        logger.error(f"Error getting lastmod for {template_name}: {e}")
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
            logger.warning(f"Could not parse datetime string for sitemap: {iso_string}")
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
        logger.error("GCS client not initialized.")
        return None
    return storage_client.bucket(bucket_name)


def list_blog_slugs_from_gcs(gcs_object_prefix=''): # Renamed for clarity from the method's 'prefix'
    logger = get_logger()
    slugs = set()
    log_prefix_func = "LIST_GCS_SLUGS_V1" # For this function's logs

    #logger.info(f"{log_prefix_func} :: Listing slugs with GCS object prefix: '{gcs_object_prefix}'")
    
    bucket = get_gcs_bucket(BLOG_BUCKET_NAME) # Ensure BLOG_BUCKET_NAME is accessible
    if not bucket:
        logger.error(f"{log_prefix_func} :: Bucket not available.")
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
        logger.error(f"{log_prefix_func} :: Error during bucket.list_blobs or iteration: {e_list}", exc_info=True)
        return list(slugs) # Return empty list on error

    #logger.info(f"{log_prefix_func} :: Returning {len(slugs)} slugs: {slugs if len(slugs) < 10 else str(list(slugs)[:10]) + '...'}")
    return list(slugs)

# In rl_data_gcs.py
def check_if_post_slug_exists_in_gcs(slug_to_check):
    logger = get_logger()
    
    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name) # Your existing helper
    if not bucket:
        logger.error(f"Could not get GCS bucket for slug check.")
        return True # Fail safe

    # Check for the existence of the content.json file for that slug
    config_blob_path = f"{slug_to_check}/content.json"
    blob = bucket.blob(config_blob_path)
    
    try:
        if blob.exists():
            #logger.info(f"Slug '{slug_to_check}' (content.json) FOUND in GCS.")
            return True
    except Exception as e:
        logger.error(f"Error checking GCS for slug '{slug_to_check}': {e}", exc_info=True)
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
        logger.error(f"Error saving post {slug} to GCS: {e}")
        return False



def get_blog_image_url_from_gcs(slug, filename):
    logger = get_logger()
    
    #try:
    #    logger.info(f" :: For {str(BLOG_BLOB_DIR)}/{slug}/{filename}. GCS Lib: {google.cloud.storage.__version__}, GAuth Lib: {google.auth.__version__}")
    #except Exception: pass # Best effort logging

    bucket = get_gcs_bucket(BLOG_BUCKET_NAME)
    if not bucket:
        logger.error(f"Failed to get GCS bucket object for '{BLOG_BUCKET_NAME}'.")
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
        logger.error(f" :: Failed to create iam.Signer: {e_iam_signer}", exc_info=True)
        return None # Cannot proceed if iam.Signer creation fails

    if not signing_credentials:
        logger.error(f" :: No valid signing credentials could be established.")
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
         logger.error(f" :: AttributeError (likely 'need private key') with '{credentials_method_used}': {ae}", exc_info=True)
         if isinstance(signing_credentials, google_auth_iam.Signer):
             logger.error(f" :: This confirms the issue: iam.Signer passed to 'credentials' kwarg is not being handled as expected by GCS lib {google.cloud.storage.__version__} when backed by token-based credentials.")
         return None
    except google.auth.exceptions.RefreshError as re: # For ADC/metadata issues if iam.Signer fails during its own auth
        logger.error(f" :: Google Auth RefreshError with '{credentials_method_used}': {re}", exc_info=True)
        return None
    except Exception as e: # Catch-all for other unexpected errors
        logger.error(f" :: General error generating signed URL with '{credentials_method_used}': {e}", exc_info=True)
        return None


def delete_blog_post_from_gcs(slug):
    """
    Deletes all GCS objects associated with a blog post slug
    under the configured BLOG_BLOB_DIR in the BLOG_BUCKET_NAME.
    Effectively removes the "slug directory" and its contents.
    """
    logger = get_logger()

    if not slug:
        logger.error(f"Slug not provided for deletion.")
        return False

    blog_bucket_name = BLOG_BUCKET_NAME
    bucket = get_gcs_bucket(blog_bucket_name)
    if not bucket:
        logger.error(f"Could not get GCS bucket '{blog_bucket_name}'.")
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
            logger.error(f"Failed to delete blob gs://{bucket.name}/{blob_item.name}: {e}", exc_info=True)
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
            logger.error(f"Error deleting image {path_to_delete} from GCS for post {slug}: {e}")

    if errors_encountered:
        logger.warning(f"Finished deletion attempt for prefix 'gs://{bucket.name}/{prefix_to_delete}' with errors. Deleted {deleted_count} objects.")
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
            logger.error(f"Error deleting image {path_to_delete} from GCS for post {slug}: {e}")
    return deleted_any

import os
import json
from pathlib import Path # For consistency if LOCAL_BLOG_DATA_DIR is Path
from google.cloud import storage # Only if you intend to initialize client here, otherwise not needed
from flask import current_app as app # Or your get_logger and how you access config

def sync_local_blogs_to_gcs():
    """
    Synchronizes blog posts from the local directory to GCS.
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
        logger.error(f"Failed to list slugs from GCS: {e_gcs_list}", exc_info=True)
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
                            #logger.warning(f"Slug in '{config_file_name}' ('{post_data.get('slug')}') for '{slug_to_sync}' doesn't match folder. Using folder name.")
                            post_data['slug'] = slug_to_sync 
                        
                        # save_post_config_to_gcs should handle blog_gcs_base_prefix internally
                        if save_post_config_to_gcs(slug_to_sync, post_data):
                            logger.info(f"Synced '{config_file_name}' for '{slug_to_sync}' to GCS.")
                            
                            local_images_path = local_post_full_path / 'images'
                            if local_images_path.exists() and local_images_path.is_dir():
                                images_synced_for_this_post = 0
                                bucket_for_img_upload = get_gcs_bucket(blog_bucket_name_from_env) # Get bucket once per post
                                if not bucket_for_img_upload:
                                    logger.error(f"Could not get GCS bucket for image upload of '{slug_to_sync}'. Skipping image sync for this post.")
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
                                                logger.error(f"Failed to upload image '{img_filename}' for '{slug_to_sync}': {e_img}", exc_info=True)
                                                current_post_fully_synced = False
                                    #logger.info(f"For post '{slug_to_sync}', attempted to sync {images_synced_for_this_post} images.")
                            else:
                                logger.info(f"No 'images' directory found for local post '{slug_to_sync}'.")
                        else:
                             logger.error(f"Failed to save '{config_file_name}' for '{slug_to_sync}' to GCS.")
                             current_post_fully_synced = False
                        
                        if current_post_fully_synced:
                            synced_this_run_count += 1
                        else:
                            failed_this_run_slugs.append(slug_to_sync)

                    except json.JSONDecodeError as jde:
                        logger.error(f"Error decoding JSON from '{config_file_local_path}': {jde}", exc_info=True)
                        failed_this_run_slugs.append(slug_to_sync)
                    except Exception as e_sync_post:
                        logger.error(f"General error syncing post '{slug_to_sync}': {e_sync_post}", exc_info=True)
                        failed_this_run_slugs.append(slug_to_sync)
                else:
                    logger.warning(f"'{config_file_name}' not found for local post '{slug_to_sync}'. Skipping sync.")
                    # Not necessarily a failure of the overall sync process, just this item.
                    # You could add it to a list of "skipped_no_config_slugs" if needed.
            else:
                #logger.debug(f"Post '{slug_to_sync}' already exists in GCS. Skipping sync.")
                skipped_this_run_count += 1
        # else: item is not a directory
    
    final_message = f"Sync complete. New posts synced: {synced_this_run_count}. Posts skipped (already in GCS): {skipped_this_run_count}. Posts failed to sync fully: {len(failed_this_run_slugs)}."
    logger.info(f"{final_message}")
    if failed_this_run_slugs:
        logger.warning(f"Slugs that failed to sync completely: {failed_this_run_slugs}")
        return {"status": "partial_success", "message": final_message, "synced": synced_this_run_count, "failed": len(failed_this_run_slugs), "skipped": skipped_this_run_count}
    
    return {"status": "success", "message": final_message, "synced": synced_this_run_count, "failed": 0, "skipped": skipped_this_run_count}
