import csv
from pathlib import Path
import logging

import rl.rl_data


#call per module.
logger = logging.getLogger()

# Find competitor function
def find_competitor(competitor, callback):
    matches = []
    matchcount = 0
    
    logger.debug(f"find_competitor called {competitor}")

    #for each element in EVENT_DATA_LIST
    for element in rl.rl_data.EVENT_DATA_LIST:
        #equivalent to the following filepath = './data/input/' + filename
        filepath = Path(rl.rl_data.CSV_INPUT_DIR) / Path(element[0] + '.csv')

        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    # Check if the name field has a partial match with competitor (case insensitive)
                    if competitor.upper() in row['Name'].upper():

                        match = {
                            'competitor': row['Name'],
                            'description': element[1],  
                            'race_no': row['Race No'],
                            'event': element[0]  # could be extracted from filename
                        }
                        logger.debug(f"found a match {match}")
                        matches.append(match)
                        matchcount += 1

                        if matchcount >= 50:
                            #leave early
                            logger.debug(f'reached {matchcount} matches' )
                            callback(competitor, matches)
                            return 
                           

        except Exception as e:
            logger.critical(f"Error occurred: {e}")   

    #only callback once all the files have been checked
    callback(competitor, matches)