import csv
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from flask import session


# file sturcture 'constants'
# static - csv 	- input
#				- generic
#		 - pdf 	- generic
#				- comp
#		 - png	- generic
#				- comp

CSV_INPUT_DIR    = Path('static') / 'csv' / 'input'
CSV_GENERIC_DIR  = Path('static') / 'csv' / 'generic' 
CSV_FEEDBACK_DIR = Path('static') / 'csv' / 'feedback'
PDF_COMP_DIR     = Path('static') / 'pdf' / 'comp' 
PDF_GENERIC_DIR  = Path('static') / 'pdf' / 'generic' 
PNG_COMP_DIR     = Path('static') / 'png' / 'comp'
PNG_GENERIC_DIR  = Path('static') / 'png' / 'generic' 
PNG_HTML_DIR     = Path('static') / 'png' / 'html' 

LOG_FILE_DIR      = Path('logs') 
LOG_FILE          = LOG_FILE_DIR / 'activity.log'
DEFAULT_LOG_LEVEL = logging.DEBUG # Lowest - Anything below will be filtered out
DEFAULT_LOG_CONSOLE_LEVEL = logging.INFO # Middle - Anything will be written to console/terminal
DEFAULT_LOG_FILE_LEVEL = logging.WARNING # Highest - Anything above will be written to file

#The 2023 Events Lists
EVENTLIST23 =      [         'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']
EVENTLISTSTART23 = ['Start', 'Run','Bike','Sandbag Gauntlet','Battle Rope Pull','Farmer\'s Carry','Row','Deadball Burpee','Sled Push','Pendulum Shots','Agility Climber','Ski','The Mule']

#The 2024 Events Lists
EVENTLIST24 =      [         'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']
EVENTLISTSTART24 = ['Start', 'Run', 'Row', 'Deadball Burpee', 'Pendulum Shots', 'Bike', 'Sandbag Gauntlet', 'Battle Whip', 'Farmer\'s Carry', 'Agility Chamber', 'Ski', 'Mule', 'Sled Push Pull']

# Your data for filtering purposes
EVENT_DATA_LIST = [
    #2023
    ["MensSinglesCompetitive2023", "REDLINE Fitness Games '23 Mens Singles Comp.", "2023", "MENS", "SINGLES_COMPETITIVE", "KL"],
    ["WomensSinglesCompetitive2023", "REDLINE Fitness Games '23 Womens Singles Comp.", "2023", "WOMENS", "SINGLES_COMPETITIVE", "KL"],
    ["MensSinglesOpen2023", "REDLINE Fitness Games '23 Mens Singles Open", "2023", "MENS", "SINGLES_OPEN", "KL"],
    ["WomensSinglesOpen2023", "REDLINE Fitness Games '23 Womens Singles Open", "2023", "WOMENS", "SINGLES_OPEN", "KL"],
    ["MensDoubles2023", "REDLINE Fitness Games '23 Mens Doubles", "2023", "MENS", "DOUBLES", "KL"],
    ["WomensDoubles2023", "REDLINE Fitness Games '23 Womens Doubles", "2023", "WOMENS", "DOUBLES", "KL"],
    ["MixedDoubles2023", "REDLINE Fitness Games '23 Mixed Doubles", "2023", "MIXED", "DOUBLES", "KL"],
    ["TeamRelayMen2023", "REDLINE Fitness Games '23 Mens Team Relay", "2023", "MENS", "RELAY", "KL"],
    ["TeamRelayWomen2023", "REDLINE Fitness Games '23 Womens Team Relay", "2023", "WOMENS", "RELAY", "KL"],
    ["TeamRelayMixed2023", "REDLINE Fitness Games '23 Mixed Team Relay", "2023", "MIXED", "RELAY", "KL"],
    #2024
    ["MensSinglesCompetitive2024", "REDLINE Fitness Games '24 Mens Singles Comp.", "2024", "MENS", "SINGLES_COMPETITIVE", "KL"],
    ["WomensSinglesCompetitive2024", "REDLINE Fitness Games '24 Womens Singles Comp.", "2024", "WOMENS", "SINGLES_COMPETITIVE", "KL"],
    ["MensSinglesOpen2024", "REDLINE Fitness Games '24 Mens Singles Open", "2024", "MENS", "SINGLES_OPEN", "KL"],
    ["WomensSinglesOpen2024", "REDLINE Fitness Games '24 Womens Singles Open", "2024", "WOMENS", "SINGLES_OPEN", "KL"],
    ["MensDoubles2024", "REDLINE Fitness Games '24 Mens Doubles", "2024", "MENS", "DOUBLES", "KL"],
    ["WomensDoubles2024", "REDLINE Fitness Games '24 Womens Doubles", "2024", "WOMENS", "DOUBLES", "KL"],
    ["MixedDoubles2024", "REDLINE Fitness Games '24 Mixed Doubles", "2024", "MIXED", "DOUBLES", "KL"],
    ["TeamRelayMen2024", "REDLINE Fitness Games '24 Mens Team Relay", "2024", "MENS", "RELAY", "KL"],
    ["TeamRelayWomen2024", "REDLINE Fitness Games '24 Womens Team Relay", "2024", "WOMENS", "RELAY", "KL"],
    ["TeamRelayMixed2024", "REDLINE Fitness Games '24 Mixed Team Relay", "2024", "MIXED", "RELAY", "KL"],
]



