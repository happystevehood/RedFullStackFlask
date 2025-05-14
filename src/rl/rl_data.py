import os
from pathlib import Path
import logging

import os
import uuid
import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import portalocker  # Cross-platform file locking

from flask import g, render_template as flask_render_template

import rl.rl_data as rl_data 

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

# This data should not be served to the user
LOG_FILE_DIR      = Path('store') / 'logs'
LOG_FILE          = LOG_FILE_DIR / 'activity.log'
LOG_CONFIG_FILE   = LOG_FILE_DIR / 'log_config.json'

CSV_FEEDBACK_DIR  = Path('store') / 'feedback'

ENV_PROD_FILENAME = '.env.production'
ENV_PROD_FILE = Path('.') / ENV_PROD_FILENAME
ENV_DEVEL_FILENAME = '.env.development'
ENV_DEVEL_FILE = Path('.') / ENV_DEVEL_FILENAME


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
         
        #print(f"filter: {record.getMessage()}")

        # Add worker_id attribute to the record
        if not hasattr(record, 'worker_id'):
            record.worker_id = WORKER_ID
                    
        # Add request info if available
        if not hasattr(record, 'request_id'):
            if hasattr(thread_local, 'request_id'):
                record.request_id = thread_local.request_id
            else:
                record.request_id = '-'

        #print(f"record.worker_id: {record.worker_id} {record.request_id} {record.getMessage()}")

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
        # The original code seems to have a problem with non local moduls
        ## Quick check for log level before trying to lock
        ##if not self.filter(record):
        ##    print(f"if not self.filter(record)") 
        ##    return
        
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
                #print(f"super().emit({record})") 
                super().emit(record)
        except (portalocker.LockException, IOError, OSError) as e:
            # If locking fails, still try to emit without lock
            try:
                #print(f"!super().emit({record})") 
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
    
    #disable all those matplotlib.font_manager DEBUG messates
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

    logger.info(f"Logger initialized for worker {WORKER_ID}")
    return logger

def update_log_level(global_level=None, handler_levels=None):
    """Update log levels and save to config file"""
    logger = get_logger()
    logger.debug(f"update_log_level> {global_level}, {handler_levels}")
    
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
    logger.debug("get_log_levels>")
    
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
    
    logger.debug("get_log_levels<")
    return levels

#############################
# Non log based helper functions
#############################

def remove_files_from_directory(directory):
    """Removes all files within the specified directory, but leaves the directory untouched."""

    logger = get_logger()
    
    logger.debug("remove_files_from_directory> %s",str(directory))
    logger.debug("cwd %s",str(os.getcwd()))
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    logger.debug("remove_files_from_directory<")


def delete_generated_files():
    """Removes all data files generated here included competitor files"""

    logger = get_logger()
    logger.debug("delete_generated_files>")
    
    remove_files_from_directory(CSV_GENERIC_DIR);
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PDF_GENERIC_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 
    remove_files_from_directory(PNG_GENERIC_DIR);
    
    logger.debug("delete_generated_files<")

def delete_competitor_files():
    
    logger = get_logger()
    logger.debug("delete_competitor_files>")
    
    """Removes all competitor data files generated here"""
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PNG_COMP_DIR);
    
    logger.debug("delete_competitor_files<") 

#############################
# Helper function to convert seconds to minutes.
#############################

def format_seconds(seconds):
    
    logger = get_logger()

    logger.debug("format_seconds>")
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


# Example usage
#print(convert_to_standard_time("30:15.5"))      # Minutes:Seconds.Microseconds format -> "00:30:15.5"
#print(convert_to_standard_time("30:15.567"))    # Minutes:Seconds.Microseconds format -> "00:30:15.5"
#print(convert_to_standard_time("2:45:30"))      # Hours:Minutes:Seconds format -> "02:45:30.0"
#print(convert_to_standard_time("2:45:30.5"))    # Hours:Minutes:Seconds.Microseconds format -> "02:45:30.5"
#print(convert_to_standard_time("2:45:30.567"))  # Hours:Minutes:Seconds.Microseconds format -> "02:45:30.5"
#print(convert_to_standard_time("nan"))          # NaN value -> "00:00:00.0"
#print(convert_to_standard_time(None))           # None value -> "00:00:00.0"
#print(convert_to_standard_time(""))             # Empty string -> "00:00:00.0"