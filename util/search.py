import csv
import os
from pathlib import Path

from visualisation.redline_vis import myFileLists 
import util.data

# Find competitor function
def find_competitor(competitor, callback):
    matches = []
    matchcount = 0
    
    #print('find_competitor called', competitor)

    #for each element in myFileLists
    for element in myFileLists:
        #equivalent to the following filepath = './data/input/' + filename
        filepath = Path(util.data.CSV_INPUT_DIR) / Path(element[0] + '.csv')

        try:
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    # Check if the name field has a partial match with competitor (case insensitive)
                    if competitor.upper() in row['Name'].upper():
                        #print('found a match', row['Name'])

                        match = {
                            'competitor': row['Name'],
                            'description': element[1],  
                            'race_no': row['Race No'],
                            'event': element[0]  # could be extracted from filename
                        }
                        #print('found a match', match)
                        matches.append(match)
                        matchcount += 1

                        if matchcount >= 100:
                            #leave early
                            print(f'reached 100 matches' )
                            callback(competitor, matches)
                            return 
                            

                #print(f"Parsed {reader.line_num} rows")

        except Exception as e:
            print(f"Error occurred: {e}")

    #only callback once all the files have been checked
    callback(competitor, matches)