def init_filepaths(dummy):

    print(CSV_INPUT_DIR)

    return True


# helper function
def remove_files_from_directory(directory):
    """Removes all files within the specified directory, but leaves the directory untouched."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)


def delete_generated_files():
    """Removes all data files generated here included competitor files"""
    remove_files_from_directory(CSV_GENERIC_DIR);
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PDF_GENERIC_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 
    remove_files_from_directory(PNG_GENERIC_DIR);

def delete_competitor_files():
    """Removes all competitor data files generated here"""
    remove_files_from_directory(PDF_COMP_DIR); 
    remove_files_from_directory(PNG_COMP_DIR); 

#############################
# Helper function to convert seconds to minutes.
#############################

def format_seconds(seconds):
    minutes = int(seconds // 60)
    sec = round(seconds % 60, 1)
    return f"{minutes}m {sec:.1f}s"


def setup_logger():
    os.makedirs(LOG_FILE_DIR, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(DEFAULT_LOG_LEVEL)  # Global level

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')

    # File handler
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        # File handler
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
        file_handler.setLevel(DEFAULT_LOG_FILE_LEVEL)  # Can customize
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # console handler
    if not any(type(h) is logging.StreamHandler for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(DEFAULT_LOG_CONSOLE_LEVEL)
        console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(console_handler)

    print("Configured log handlers:",logger.handlers)
    for handler in logger.handlers:
        print(f"Handler: {type(handler)}, Level: {logging.getLevelName(handler.level)}")

    logger.debug("Logger debug message test")
    logger.info("Logger info message test")
    logger.warning("Logger warning message test")
    logger.error("Logger error message test")
    logger.critical("Logger critical message test")


def update_log_level(global_level=None, handler_levels=None):
    logger = logging.getLogger()
    if global_level:
        level = getattr(logging, global_level.upper(), None)
        if isinstance(level, int):
            logger.setLevel(level)

    if handler_levels:
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler) and 'file' in handler_levels:
                level = getattr(logging, handler_levels['file'].upper(), None)
                if isinstance(level, int):
                    handler.setLevel(level)
            elif isinstance(handler, logging.StreamHandler) and 'console' in handler_levels:
                level = getattr(logging, handler_levels['console'].upper(), None)
                if isinstance(level, int):
                    handler.setLevel(level)

def get_log_levels():
    logger = logging.getLogger()
    levels = {
        'global': logging.getLevelName(logger.level),
        'file': None,
        'console': None
    }
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            levels['file'] = logging.getLevelName(handler.level)
        elif isinstance(handler, logging.StreamHandler):
            levels['console'] = logging.getLevelName(handler.level)
    return levels
