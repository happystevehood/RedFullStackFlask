# This module was developed to create visualisation of the results below.
#
# 2023 Results
# 2023 redline fitness games scraped from - Day 1 results.
# https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1216
# 2023 redline fitness games scraped from - Day 2 results.
# https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1217
# 
# 2024
# 2024 redline fitness games scraped from - Day 1 results.
# https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1251
# 2024 redline fitness games scraped from - Day 2 results.
# https://runnersunite.racetecresults.com/results.aspx?CId=16634&RId=1252
#
# Results from abvove were cut and paste into excel file and saved as csv files per competition.
#
# This intial development is based on the format for 2023, with 2024 format
#

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.lines as mlines
import seaborn as sns

from datetime import datetime, timedelta

#pdf creation
import os, pymupdf
from pathlib import Path
import re
from flask import session, url_for, render_template, jsonify

from slugify import slugify 

# local inclusion.
import rl.rl_data as rl_data
from rl.rl_dict import OUTPUT_CONFIGS


# Otherwise get this warning - UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail
mpl.use('agg')
 
 #############################
# Tidy df functions 
#############################
 
def prepare_data_for_processing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares a fitness games DataFrame for further processing using the provided
    helper functions for time string standardization.
    """
    df_processed = df.copy()
    
    runtimeVars = session.get('runtime', {})
    station_list = runtimeVars['StationList']

    # --- Step 1: Standardize common column names ---
    rename_map = {'Overall Pos': 'Pos', 'Net Pos': 'Pos', 'Net Cat Pos': 'Cat Pos'}
    df_processed.rename(columns=rename_map, inplace=True)
    df_processed = df_processed.drop(columns=['Fav', 'Share', 'Net Cat Pos (Net Gen Pos)', 'Net Gender Pos'], errors='ignore')

    # --- Step 2: Detect format and apply the correct transformation ---
    if 'Start' not in df_processed.columns:
        # ** CRUCIBLE FORMAT DETECTED (Durations) **
        print("--> Detected 'Crucible' format (durations). Applying full transformation...")

        # Check if the 'Status' column exists to avoid errors.
        if 'Status' in df_processed.columns:
            #print("Found 'Status' column. Filtering for 'Finished' entries...")
            original_row_count = len(df_processed)

            # 2. For each row, keep only the ones where the 'Status' is 'Finished'.
            #    We use .str.strip() to handle potential extra spaces like "Finished ".
            df_processed = df_processed[df_processed['Status'].str.strip() == 'Finished'].copy()

            # Provide feedback on how many rows were removed
            rows_removed = original_row_count - len(df_processed)
            #if rows_removed > 0:
            #    print(f"Removed {rows_removed} rows with a status other than 'Finished'.")

            # 3. At the end, delete the 'Status' column from the DataFrame.
            df_processed.drop(columns=['Status'], inplace=True)
            #print("Successfully removed the 'Status' column.")

        else:
            print("Warning: 'Status' column not found. No filtering was performed.")


        # 2a. Dynamically identify station columns
        df_processed.rename(columns={'Sled Push & Pull':'Sled Push Pull'},inplace=True)
        df_processed.rename(columns={'Ski Erg':'Ski'},inplace=True)
        df_processed.rename(columns={'Row Erg':'Row'},inplace=True)
        df_processed.rename(columns={'Bike Erg':'Bike'},inplace=True)
        df_processed.rename(columns={'Erg Bike':'Bike'},inplace=True)
        
        known_metadata_cols = ['Name', 'Race No', 'Pos', 'Cat Pos', 'Net Time', 'Category', 'Wave', 'Gender', 'Team', 'Member1', 'Member2', 'Member3', 'Member4']
        station_cols = [col for col in df_processed.columns if col not in known_metadata_cols]
        
        # 2b. Standardize all time strings, then convert to seconds for calculation
        df_processed['Net Time'] = df_processed['Net Time'].apply(rl_data.convert_to_standard_time).apply(rl_data.standard_time_str_to_seconds)
        for col in station_cols:
            df_processed[col] = df_processed[col].apply(rl_data.convert_to_standard_time).apply(rl_data.standard_time_str_to_seconds)
        
        # 2c. Add 'Start' and 'Time Adj'
        df_processed['Start'] = 0.0
        if 'Time Adj' not in df_processed.columns:
             df_processed['Time Adj'] = 0.0
             df_processed['Time Adj'] = df_processed['Time Adj'].apply(rl_data.seconds_to_standard_time_str)

        # 2e. iteratively finds rows with missing station times and corrects the
        # subsequent station's time, which is incorrectly recorded as an elapsed time.
        
        # ### FIX: Convert all station columns to 'object' dtype ###
        # This prevents the FutureWarning by ensuring the columns can accept string values
        # like '00:00:00' even if they were initially inferred as float64 due to being empty.
        for station_name in station_list:
            if station_name in df_processed.columns:
                df_processed[station_name] = df_processed[station_name].astype(object)
        # ### END FIX ###

        # Iterate over each row
        for index, row in df_processed.iterrows():
            # --- DEBUGGING: Add a loop counter and limit ---
            loop_count = 0
            loop_limit = 20 # A safe limit, as there are only ~12 stations

            while True:
                loop_count += 1
                if loop_count > loop_limit:
                    #print(f"!!! Loop limit exceeded for row index {index}. Breaking to prevent infinite loop. !!!")
                    #print("--- FINAL ROW STATE ---")
                    #print(row[station_list])
                    break

                blank_info = rl_data.find_first_blank_column(row, station_list[:-1])
                
                # If no blank is found, this row is clean, so we can exit the while loop
                if blank_info is None:
                    # If this is the first pass, the row was already clean.
                    if loop_count == 1:
                        pass # Just move on
                    #else:
                    #    print(f"--- Row {index} successfully cleaned. ---")
                    break
                
                # --- DEBUGGING: Print the state at the start of the loop ---
                #print(f"\n--- Processing Row Index: {index} (Attempt #{loop_count}) ---")
                #print(f"Found blank column: {blank_info}")

                blank_col_index, blank_col_name = blank_info
                elapsed_time_col_name = station_list[blank_col_index + 1]
                elapsed_seconds = row.get(elapsed_time_col_name, '') # Use .get for safety

                if pd.notna(elapsed_seconds) and elapsed_seconds != '':
                    #print(f"  > row: {row}")
                    previous_station_cols = station_list[:blank_col_index]
                    sum_of_previous_seconds = rl_data.calculate_row_sum(row, previous_station_cols)
                    
                    correct_duration_seconds = elapsed_seconds - sum_of_previous_seconds
                    
                    # --- DEBUGGING: Print calculations ---
                    #print(f"  > Previous stations columns: {previous_station_cols}")
                    #print(f"  > Previous stations sum: {sum_of_previous_seconds}s")
                    #print(f"  > Incorrect elapsed time in '{elapsed_time_col_name}': {elapsed_seconds}s ")
                    #
                    # print(f"  > Calculated correct duration: {correct_duration_seconds}s ")

                    df_processed.at[index, elapsed_time_col_name] = correct_duration_seconds
                #else:
                    #print(f"  > The next column '{elapsed_time_col_name}' is also blank. Skipping correction for it.")

                # Fill the original blank cell
                df_processed.at[index, blank_col_name] = 0.0
                #print(f"  > Filled '{blank_col_name}' with '0.0'.")
                
                # Update the 'row' variable with the changes
                row = df_processed.loc[index]
            
        # 2e. Calculate cumulative sum of durations IN SECONDS
        
        # 1. Create a temporary DataFrame containing only numerical seconds.
        #    We use .apply() to run your time_str_to_seconds function on every cell.
        df_seconds = df_processed[station_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

        # 2. Now, perform the cumsum() operation on this purely numerical DataFrame.
        #    This will now work correctly.
        df_cumulative_seconds = df_seconds.cumsum(axis=1)

        # 2f. Convert cumulative seconds and other time fields back to STANDARD STRING format
        df_processed['Start'] = df_processed['Start'].apply(rl_data.seconds_to_standard_time_str)
        df_processed['Net Time'] = df_processed['Net Time'].apply(rl_data.seconds_to_standard_time_str)
        for col in station_cols:
             df_processed[col] = df_cumulative_seconds[col].apply(rl_data.seconds_to_standard_time_str)
        
        #print(f"--> Transformation complete. Data is now in cumulative timestamp format.")

    else:
        # ** REDLINE FORMAT DETECTED (Cumulative Timestamps) **
        print("--> Detected 'Redline' format (cumulative timestamps). Applying standardization...")
        
        # 2a. Normalize legacy Redline names
        redline_rename_map = {
            'Sled Push & Pull': 'Sled Push Pull', 'Ski Erg': 'Ski', 'Row Erg': 'Row', 'Bike Erg': 'Bike',
            'Battle Rope Whips': 'Battle Whip', 'SandbagGauntlet': 'Sandbag Gauntlet',
            'Deadball Burpee Over Target': 'Deadball Burpee',
        }
        df_processed.rename(columns=redline_rename_map, inplace=True)

        # 2b. Ensure all timestamp fields are in the standard format
        known_metadata_cols = ['Name', 'Race No', 'Pos', 'Cat Pos', 'Net Time', 'Category', 'Wave', 'Gender', 'Time Adj', 'Team', 'Member1', 'Member2', 'Member3', 'Member4']
        timestamp_cols = [col for col in df_processed.columns if col not in known_metadata_cols] + ['Net Time']
        
        for col in timestamp_cols:
             if col in df_processed.columns:
                  df_processed[col] = df_processed[col].apply(rl_data.convert_to_standard_time)

        print("--> Standardization complete.")

    return df_processed
 
#############################
# Tidy df functions 
#############################
def tidyTheData(df, filename):

    logger = rl_data.get_logger()
    runtimeVars = session.get('runtime', {})

    #Clean a few uneeded columns first.
    if 'Fav' in df.columns:
        df.drop('Fav', axis=1, inplace = True)

    if 'Share' in df.columns:
        df.drop('Share', axis=1, inplace = True)
        
    if 'Net Cat Pos (Net Gen Pos)' in df.columns:
        df.drop('Net Cat Pos (Net Gen Pos)', axis=1, inplace = True)

    if 'Net Gender Pos' in df.columns:
        df.drop('Net Gender Pos', axis=1, inplace = True)

    #Rename Columns so consistent across years....etc
    df.rename(columns={'Net Pos':'Pos'},inplace=True)
    df.rename(columns={'Net Cat Pos':'Cat Pos'},inplace=True)
    df.rename(columns={'Sled Push & Pull':'Sled Push Pull'},inplace=True)
    df.rename(columns={'Ski Erg':'Ski'},inplace=True)
    df.rename(columns={'Row Erg':'Row'},inplace=True)
    df.rename(columns={'Bike Erg':'Bike'},inplace=True)
    df.rename(columns={'Erg Bike':'Bike'},inplace=True)
    df.rename(columns={'Battle Rope Whips':'Battle Whip'},inplace=True)
    df.rename(columns={'SandbagGauntlet':'Sandbag Gauntlet'},inplace=True)
    df.rename(columns={'Deadball Burpee Over Target':'Deadball Burpee'},inplace=True)

    #in 2023 doubles "The Mule" Column is called "Finish Column"
    df.rename(columns={'Finish':'The Mule'},inplace=True)

    #for 2025
    actual_station_names = runtimeVars['StationList']
    for station_name in actual_station_names:
        station_name_duration = station_name + ' Workout Time' 
        if station_name_duration in df.columns:
            df.drop(station_name_duration, axis=1, inplace = True)
            #print(f"dropped column: {station_name_duration}")
        #else:
            #print(f"Column {station_name_duration} not found in DataFrame, cannot drop it.")
 
    #name_column = df.pop('Name')  # Remove the Name column and store it
    #df.insert(1, 'Name', name_column)  # Insert it at position 2 (leftmost)

    #make a copy of original data frame during tidying process.
    dforig = df.copy(deep=True)

    #add a  column to calculate the times based on sum of each event.
    df.insert(len(df.columns), 'Calc Time', 0.0)

    #Reset the CutOffEvent count value to 0
    #runtimeVars['StationCutOffCount'][:] = [0 for _ in runtimeVars['StationCutOffCount']]
       
    #actual_station_names = runtimeVars['StationList']
    #timestamp_cols = runtimeVars['StationListStart'] 
    
    #print(f"actual_station_names: {actual_station_names}")
    #print(f"timestamp_cols: {timestamp_cols}")
    
    #for i, station_name_for_duration in enumerate(actual_station_names):
    #    start_timestamp_col_name = timestamp_cols[i]
    #    end_timestamp_col_name = timestamp_cols[i+1]
        
    actual_station_names = runtimeVars['StationList']
    timestamp_cols = runtimeVars['StationListStart']     
    n = len(actual_station_names)

    for i in range(n - 1, -1, -1):  # Start at n-1, go down to 0 (exclusive -1), step by -1
        
        station_name_for_duration = actual_station_names[i]
        #what to do if final value is zero?
        if i != n - 1:
            station_end_name_for_duration = actual_station_names[i+1]
        start_timestamp_col_name = timestamp_cols[i]
        end_timestamp_col_name = timestamp_cols[i+1]
          
        #print(f"i: {i}")
        #print(f"station_name_for_duration: {station_name_for_duration}")
        #print(f"start_timestamp_col_name: {start_timestamp_col_name}")
        #print(f"end_timestamp_col_name: {end_timestamp_col_name}")

        #reorganise data such that each event a duration in reverse format
        for x in df.index:
            
            #if time format wrong, it causes excpetions.
            try:
                
                #print(f"x: {x}")

                end_time_str = rl_data.convert_to_standard_time(df.loc[x, end_timestamp_col_name])
                start_time_str = rl_data.convert_to_standard_time(df.loc[x, start_timestamp_col_name])

                #print(f"end_time_str: {end_time_str}, start_time_str: {start_time_str}")

                duration_seconds = timedelta.total_seconds(
                    datetime.strptime(end_time_str, "%H:%M:%S.%f") -
                    datetime.strptime(start_time_str, "%H:%M:%S.%f")
                )
                #print(f"duration_seconds: {duration_seconds}")
                
                df.loc[x, station_name_for_duration] = duration_seconds

                # ... (Your checks for < 20.0 and > 420.0 with correct indexing for StationCutOffCount[i]) ...
                if duration_seconds < 20.0:
                    logger.info(f"Removed Low value {filename} {x} {station_name_for_duration} {duration_seconds} {df.loc[x,'Pos']}")
                    #both the higher and lower stations should be 0! If finishing time is zero then we are all done, in a bad way.
                    df.loc[x,station_name_for_duration] = float("nan")
                    if i != n - 1:
                        df.loc[x,station_end_name_for_duration] = float("nan")
                    #df.drop(x, inplace=True)
                    continue 
                
                elif ((duration_seconds > 600.0 and runtimeVars['eventDataList'][2]=="2025") or 
                      (duration_seconds > 420.0 and runtimeVars['eventDataList'][2]!="2025")):
                          
                    if i < len(runtimeVars['StationCutOffCount']):
                         runtimeVars['StationCutOffCount'][i] = runtimeVars['StationCutOffCount'][i] + 1
                    else:
                        logger.warning(f"Index {i} out of bounds for StationCutOffCount (len {len(runtimeVars['StationCutOffCount'])})")

            except (ValueError):
                    #One of the values in not a string so write NaN to the value.
                    logger.info(f'ValueError {filename} {x} {station_name_for_duration}, {start_timestamp_col_name}, {end_timestamp_col_name}'  )
                    df.loc[x,station_name_for_duration] = float("nan")

            except (TypeError):
                    #One of the values in not a string so write NaN to the value.
                    logger.info(f'TypeError {filename} {x} {station_name_for_duration}, {start_timestamp_col_name}, {end_timestamp_col_name}'  )
                    df.loc[x,station_name_for_duration] = float("nan")
                    

    #Now I want to get the mean time of each event duration in seconds, so can create a ratio of 2 event times
    meanStationList = []
   
    # get the median time for each event.
    for event in runtimeVars['StationList']:
        meanStationList.append(df[event].mean())

    # now I need to search for 2 NaN"s side by side.

    # Index to last item
    MyIndex = len(runtimeVars['StationListStart']) - 1

    #iterate the event list in reverse order
    for event in runtimeVars['StationListStart'][::-1]:

        #Note Event = runtimeVars['StationListStart'][MyIndex] below, may be tidier ways to write

        #reorganise data such that each event a duration in reverse format
        for x in df.index:

            # do not check first element
            if MyIndex != 0:

                    #if two consecutive are non numbers. 
                    if (pd.isnull(df.loc[x,runtimeVars['StationListStart'][MyIndex]]) and pd.isnull(df.loc[x,runtimeVars['StationListStart'][MyIndex-1]])):
                        # then need to calculate the duration of two events.

                        #if time format wrong, it causes excpetions.
                        try: 

                            twoEventDuration = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,event]                                   ),"%H:%M:%S.%f") 
                                                                     - datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars['StationListStart'][MyIndex-2]]),"%H:%M:%S.%f"))
                            #change from 60 seconds to 90 seconds
                            if (twoEventDuration < 90.0):
                                logger.info(f"EventDurLow {filename} {x} {event} {twoEventDuration}")
                                #drop the row
                                df.drop(x, inplace = True)
                            else:        
                                df.loc[x,runtimeVars['StationListStart'][MyIndex-1]] = (twoEventDuration * meanStationList[MyIndex-2] )/(meanStationList[MyIndex-2] + meanStationList[MyIndex-1])
                                df.loc[x,runtimeVars['StationListStart'][MyIndex]]  = (twoEventDuration * meanStationList[MyIndex-1] )/(meanStationList[MyIndex-2] + meanStationList[MyIndex-1])

                        except (ValueError, TypeError):
                                #This will catch the competitors where NET time is "DNF" etc....

                                #Set Time values to None
                                df.loc[x,runtimeVars['StationListStart'][MyIndex-1]] = float("nan")
                                df.loc[x,runtimeVars['StationListStart'][MyIndex]] = float("nan")

                                #print(f"tidyTheData ValueError, TypeError: {x} {event} {MyIndex} {rl_data.convert_to_standard_time(dforig.loc[x,event])} {rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars['StationListStart'][MyIndex-2]])}")
                                
                    
        MyIndex = MyIndex - 1

    # convert Net Time Column to float in seconds.
    for x in df.index:

        #if time format wrong, it causes excpetions.
        try:

            df.loc[x,'Net Time'] =  timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,'Net Time']),"%H:%M:%S.%f") 
                                                          - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f"))
            
            df.loc[x,'Start']    =  timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,'Start'])   ,"%H:%M:%S.%f") 
                                                          - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f"))
                      
            #time Adjust format is the samve #added for 2025
            if ('Time Adj' in df.columns and pd.isna(df.loc[x, "Time Adj"]) == False):
                
                time_str = df.loc[x,"Time Adj"]
                multiplier = 1.0

                # Check for a sign and set the multiplier
                if time_str.startswith('-'):
                    multiplier = -1.0
                    time_str = time_str[1:]  # Remove the sign for parsing
                elif time_str.startswith('+'):
                    time_str = time_str[1:]  # Remove the sign for parsing
                
                #print(f"Time Adj 1: {df.loc[x,'Time Adj']}")
                timeAdj = df.loc[x,"Time Adj"].replace("+", "")
                df.loc[x,'Time Adj'] = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(time_str),"%H:%M:%S.%f") 
                                                             - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f")) * multiplier
            else:
                df.loc[x,'Time Adj'] = 0.0

            #if net time less than 10 minutes (used to be 6 minutes)
            if ((df.loc[x,'Net Time']) < 600.0):
                #print data...
                logger.info(f"Removed Low NetTime {filename} {x} {df.loc[x,'Net Time']} {df.loc[x,'Pos']}")
                #drop the row
                df.drop(x, inplace = True)
                # added as this can cause problems dur the next calculations below.
                continue
               
            #Reset Calculated time for this index
            calculatedNetTime = 0.0

            #iterate the event list in reverse order
            for event in runtimeVars['StationListStart']:
                #print(f"event in {x} {event}")
                calculatedNetTime = calculatedNetTime + df.loc[x,event] 
                
            if ('Time Adj' in df.columns and pd.isna(df.loc[x, "Time Adj"]) == False):
                calculatedNetTime = calculatedNetTime + df.loc[x,'Time Adj']    

            #Store the event time.
            df.loc[x,'Calc Time'] = calculatedNetTime    

            #if NetTime - Calculated time is more than 13 seconds
            if ((abs(df.loc[x,'Net Time'] - calculatedNetTime) > 13) and runtimeVars['eventDataList'][7]=="RL_FIT_GAM"):                               
                logger.info(f"Warning: NetTime Mismatch {filename} {abs(df.loc[x,'Net Time'] - calculatedNetTime)}, {x}"  )

        except (ValueError, TypeError):
                 #Set Time values to None
                df.loc[x,'Calc Time'] = float("nan")
                df.loc[x,'Net Time'] = float("nan")
                logger.info(f"Warning: ValueError Type Error {filename} {x}"  )

                #drop the row
                df.drop(x, inplace = True)

    #On a column by colum basis 
    for event in runtimeVars['StationList'][::1]:
        #add a rank column per event
        df[event + ' Rank'] = df[event].rank(ascending=True)

    #add a Rank Average Column initialised to 0
    df['Average Rank'] = 0.0

    # Calculate the Average Ranks per competitor
    for x in df.index:

        RankTotal = 0
        for event in runtimeVars['StationList'][::1]:
            
            #add a running total of Rank
            RankTotal = RankTotal + df.loc[x, event + ' Rank']

        #write the rank average to the df.
        df.loc[x,'Average Rank'] = RankTotal / len(runtimeVars['StationList'])

    session['runtime'] = runtimeVars
    
 ##############################################################
# Input a df using runtimeVars['competitorRaceNo'] and runtimeVars['competitorName']
# returns a competitor index
#############################################################
def getCompetitorIndex(df, runtimeVars_override=None):


    if runtimeVars_override != None:
        runtimeVars = runtimeVars_override
    else:
        runtimeVars = session.get('runtime', {})
    
    #initialise return value to -1
    compIndex = -1

    #search for the competitor name in the dataframe
    
    # get mask based on substring matching competitor name.
 
     #if relay 
    if 'Member4' in df.columns:
        nameMask = df['Name'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem1Mask = df['Member1'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem2Mask = df['Member2'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        mem3Mask = df['Member3'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        mem4Mask = df['Member4'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        compMask = nameMask | mem1Mask | mem2Mask | mem3Mask | mem4Mask & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False, regex=False)
    elif 'Member2' in df.columns:
        nameMask = df['Name'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem1Mask = df['Member1'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem2Mask = df['Member2'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        compMask = nameMask | mem1Mask | mem2Mask & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False, regex=False)       

    else:
        compMask = df['Name'].str.contains(runtimeVars['competitorName'], regex=False) & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False, regex=False)

    #dataframe with matching competitors and race number
    compDF = df[compMask]

    #if there is at least one match.
    if (len(compDF.index) > 0):

        #get the index of first match.
        compIndex = df[compMask].index.values.astype(int)[0]
 
    else:

        logger = rl_data.get_logger()
        logger.error(f"No data for the selected competitor {runtimeVars['competitorName']} {runtimeVars['competitorRaceNo']} in the selected event {runtimeVars['eventDataList'][0]}")
        logger.debug(f"df {df.shape} compDF {compDF.shape}")

    return compIndex

################################
# Tidy the data/data frame for Correlation
def tidyTheDataCorr(df, runtimeVars_override=None):

    if runtimeVars_override != None:
        runtimeVars = runtimeVars_override
    else:
        runtimeVars = session.get('runtime', {})

    ####Remove Rank columns as dont need anymore
    for event in runtimeVars['StationList'][::1]:
        df.drop(event + ' Rank', axis=1, inplace = True)

    #Average Rank not needed
    if 'Average Rank' in df.columns:
        df.drop('Average Rank', axis=1, inplace = True)

    #Start not in duration format and dont need.
    if 'Start' in df.columns:
        df.drop('Start', axis=1, inplace = True)

    #Start not in duration format and dont need.
    if 'Calc Time' in df.columns:
        df.drop('Calc Time', axis=1, inplace = True)

    #get rid of this in place of 'Calc Time'
    if 'Time Adj' in df.columns:
        df.drop('Time Adj', axis=1, inplace = True)

    if 'Team' in df.columns:
        df.drop('Team', axis=1, inplace = True)

    if 'Member2' in df.columns:
        df.drop('Member1', axis=1, inplace = True)
        df.drop('Member2', axis=1, inplace = True)
        
    if 'Member4' in df.columns:
        df.drop('Member3', axis=1, inplace = True)
        df.drop('Member4', axis=1, inplace = True)

    if 'Pos' in df.columns:
        df.drop('Pos', axis=1, inplace = True)
    
    if 'Category' in df.columns:
        df.drop('Category', axis=1, inplace = True)
        
    if 'Cat Pos' in df.columns:
        df.drop('Cat Pos', axis=1, inplace = True)

    if 'Net Gender Pos' in df.columns:
        df.drop('Net Gender Pos', axis=1, inplace = True)

    #modified for 2025
    if 'Gender' in df.columns:
        df.drop('Gender', axis=1, inplace = True)
        
    if 'Wave' in df.columns:
        df.drop('Wave', axis=1, inplace = True)

    #Remove boring columns
    df.drop(columns=['Race No','Name'], inplace=True)

    #drop rows with empty data 
    df.dropna(inplace = True )
    
    return df


########################################################
#
#this is where the creator/generator/show functions start
#
########################################################

 ################################
# Create a competitor info file.
################################
def CreateDfCsv(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()
    # Check if file exists or force generation

    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    #ignore competitorIndex

    df.to_csv(filepath, index=False)
    logger.debug(f"Saved {filepath}")

    return True
 ################################
# Create a competitor info file.
################################

def GenerateCompInfoTable(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath) : # Add force check if needed
        logger.debug(f"File {filepath} already exists. Reading content.")
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                return f.read()
        except Exception as e:
            logger.critical(f"Error reading existing HTML file {filepath}: {e}")

    if competitorIndex == -1 or competitorIndex not in df.index:
        message = f"Invalid competitorIndex ({competitorIndex}) or competitor not in DataFrame for event {runtimeVars.get('eventDataList', [None, 'N/A'])[1]}."
        logger.error(message)
        error_html = f"<p class='text-danger'>{message}</p>"
        try:
            with open(filepath, "w", encoding='utf-8-sig') as file: file.write(error_html)
        except Exception as e: logger.critical(f"Error writing error HTML to {filepath}: {e}")
        return error_html

    html_parts = ['<div class="table-responsive">']
    html_parts.append('<table class="table table-sm table-striped table-bordered mb-4"><tbody>') 
    
    competitor_name_title = df.loc[competitorIndex, "Name"].title() if pd.notna(df.loc[competitorIndex, "Name"]) else "N/A"

    if 'Member1' in df.columns and pd.notna(df.loc[competitorIndex, "Member1"]):
        members_list = [df.loc[competitorIndex, f"Member{i}"].title() for i in range(1, 3) if f"Member{i}" in df.columns and pd.notna(df.loc[competitorIndex, f"Member{i}"])]
        
        if 'Member3' in df.columns and pd.notna(df.loc[competitorIndex, "Member3"]):
            members_list = [df.loc[competitorIndex, f"Member{i}"].title() for i in range(3, 5) if f"Member{i}" in df.columns and pd.notna(df.loc[competitorIndex, f"Member{i}"])] + members_list

        team_members_str = ', '.join(members_list)        
        html_parts.append(f'<tr><th scope="row" style="width: 30%;">Team Name</th><td>{competitor_name_title}</td></tr>')
        if team_members_str: html_parts.append(f'<tr><th scope="row">Members</th><td>{team_members_str}</td></tr>')
    else:
        html_parts.append(f'<tr><th scope="row" style="width: 30%;">Competitor Name</th><td>{competitor_name_title}</td></tr>')

    if 'Team' in df.columns and pd.notna(df.loc[competitorIndex, "Team"]) :
        team_name_title = df.loc[competitorIndex, "Team"].title() 
        html_parts.append(f'<tr><th scope="row">Team</th><td>{team_name_title}</td></tr>')

    if 'Gender' in df.columns:
        html_parts.append(f'<tr><th scope="row">Gender</th><td>{df.loc[competitorIndex, "Gender"]}</td></tr>')

    compCat = None
    if 'Category' in df.columns:
        compCat = df.loc[competitorIndex, "Category"]
        html_parts.append(f'<tr><th scope="row">Category</th><td>{compCat if pd.notna(compCat) else "N/A"}</td></tr>')

    event_display_name = runtimeVars.get('eventDataList', [None, "N/A"])[1]
    html_parts.append(f'<tr><th scope="row">Event</th><td>{event_display_name}</td></tr>')
    
    if 'Wave' in df.columns:
        html_parts.append(f'<tr><th scope="row">Wave</th><td>{df.loc[competitorIndex, "Wave"]}</td></tr>')
    
    total_finishers = len(df.dropna(subset=['Net Time']).index)
    pos_val = df.loc[competitorIndex, "Pos"]
    pos_display = f"{int(pos_val)}" if pd.notna(pos_val) else "N/A"
    html_parts.append(f'<tr><th scope="row">Overall Position</th><td>{pos_display} of {total_finishers}</td></tr>')

    if compCat and compCat != "All Ages" and 'Category' in df.columns and 'Cat Pos' in df.columns:
        cat_pos_val = df.loc[competitorIndex, "Cat Pos"]
        cat_pos_display = f"{int(cat_pos_val)}" if pd.notna(cat_pos_val) else "N/A"
        if compCat in df['Category'].value_counts():
            cat_finishers = df['Category'].value_counts()[compCat]
            html_parts.append(f'<tr><th scope="row">Category Position</th><td>{cat_pos_display} of {cat_finishers}</td></tr>')
        else:
            html_parts.append(f'<tr><th scope="row">Category Position</th><td>{cat_pos_display} (Category count unavailable)</td></tr>')
            
    html_parts.append(f'<tr><th scope="row">Calculated Time</th><td>{rl_data.format_time_mm_ss(df.loc[competitorIndex, "Calc Time"])}</td></tr>')
    html_parts.append(f'<tr><th scope="row">Time Adjustment</th><td>{rl_data.format_time_mm_ss(df.loc[competitorIndex, "Time Adj"])}</td></tr>')
    html_parts.append(f'<tr><th scope="row">Net Time</th><td>{rl_data.format_time_mm_ss(df.loc[competitorIndex, "Net Time"])}</td></tr>')
    
    avg_rank_val = df.loc[competitorIndex, "Average Rank"]
    avg_rank_display = f"{avg_rank_val:.1f}" if pd.notna(avg_rank_val) else "N/A"
    html_parts.append(f'<tr><th scope="row">Average Event Rank</th><td>{avg_rank_display} of {total_finishers}</td></tr>')

    dfcat = None 
    if compCat and compCat != "All Ages" and 'Category' in df.columns:
        dfcat = df[df['Category'] == compCat].copy() 
        if not dfcat.empty and competitorIndex in dfcat.index:
            current_station_list_for_cat_rank = runtimeVars.get('StationList', []) # Use Stationlist
            
            cat_rank_cols_to_avg = []
            for station in current_station_list_for_cat_rank:
                if station in dfcat.columns:
                    dfcat.loc[:, station + ' CatRank'] = pd.to_numeric(dfcat[station], errors='coerce').rank(ascending=True, na_option='bottom')
                    cat_rank_cols_to_avg.append(station + ' CatRank')
                else:
                    dfcat.loc[:, station + ' CatRank'] = np.nan

            if cat_rank_cols_to_avg:
                 dfcat['Average Cat Rank'] = dfcat[cat_rank_cols_to_avg].mean(axis=1, skipna=True)
                 avg_cat_rank_val = dfcat.loc[competitorIndex, "Average Cat Rank"] # This should be from dfcat
                 avg_cat_rank_display = f"{avg_cat_rank_val:.1f}" if pd.notna(avg_cat_rank_val) else "N/A"
                 html_parts.append(f'<tr><th scope="row">Average Event CatRank</th><td>{avg_cat_rank_display} of {cat_finishers}</td></tr>')
            else:
                html_parts.append(f'<tr><th scope="row">Average Event CatRank</th><td>N/A</td></tr>')
        elif compCat and compCat != "All Ages":
             html_parts.append(f'<tr><th scope="row">Average Event CatRank</th><td>N/A</td></tr>') # Simpler N/A

    html_parts.append('</tbody></table><br>')

    # --- Station Breakdown Table ---
    station_breakdown_columns_display = ['Time', 'Rank'] # Display column names
    station_breakdown_data_keys = ['Time', 'Rank'] # Keys for internal data structure

    if compCat and compCat != "All Ages" and dfcat is not None and not dfcat.empty and competitorIndex in dfcat.index:
        station_breakdown_columns_display.append('CatRank')
        station_breakdown_data_keys.append('CatRank') # Internal key matches display
    
    current_station_list_for_breakdown = runtimeVars.get('StationList', [])
    
    station_table_rows_data = []
    if not current_station_list_for_breakdown:
        logger.error("EventList (for station breakdown) is empty in runtimeVars.")
    
    for station in current_station_list_for_breakdown:
        row_data = {'Station': station} # Add station name to the row data itself
        
        time_val = df.loc[competitorIndex, station] if station in df.columns else np.nan
        rank_col_name = f"{station} Rank"
        rank_val = df.loc[competitorIndex, rank_col_name] if rank_col_name in df.columns else np.nan
        
        #count the number of valide values in the time column
        #rank_val_count = df[station].count()
        
        row_data['Time'] = rl_data.format_time_mm_ss(time_val)
        row_data['Rank'] = f"{rank_val:.1f} of {total_finishers}" if pd.notna(rank_val) else ''

        if 'CatRank' in station_breakdown_data_keys:
            catrank_col_name = f"{station} CatRank"
            if dfcat is not None and catrank_col_name in dfcat.columns and competitorIndex in dfcat.index:
                #count the number of valid values in the rank column
                cat_finishers = df['Category'].value_counts()[compCat]
        
                catrank_val = dfcat.loc[competitorIndex, catrank_col_name]
                row_data['CatRank'] = f"{catrank_val:.1f} of {cat_finishers}" if pd.notna(catrank_val) else ''
            else:
                 row_data['CatRank'] = '' # Ensure key exists if column should
        
        station_table_rows_data.append(row_data)

    if station_table_rows_data:
        # Create DataFrame directly from list of dictionaries
        tableDF = pd.DataFrame(station_table_rows_data)
        # Set 'Station' as the first column if it isn't already, or use it as index
        if 'Station' in tableDF.columns:
            tableDF = tableDF.set_index('Station') 
            # Reorder columns to match display order, if 'Station' was not first
            # This is not strictly necessary if columns in station_table_rows_data were ordered
            # tableDF = tableDF[station_breakdown_columns_display] # This line might error if 'Station' is index
            # If 'Station' is index, columns are just the data columns
            tableDF = tableDF[station_breakdown_data_keys]


        # Convert DataFrame to HTML
        # index=True to show the "Station" index, index_names=False to hide the "Station" label above the index
        html_station_table = tableDF.to_html(
            classes=['table', 'table-sm', 'table-striped', 'table-bordered', 'dataframe'], # Add 'dataframe' for specific styling
            border=0, 
            na_rep='',
            index=True, # Show the 'Station' index
            index_names=False # Show the index name 'Station' as a header
        )
        html_parts.append(html_station_table)
    else:
        html_parts.append("<p>No station breakdown data available.</p>")

    html_parts.append('</div>') # Close responsive wrapper
    final_html = "".join(html_parts)

    try:
        with open(filepath, "w", encoding='utf-8-sig') as file:
            file.write(final_html)
        logger.debug(f"Saved competitor info HTML to {filepath}")
    except Exception as e:
        logger.critical(f"Error writing HTML file {filepath}: {e}")
        return f"<p class='text-danger'>Error generating competitor information file: {e}</p>"

    return final_html
    

#############################
# Correlation
#############################

def CreateCorrBar(df, filepath, runtimeVars, competitorIndex=-1):
    logger = rl_data.get_logger()
  
    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    dfcorr = df.copy(deep=True)

    #next level tidying for correlation
    tidyTheDataCorr(dfcorr, runtimeVars)

    #print(dfcorr.head(10))

    #get corrolation info
    corr_matrix = dfcorr.corr()

    #if a competitor is selected dont show correlation bar chart    
    if(competitorIndex == -1):

        plt.figure(figsize=(10, 10))
        
        # Shows a nice correlation barchar
        heatmap = sns.barplot( data=corr_matrix['Net Time'].drop(['Net Time']))
        
        for i in heatmap.containers:
            heatmap.bar_label(i,fmt='%.2f')
        
        plt.xticks(rotation=70)
        plt.ylabel('Total Time')

        heatmap.set_title('Event Correlation V Total Time ' + runtimeVars['eventDataList'][1], fontdict={'fontsize':12}, pad=10);

        # Output/Show depending of global variable setting with pad inches
        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
        plt.close()

    return True

############################
# Shot Correlation Heatmap
#############################

def CreateCorrHeat(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
    
    #if a competitor is selected dont show correlation bar chart    
    if(competitorIndex == -1):

        dfcorr = df.copy(deep=True)

        #next level tidying for correlation
        tidyTheDataCorr(dfcorr, runtimeVars)
      
        #get corrolation info
        corr_matrix = dfcorr.corr()

        plt.figure(figsize=(10, 10))
        heatmap = sns.heatmap(corr_matrix, vmin=-0, vmax=1, annot=True, cmap='BrBG')
        heatmap.set_title('Correlation Heatmap ' + runtimeVars['eventDataList'][1], fontdict={'fontsize':12}, pad=12);

        # Output/Show depending of global variable setting with pad inches
        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
        plt.close()

    return True

############################
# Show Histogram Age Categories
#############################
def CreateHistAgeCat(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()
    config = session.get('ouptut_config', {}) 

    if os.path.isfile(filepath) and not config.get('forcePng', False):
        logger.debug(f"File {filepath} already exists for CreateHistAgeCat. Skipping generation.")
        return True

    fig, ax = plt.subplots(figsize=(12, 8)) # Use ax for more control

    # --- Data Preparation ---
    if 'Net Time' not in df.columns:
        logger.error("'Net Time' column not found in DataFrame for histogram.")
        plt.close(fig)
        return False
        
    net_times_numeric = pd.to_numeric(df['Net Time'], errors='coerce')
    net_times_in_minutes = net_times_numeric.dropna() / 60.0

    if net_times_in_minutes.empty:
        logger.warning("No valid 'Net Time' data for histogram.")
        ax.text(0.5, 0.5, "No valid Net Time data to display.", ha='center', va='center', transform=ax.transAxes)
        ax.set_xlabel('Time (Minutes)')
        ax.set_ylabel('Num. Participants')
        ax.set_title(runtimeVars['eventDataList'][1] + ' Time Distribution - No Data')
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.3)
        plt.close(fig)
        return True

    min_time_min = np.floor(net_times_in_minutes.min()) 
    #max_time_min = np.ceil(net_times_in_minutes.max()) 
    max_time_min = np.ceil(net_times_in_minutes.quantile(0.98)) 
    if min_time_min >= max_time_min: max_time_min = min_time_min + 1
    bins = np.arange(min_time_min, max_time_min + 1, 1)
    if len(bins) < 2: bins = np.array([min_time_min, min_time_min + 1])

    # --- Category Handling & Plotting ---
    legend_handles = []
    legend_labels = []

    if 'Category' in df.columns and df['Category'].nunique() > 1 and runtimeVars.get('requires_category_data', True): # Check config if this plot should be by cat
        unique_cats = sorted(df['Category'].dropna().unique())
        # Prioritize specific category order if defined, else use unique_cats
        category_order = runtimeVars.get('CategoryOrderHint', unique_cats) # Add CategoryOrderHint to runtimeVars if specific order needed
        
        # Ensure category_order only contains categories present in the data for this event
        category_order = [cat for cat in category_order if cat in unique_cats]
        if not category_order : category_order = unique_cats # Fallback if hint was bad

        try:
            colors = sns.color_palette("tab10", n_colors=len(category_order))
        except ImportError:
            colors = plt.cm.get_cmap('viridis', len(category_order)).colors if len(category_order) > 0 else ['blue']

        data_to_plot_stacked = []
        actual_labels_for_stack = []
        actual_colors_for_stack = []

        for i, cat_name in enumerate(category_order):
            category_times_in_minutes = pd.to_numeric(df[df['Category'] == cat_name]['Net Time'], errors='coerce').dropna() / 60.0
            if not category_times_in_minutes.empty:
                data_to_plot_stacked.append(category_times_in_minutes)
                actual_labels_for_stack.append(cat_name)
                actual_colors_for_stack.append(colors[i % len(colors)])
        
        if data_to_plot_stacked:
            ax.hist(data_to_plot_stacked, bins=bins, stacked=True, label=actual_labels_for_stack, color=actual_colors_for_stack, edgecolor='white')
            # For legend, get handles from hist or create custom ones
            # plt.hist returns n, bins, patches. patches is a list of lists for stacked.
            # For simplicity with stacked, let legend be created from labels passed to hist.
            # legend_handles, legend_labels = ax.get_legend_handles_labels() # This might get complex with stacked
            # Create custom handles for stacked legend
            for i, label in enumerate(actual_labels_for_stack):
                legend_handles.append(mlines.Line2D([], [], color=actual_colors_for_stack[i], marker='s', linestyle='None', markersize=10))
                legend_labels.append(label)
        else:
            if not net_times_in_minutes.empty:
                ax.hist(net_times_in_minutes, bins=bins, color='skyblue', edgecolor='black')
    else: 
        if not net_times_in_minutes.empty:
            ax.hist(net_times_in_minutes, bins=bins, color='skyblue', edgecolor='black', label='All Participants')
            # legend_handles, legend_labels = ax.get_legend_handles_labels() # For single series

    # --- Competitor Indication (if competitorIndex is valid) ---
    if competitorIndex != -1 and competitorIndex in df.index:
        competitor_net_time_seconds = pd.to_numeric(df.loc[competitorIndex, 'Net Time'], errors='coerce')
        if not pd.isna(competitor_net_time_seconds):
            competitor_net_time_minutes = competitor_net_time_seconds / 60.0
            competitor_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Competitor"
            
            #calculate finishing percentage 
            # competitor position / max value in the 'Pos' column
            position_percent = ((100.0 * df.loc[competitorIndex, 'Pos']) / len(df.dropna(subset=['Net Time']).index)) 
                        
            # Add a vertical line for the competitor's time
            line_color = 'red' # Choose a distinct color
            ax.axvline(competitor_net_time_minutes, color=line_color, linestyle='--', linewidth=2, ymax=0.95, zorder=10)
            
            # Create a custom legend handle for the competitor
            comp_handle = mlines.Line2D([], [], color=line_color, linestyle='--', linewidth=2, 
                                        label=f"{competitor_name}'s Time ({rl_data.format_time_mm_ss(competitor_net_time_seconds)})")
            legend_handles.append(comp_handle)
            legend_labels.append(comp_handle.get_label()) # Get label from handle
            
            # Optional: Add text annotation near the line (can get crowded)
            y_pos_for_text = ax.get_ylim()[1] * 0.95 # Position text near the top
            ax.text(competitor_net_time_minutes + 0.2, y_pos_for_text, 
                     f"Top {position_percent:2.1f}%",
                     color='black', fontsize=8, ha='left', va='top')
        else:
            logger.warning(f"Competitor {competitorIndex} Net Time is invalid.")


    # --- Final Plot Styling ---
    tick_step = 5 if (max_time_min - min_time_min) > 30 else 2 if (max_time_min - min_time_min) > 10 else 1
    ax.set_xticks(np.arange(min_time_min, max_time_min + 1, tick_step))
    ax.tick_params(axis='x', labelsize=8)
    ax.tick_params(axis='y', labelsize=8)

    ax.set_xlabel('Finish Time (Minutes)', fontsize=10)
    ax.set_ylabel('Number of Participants', fontsize=10)
    event_display_name = runtimeVars['eventDataList'][1]
    
    title_str = f'{event_display_name}\nOverall Time Distribution'
    if competitorIndex != -1 and 'competitor_name' in locals() and competitor_name:
        title_str += f"\n(Competitor: {competitor_name})"
    ax.set_title(title_str, fontsize=14, pad=15)
    
    ax.grid(True, axis='y', linestyle=':', color='grey', alpha=0.7)

    if legend_handles: # Only show legend if there's something to label
        ax.legend(handles=legend_handles, labels=legend_labels, title="Legend", fontsize=8, title_fontsize=9, loc='upper right')

    plt.tight_layout()

    try:
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        logger.info(f"Saved histogram to {filepath}")
    except Exception as e:
        logger.error(f"Error saving histogram {filepath}: {e}")
    finally:
        plt.close() 

    return True

#############################
# Create Station Histograms 1 - 6 wrapper
#############################

def CreateStationHistogramsPart1(df, filepath, runtimeVars, competitorIndex=-1):
    logger = rl_data.get_logger()
    
    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping.")
        print(f"File {filepath} already exists. Skipping.")
        return False
        
    return CreateStationHistograms(df, filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex, part_to_generate=1)

#############################
# Create Station Histograms 7 - 12 wrapper
#############################

def CreateStationHistogramsPart2(df, filepath, runtimeVars, competitorIndex=-1):
    logger = rl_data.get_logger()
    
    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping.")
        print(f"File {filepath} already exists. Skipping.")
        return False
        
    return CreateStationHistograms(df, filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex, part_to_generate=2)

#############################
# Create Station Histograms 1 - 12
#############################

def CreateStationHistograms(df, filepath, runtimeVars, competitorIndex=-1, part_to_generate=None):
    """
    Generates PNGs for station histograms, split into parts.
    Each part will be a 1-column, 6-row grid of subplots.
    All subplots within a part share a common x-axis time scale if global_x_scale is True.

    Args:
        df (pd.DataFrame): The main DataFrame.
        filepath (str or Path): Filepath for png
        runtimeVars (dict): Runtime variables.
        competitorIndex (int): Index of the competitor, or -1.
        part_to_generate (int, optional): 1 or 2. If None, generates both. 
                                          Used by async calls to generate one part at a time.
    """
    logger = rl_data.get_logger()
    config = session.get('ouptut_config', {})

    station_names_all = runtimeVars.get('StationList', [])
    if not station_names_all or len(station_names_all) != 12:
        logger.error(f"StationList must contain exactly 12 stations. Found: {len(station_names_all)}")
        return False

    # --- Determine Global X-axis Range (in seconds) across ALL 12 stations ---
    # This calculation should ideally happen once if generating parts separately via async.
    # For now, it's calculated here. If called for individual parts, it should ideally get
    # these global_min/max values passed in or from a cached/pre-calculated source.
    all_filtered_times_for_global_scale = []
    for station_name_iter in station_names_all: # Iterate over all 12 for global scale
        if station_name_iter in df.columns:
            station_times_iter = pd.to_numeric(df[station_name_iter], errors='coerce').dropna()
            if not station_times_iter.empty:
                cutoff_95th = station_times_iter.quantile(0.95)
                if pd.notna(cutoff_95th):
                    all_filtered_times_for_global_scale.extend(station_times_iter[station_times_iter <= cutoff_95th].tolist())

    if not all_filtered_times_for_global_scale:
        global_min_time_sec, global_max_time_sec = 0, 600 # Default
    else:
        global_min_time_sec = np.floor(min(all_filtered_times_for_global_scale) / 10) * 10
        global_max_time_sec = np.ceil(max(all_filtered_times_for_global_scale) / 10) * 10
    if global_min_time_sec >= global_max_time_sec: global_max_time_sec = global_min_time_sec + 60
        
    #global_min_time_sec = 0
    #global_max_time_sec = 10*60
    
    num_global_bins = 60
    global_bin_width = max(5, np.ceil(((global_max_time_sec - global_min_time_sec) / num_global_bins) / 5) * 5)
    if global_bin_width == 0: global_bin_width = 5
    common_bins = np.arange(global_min_time_sec, global_max_time_sec + global_bin_width, global_bin_width)
    if len(common_bins) < 2: common_bins = np.array([global_min_time_sec, global_max_time_sec])
    # --- End of Global X-axis Scale Calculation ---

    parts_to_process = []
    if part_to_generate == 1:
        parts_to_process = [{'stations': station_names_all[0:6], 'part_num': 1, 'title_part': "Stations 1-6"}]
    elif part_to_generate == 2:
        parts_to_process = [{'stations': station_names_all[6:12], 'part_num': 2, 'title_part': "Stations 7-12"}]
    elif part_to_generate is None: # Generate both parts (e.g., for synchronous call)
        parts_to_process = [
            {'stations': station_names_all[0:6], 'part_num': 1, 'title_part': "Stations 1-6"},
            {'stations': station_names_all[6:12], 'part_num': 2, 'title_part': "Stations 7-12"}
        ]
    else:
        logger.error(f"Invalid part_to_generate value: {part_to_generate}")
        return False
        
    overall_success = True

    for part_info in parts_to_process:
        current_stations = part_info['stations']
        part_num = part_info['part_num']
        
        if (part_to_generate is None):
            base_filepath_obj = Path(filepath)
            current_filepath = base_filepath_obj.with_name(base_filepath_obj.stem + f"_Part{part_num}").with_suffix(".png")

            if os.path.isfile(current_filepath) and not config.get('forcePng', False):
                logger.debug(f"File {current_filepath} already exists. Skipping.")
                continue
        else:
            current_filepath = Path(filepath)

        # Create a 6x1 grid of subplots (6 rows, 1 column)
        nrows_subplot, ncols_subplot = 6, 1
        # Adjust figsize: taller and wide enough for one column of wide plots
        # Width can be around 12 inches. Height needs to accommodate 6 plots + titles/labels.
        # Approx 2.5-3 inches per subplot height.
        fig_height_per_subplot = 2.75 
        fig, axes = plt.subplots(nrows_subplot, ncols_subplot, figsize=(12, fig_height_per_subplot * nrows_subplot)) 
        if nrows_subplot * ncols_subplot == 1: # if for some reason only 1 plot
            axes = [axes] 
        else:
            axes = axes.flatten()

        event_display_name = runtimeVars.get('eventDataList', [None, "Event Unknown"])[1]
        main_title_text = f"{event_display_name} - {part_info['title_part']}\nTime Distributions (Fastest 99%, Common X-Axis)"
        if competitorIndex != -1 and 'Name' in df.columns and competitorIndex in df.index:
            competitor_name = df.loc[competitorIndex, 'Name']
            main_title_text += f"\nCompetitor: {competitor_name}"
        fig.suptitle(main_title_text, fontsize=14, y=0.99) # Adjust y if needed due to taller figure

        for i, station_name in enumerate(current_stations):
            if i >= len(axes): break 
            ax = axes[i]

            # ... (Data checking and filtering for station_times_for_hist as before) ...
            if station_name not in df.columns:
                ax.text(0.5,0.5, "Data N/A", ha='center', va='center'); ax.set_title(station_name, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
                continue
            station_times_all = pd.to_numeric(df[station_name], errors='coerce').dropna()
            if station_times_all.empty:
                ax.text(0.5,0.5, "No Data", ha='center', va='center'); ax.set_title(station_name, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
                continue
            cutoff_99th_station = station_times_all.quantile(0.99)
            station_times_for_hist = station_times_all[station_times_all <= cutoff_99th_station] if pd.notna(cutoff_99th_station) else station_times_all
            if station_times_for_hist.empty: station_times_for_hist = station_times_all


            ax.hist(station_times_for_hist, bins=common_bins, color='lightblue', edgecolor='black', alpha=0.75 ) #,  density=True)  density=True can be good for comparison
            ax.set_title(station_name, fontsize=10, pad=5)
            
            ax.set_xlim(global_min_time_sec, global_max_time_sec)

            # Fewer Y ticks for taller, narrower plots
            ax.yaxis.set_major_locator(plt.MaxNLocator(nbins=3, prune='both')) 
            ax.tick_params(axis='y', labelsize=7)
            if i == len(current_stations) -1 : # X-axis label only for the last subplot in the column
                 ax.set_xlabel('Time (s)', fontsize=9)
                 # X-ticks for the last subplot (can be more detailed)
                 num_desired_xticks_subplot = 10 # More ticks as it's wider
                 xtick_locs_subplot = plt.MaxNLocator(nbins=num_desired_xticks_subplot, prune='both', integer=True).tick_values(global_min_time_sec, global_max_time_sec)
                 ax.set_xticks(xtick_locs_subplot)
                 ax.set_xticklabels([f"{int(xt)}" for xt in xtick_locs_subplot], rotation=0, ha="center") # No rotation needed if enough space
                 ax.tick_params(axis='x', labelsize=8)
            else:
                 ax.set_xticks([]) # No x-ticks for upper plots in the column to save space


            # Y-axis label - can be set for the figure or for one of the middle plots
            if i == (nrows_subplot // 2) : # Put Y label on a middle plot
                ax.set_ylabel('Finishers', fontsize=9) # Changed label from 'Frequency' if density=True
                #ax.set_ylabel('Density / Frequency', fontsize=9) # Changed label from 'Frequency' if density=True

            ax.grid(True, axis='y', linestyle=':', alpha=0.5)

            if competitorIndex != -1 and competitorIndex in df.index:
                # ... (Competitor indication logic - mostly same as before) ...
                # ... ensure text annotation positions adapt to the new taller/wider subplot ...
                competitor_station_time = pd.to_numeric(df.loc[competitorIndex, station_name], errors='coerce')
                station_rank_col = f"{station_name} Rank"
                if not pd.isna(competitor_station_time) and station_rank_col in df.columns:
                    if global_min_time_sec <= competitor_station_time <= global_max_time_sec:
                        competitor_rank = pd.to_numeric(df.loc[competitorIndex, station_rank_col], errors='coerce')
                        if not pd.isna(competitor_rank):
                            total_rfs = df[station_rank_col].dropna().count()
                            pos_perc = (competitor_rank / total_rfs) * 100 if total_rfs > 0 else 0
                            
                            line_color = 'red' # Changed for better contrast
                            ax.axvline(competitor_station_time, color=line_color, linestyle='--', linewidth=2.0, ymax=0.92, zorder=10)
                            
                            # Add Competitor's Time (mm:ss) in top-right of subplot
                            competitor_time_str = f"Station time:{rl_data.format_time_mm_ss(competitor_station_time)}" # Use your project's formatter
                            ax.text(0.98, 0.97, competitor_time_str, 
                                    transform=ax.transAxes, # Position relative to subplot axes
                                    horizontalalignment='right', 
                                    verticalalignment='top',
                                    fontsize=10, 
                                    color='black', # Match line color
                                    bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7, ec='none'))
                            
                            text_y_pos = ax.get_ylim()[1] * 0.85 # Adjust y for text based on new plot height
                            current_xlim = ax.get_xlim()
                            text_x_pos_offset = (current_xlim[1] - current_xlim[0]) * 0.03 # Smaller % offset for wider plot

                            if competitor_station_time < (current_xlim[0] + (current_xlim[1]-current_xlim[0])/2): 
                                text_ha = 'left'; anno_x_pos = competitor_station_time + text_x_pos_offset
                            else: 
                                text_ha = 'right'; anno_x_pos = competitor_station_time - text_x_pos_offset
                            
                            anno_x_pos = max(current_xlim[0] + text_x_pos_offset*0.1, min(current_xlim[1] - text_x_pos_offset*0.1, anno_x_pos))

                            ax.text(anno_x_pos, text_y_pos, f"Top {pos_perc:.0f}%",
                                    color=line_color, fontsize=10, ha=text_ha, va='center', # Adjusted va
                                    bbox=dict(boxstyle='round,pad=0.15', fc='white', alpha=0.75, ec='none'))
        
        # Remove unused axes if any (shouldn't happen if current_stations has 6 items)
        for j_ax in range(len(current_stations), nrows_subplot * ncols_subplot):
             if j_ax < len(axes): fig.delaxes(axes[j_ax])

        plt.tight_layout(rect=[0, 0.02, 1, 0.95]) # Adjust rect for suptitle and potential x-label of last plot

        try:
            plt.savefig(current_filepath, bbox_inches='tight', pad_inches=0.15)
            logger.info(f"Saved station histogram {part_info['title_part']} to {current_filepath}")
        except Exception as e:
            logger.error(f"Error saving station histogram {current_filepath}: {e}")
            overall_success = False
        finally:
            plt.close(fig) 

    return overall_success

#############################
# Show Bar chart Events
#############################
def CreateBarChartEvent(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    station_names = runtimeVars['StationList']
    x_positions = np.arange(len(station_names))

    percentile_bands_data = {
        '70-90%': [df[event].quantile(0.90) for event in station_names],
        '50-70%': [df[event].quantile(0.70) for event in station_names],
        '30-50%': [df[event].quantile(0.50) for event in station_names],
        '10-30%': [df[event].quantile(0.30) for event in station_names],
        '01-10%': [df[event].quantile(0.10) for event in station_names],
        'Fastest': [df[event].quantile(0.01) for event in station_names],       
        #'Fastest': [df[event].min() for event in station_names]
    }
    
    band_colors = {
        '70-90%': 'grey', '50-70%': 'red', '30-50%': 'orange',
        '10-30%': 'green', '01-10%': 'purple', 'Fastest': 'blue'
    }
    plot_order_bands = ['70-90%', '50-70%', '30-50%', '10-30%', '01-10%', 'Fastest']

    fig, ax = plt.subplots(figsize=(10, 10)) # Square figure

    bar_handles_for_legend1 = [] 
    bar_labels_for_legend1 = []

    for band_label in plot_order_bands:
        times = percentile_bands_data[band_label]
        plot_times = [0 if pd.isna(t) else t for t in times]
        bar_container = ax.bar(station_names, plot_times, color=band_colors[band_label], label=band_label, width=0.8)
        if bar_container:
             bar_handles_for_legend1.append(bar_container[0])
             bar_labels_for_legend1.append(band_label)

    competitor_handle = None
    if competitorIndex != -1:
        competitor_event_times = [df.loc[competitorIndex, event] for event in station_names]
        competitor_plot_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Competitor"
        
        competitor_handle = ax.scatter(x_positions, competitor_event_times, 
                   marker='P', s=100, color='cyan', 
                   edgecolor='black', linewidth=1.5,
                   label=f"{competitor_plot_name}'s Time", 
                   zorder=10)

        for i, time_val in enumerate(competitor_event_times):
            if not pd.isna(time_val):
                ax.annotate(rl_data.format_time_mm_ss(time_val),
                            (x_positions[i], time_val),
                            textcoords="offset points", xytext=(0, 8), # Slightly more offset for marker
                            ha='center', fontsize=7, color='black',
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
                            
    max_y_val_for_plot = 0
    valid_top_band_times = [t for t in percentile_bands_data['70-90%'] if not pd.isna(t)]
    if valid_top_band_times: max_y_val_for_plot = max(valid_top_band_times)

    if competitorIndex != -1 and 'competitor_event_times' in locals():
        valid_comp_times = [t for t in competitor_event_times if not pd.isna(t)]
        if valid_comp_times: max_y_val_for_plot = max(max_y_val_for_plot, max(valid_comp_times))
    
    # Add more padding to Y-lim if legends are at the top inside
    #ax.set_ylim(0, max_y_val_for_plot * 1.25 if max_y_val_for_plot > 0 else 300) 
    ax.set_ylim(0, max_y_val_for_plot * 1.05 if max_y_val_for_plot > 0 else 300) 

    current_ylim_top = ax.get_ylim()[1]
    step_y = 60 if current_ylim_top > 240 else 30 
    if step_y <= 0: step_y = 30 
    ax.set_yticks(np.arange(0, current_ylim_top + step_y, step_y))

    ax.grid(True, axis='y', linestyle=':', color='grey', alpha=0.6)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(station_names, rotation=60, ha="right", fontsize=9)
    
    ax.tick_params(axis='y', labelsize=9)
    ax.set_ylabel('Time in Seconds', fontsize=10)
    # xlabel can be omitted if x-tick labels are descriptive and space is needed at bottom
    # ax.set_xlabel('Workout Station', fontsize=10) 

    # --- Title ---
    # Reduced title padding to bring it closer to the plot
    title_pad = 10 
    if competitorIndex == -1:
        ax.set_title(f"{runtimeVars['eventDataList'][1]}\nStation Time Distribution", fontsize=13, pad=title_pad)
    else:
        competitor_title_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Selected Competitor"
        ax.set_title(f"{runtimeVars['eventDataList'][1]} - {competitor_title_name}\nPerformance vs. Time Percentiles", fontsize=13, pad=title_pad)
    
    # --- Legend Handling: Two separate legends at the top ---
    # Legend 1: Percentile Bands (reversed for visual stacking order)
    leg1_handles = bar_handles_for_legend1[::-1]
    leg1_labels = bar_labels_for_legend1[::-1]
    
    legend1 = ax.legend(leg1_handles, leg1_labels,
                        loc='upper center', 
                        bbox_to_anchor=(0.5, 0.99), # High up, centered
                        ncol=3, # Try to fit in 2 rows if 6 items
                        fancybox=True, shadow=False, fontsize=7,
                        handletextpad=0.4, columnspacing=0.8, labelspacing=0.3,
                        title="Time at Percentile of Athletes", title_fontsize=7.5)
    if legend1: legend1.get_title().set_fontweight('bold')

    if competitorIndex != -1 and competitor_handle:
        # Legend 2: Competitor's Time
        # Place it slightly offset from the first legend, or in a different corner
        legend2 = ax.legend([competitor_handle], [competitor_handle.get_label()],
                            loc='upper right', # Or 'upper left'
                            bbox_to_anchor=(0.98, 0.99), # Adjust to fit, e.g., top-right corner
                            fancybox=True, shadow=False, fontsize=8, frameon=True, facecolor='white', edgecolor='lightgray')
        ax.add_artist(legend1) # IMPORTANT: Add the first legend back

    # Adjust subplot parameters to minimize unused space and ensure legends fit
    # We want to maximize plot area, so reduce bottom margin significantly
    # Top margin needs to be just enough for title and upper legends
    plt.subplots_adjust(left=0.08, right=0.95, top=0.97, bottom=0.15) # Reduced bottom margin

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.1)
    plt.close()
    
    return True

#############################
# Show Violin chart
#############################

def CreateViolinChartEvent(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    station_data_df = df[runtimeVars['StationList']].copy()
    for col in runtimeVars['StationList']:
        station_data_df[col] = pd.to_numeric(station_data_df[col], errors='coerce')

    all_station_times_flat = station_data_df.values.flatten()
    all_station_times_flat = all_station_times_flat[~np.isnan(all_station_times_flat)] 
    
    cutoff_time = 600.0 
    if len(all_station_times_flat) > 0:
        pass 

    df_melted = station_data_df.melt(var_name='Station', value_name='Time (s)')
    df_melted['Station'] = pd.Categorical(df_melted['Station'], categories=runtimeVars['StationList'], ordered=True)
    df_melted_filtered = df_melted[df_melted['Time (s)'] < cutoff_time].dropna(subset=['Time (s)'])

    plt.figure(figsize=(12, 12))
    ax = plt.gca() # Get current axes to use for annotations later

    if not df_melted_filtered.empty:
        sns.violinplot(ax=ax, x='Station', y='Time (s)', data=df_melted_filtered, 
                       order=runtimeVars['StationList'], 
                       inner='quartile', 
                       cut=1,          
                       hue='Station',         
                       palette='viridis',     
                       legend=False,          
                       linewidth=1.5,   
                       density_norm='width')
    else:
        print("Warning: All data filtered out by cutoff time. Plotting empty chart structure.")
        ax.set_xticks(np.arange(len(runtimeVars['StationList'])))
        ax.set_xticklabels(runtimeVars['StationList'], rotation=90, fontsize=9)

    if competitorIndex != -1:
        compList_station_times_raw = [] # Store raw times for labeling
        compList_station_times_plot = [] # Store potentially clamped times for plotting marker

        for event in runtimeVars['StationList']:
            comp_time = df.loc[competitorIndex, event]
            try:
                comp_time_numeric = float(comp_time)
                compList_station_times_raw.append(comp_time_numeric)
                # If competitor time is above cutoff, clamp it for marker visibility
                plot_time = min(comp_time_numeric, cutoff_time -1) if not pd.isna(comp_time_numeric) else np.nan
                compList_station_times_plot.append(plot_time)
            except (ValueError, TypeError):
                compList_station_times_raw.append(np.nan)
                compList_station_times_plot.append(np.nan)

        x_positions = np.arange(len(runtimeVars['StationList']))
        
        competitor_name_legend = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Competitor"

        plt.scatter(x_positions, compList_station_times_plot, 
                    marker='D', s=80, color='orangered', 
                    edgecolor='black', linewidth=1,
                    label=f"{competitor_name_legend}'s Time", 
                    zorder=10)
        
        # Add mm:ss labels to each competitor marker
        for i, raw_time in enumerate(compList_station_times_raw):
            plot_time_for_marker = compList_station_times_plot[i] # Y-coordinate of the marker
            if not pd.isna(raw_time) and not pd.isna(plot_time_for_marker):
                ax.annotate(rl_data.format_time_mm_ss(raw_time), # Label with the raw, un-clamped time
                            (x_positions[i], plot_time_for_marker),
                            textcoords="offset points", 
                            xytext=(0, 7), # Offset 7 points vertically upwards
                            ha='center', 
                            fontsize=7, 
                            color='black', # Or 'orangered' to match marker
                            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", lw=0.5, alpha=0.7))

        plt.legend(loc='upper right', fontsize=9)

    max_y_for_ticks = cutoff_time
    # Ensure compList_station_times_plot exists and is populated before using it in nanmax
    if competitorIndex != -1 and 'compList_station_times_plot' in locals() and len(compList_station_times_plot) > 0:
         valid_comp_plot_times = [t for t in compList_station_times_plot if not pd.isna(t)]
         if valid_comp_plot_times: # Check if there are any valid (non-NaN) times
            max_y_for_ticks = max(cutoff_time, np.nanmax(valid_comp_plot_times))
    
    upper_ytick_limit = max_y_for_ticks + 60
    if upper_ytick_limit <=0 : upper_ytick_limit = 60 
    step = 60 if upper_ytick_limit > 240 else 30 # Adjust step based on range for better ticking
    plt.yticks(np.arange(0, upper_ytick_limit, step))

    plt.tick_params(axis='x', labelrotation=90, labelsize=9)
    plt.tick_params(axis='y', labelsize=9)
    plt.ylabel('Time in Seconds', fontsize=10)
    plt.xlabel('Workout Station', fontsize=10)
    plt.grid(True, linestyle=':', color='grey', alpha=0.6)
    
    if competitorIndex == -1:
        plt.title(f"{runtimeVars['eventDataList'][1]} Station Time Distribution", fontsize=14)
    else:
        competitor_title_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Selected Competitor"
        plt.title(f"{runtimeVars['eventDataList'][1]} - {competitor_title_name}\nStation Time vs. Distribution", fontsize=14)
    
    #plt.tight_layout(pad=1.0)

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()
    
    return True
#############################
# Show Bar chart Cut Off Events
#############################

def CreateBarChartCutOffEvent(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
    
    fig, ax = plt.subplots(figsize=(10, 10))

    #null list
    cutOffStationList = []
    MyIndex = 0

    for event in runtimeVars['StationList'][::]:
        #add percentage to list
        cutOffStationList.append((100*runtimeVars['StationCutOffCount'][MyIndex]) / len(df.index) )
        MyIndex = MyIndex + 1

    if runtimeVars['eventDataList'][2]=="2025":
        ax.bar(runtimeVars['StationList'], cutOffStationList,       color='red'   , label='Partipants > 10min')
    else:
        ax.bar(runtimeVars['StationList'], cutOffStationList,       color='orange', label='Partipants > 7min')

    

    for container in ax.containers:
        ax.bar_label(container,fmt='%.1f%%')

    plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)
    plt.tick_params(axis='x', labelrotation=90)
    plt.ylabel('Num Participants')
    
    if runtimeVars['eventDataList'][2]=="2025":
        plt.title(runtimeVars['eventDataList'][1] + ' Station 10 Min Stats')
    else:
        plt.title(runtimeVars['eventDataList'][1] + ' Station 7 Min Stats')
    
    plt.legend() 

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

#############################
# Show PieChartAverage
#############################
def CreatePieChartAverage(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    # Just do Generic pie chart based on mean time per event.
    if(competitorIndex==-1):

        plt.figure(figsize=(10, 10))

        meanStationList = []
        meanStationListLabel = []
        totalMeanTime = 0.0
    
        # get the median time for each event.
        for event in runtimeVars['StationList']:
            meanStationList.append(df[event].mean())
            totalMeanTime = totalMeanTime + int(df[event].mean())

            eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df[event].mean())//60 ,int(df[event].mean())%60)
            meanStationListLabel.append(eventLabelString)

        totalMeanTimeString = "{:1d}m {:2d}s".format(int(totalMeanTime)//60 ,int(totalMeanTime)%60)
        plt.title(runtimeVars['eventDataList'][1] + ' Average Station Breakdown : ' + totalMeanTimeString )
    
        #create pie chart = Use Seaborn's color palette 'Set2'
        plt.pie(meanStationList, labels = meanStationListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))
        
        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
        plt.close()

    # else do competitor specific pie chart based on actual time per event.
    else:
        
        #print(f"Generating Pie Chart for competitor {df.loc[competitorIndex,'Name']} {filepath}")

        plt.figure(figsize=(10, 10))

        compStationList = []
        compStationListLabel = []

        # get the median time for each event.
        for event in runtimeVars['StationList']:
        
            compStationList.append(df.loc[competitorIndex,event])
            eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df.loc[competitorIndex,event])//60 ,int(df.loc[competitorIndex,event])%60)
            compStationListLabel.append(eventLabelString)

        totalCompTimeString = "{:1d}m {:2d}s".format(int(df.loc[competitorIndex,'Calc Time'])//60 ,int(df.loc[competitorIndex,'Calc Time'])%60)
        plt.title(runtimeVars['eventDataList'][1] + ' ' + df.loc[competitorIndex,'Name'] + ' Stations: ' + totalCompTimeString )

        #print(f"Generating Pie Chart for competitor {compStationList} {compStationListLabel}")

        #create pie chart = Use Seaborn's color palette 'Set2'
        plt.pie(compStationList, labels = compStationListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))

        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
        plt.close()

    return True


#############################
# Show Radar Chart
#############################

def CreateRadar(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
    
    num_vars = len(runtimeVars['StationList'])
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True)) # Use consistent larger size

    if competitorIndex == -1:
        # --- Generic Radar: Median Actual Times (Y-axis in seconds) ---
        # Faster times (lower seconds) will be closer to the center.
        
        median_event_times_actual = []
        station_axis_labels = [] # For station names only on this plot

        for event in runtimeVars['StationList']:
            median_time = df[event].quantile(0.50)
            median_event_times_actual.append(median_time)
            station_axis_labels.append(event) # Just the event name for axis labels

        # Data to plot (actual median times), close the loop for plot
        values_to_plot = np.concatenate((median_event_times_actual, [median_event_times_actual[0]]))
        plot_angles = angles + [angles[0]] # Close the loop for angles as well

        ax.plot(plot_angles, values_to_plot, linewidth=2, linestyle='solid', label='Median Time (s)', color='darkorange', zorder=2)
        ax.fill(plot_angles, values_to_plot, color='gold', alpha=0.25, zorder=1)

        # Set Y-axis limits based on actual median times
        min_y_val = 0 # Or min(median_event_times_actual) * 0.9 if you don't want to start at 0
        max_y_val = max(median_event_times_actual) * 1.1 # Extend a bit for labels
        ax.set_ylim(min_y_val, max_y_val)

        # Add labels for each data point on the median line
        for i, value in enumerate(median_event_times_actual):
            angle_rad = angles[i] # Use original angles (not plot_angles) for label placement
            # Add a small offset to place label slightly outside the point
            offset = (max_y_val - min_y_val) * 0.05 # 5% of range as offset
            ax.text(angle_rad, value + offset, f"{value:.0f}s", 
                    horizontalalignment='center', verticalalignment='center', # Adjust as needed
                    fontsize=7, color='black', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", lw=0.5, alpha=0.7))

        # Y-axis ticks and labels (showing seconds)
        num_yticks = 5 
        yticks = np.linspace(min_y_val if min_y_val > 0 else ax.get_yticks()[1], max_y_val, num_yticks, endpoint=True) # Avoid 0 if min_y_val is 0 for first tick
        ax.set_yticks(yticks)
        ax.set_yticklabels([f"{val:.0f}s" for val in yticks])

        ax.set_xticks(angles) # Use original angles for xticks
        ax.set_xticklabels(station_axis_labels) # Set x-tick labels to event names
        
        plt.title(f"{runtimeVars['eventDataList'][1]}\nMedian Performance Times (Seconds)", size=14, color='black', y=1.1)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1)) # Moved legend

    else: # competitorIndex != -1 (Individual Competitor Plot - kept as your preferred version)
        compEventPercentiles = []
        compEventLabels = [] 

        for event in runtimeVars['StationList']:
            raw_rank = df.loc[competitorIndex, event + ' Rank']
            max_rank = df[event + ' Rank'].max() 
            
            valid_ranks = df[event + ' Rank'].dropna()
            if len(valid_ranks) <= 1:
                percentile = 50 # Default for no meaningful rank
            else:
                percentile = ((raw_rank) / max_rank) * 100 if max_rank > 0 else 0

            percentile = max(0, min(100, percentile)) # Clamp
            eventLabelString = f"{event}\nTop {percentile:.1f}%"

            compEventPercentiles.append(percentile)
            compEventLabels.append(eventLabelString)

        plot_angles = angles + [angles[0]] # Ensure plot_angles is defined here too
        values_to_plot = np.concatenate((compEventPercentiles, [compEventPercentiles[0]]))
        
        ax.plot(plot_angles, values_to_plot, linewidth=2, linestyle='solid', label='Competitor %ile Rank', color='dodgerblue', zorder=3)
        ax.fill(plot_angles, values_to_plot, color='dodgerblue', alpha=0.3, zorder=2)

        median_percentiles_benchmark = np.array([50] * (num_vars + 1)) 
        ax.plot(plot_angles, median_percentiles_benchmark, linewidth=1, linestyle='--', color='brown', label='Median (50th %ile)', zorder=1)
        
        # This y_lim inversion was key to your "Top X%" label making sense with lower %ile being better graphically
        ax.set_ylim(100, 0) 
        ax.set_yticks(np.arange(0, 101, 20)) 
        ax.set_yticklabels(["Top % ", "Top 20%", "Top 40%", "Top 60%", "Top 80%", " "]) 

        ax.set_xticks(plot_angles[:-1])
        ax.set_xticklabels(compEventLabels) 
        
        label_padding = -5 # Experiment with this value (e.g., 10, 15, 20, 25) 
        ax.tick_params(axis='x', pad=label_padding)

        plt.title(f"{runtimeVars['eventDataList'][1]}\n{df.loc[competitorIndex,'Name']} Performance Rank Percentile",y=1.12,size=14, color='black')
        ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1)) # Adjusted anchor for more space

    # --- Common Styling for Both Plot Types (Mostly for competitor plot now, generic has its own) ---
    if competitorIndex != -1 : # Apply this specific styling only to competitor plot
        ax.yaxis.grid(True, linestyle='--', color='gray', alpha=0.7)
        ax.xaxis.grid(True, linestyle='--', color='gray', alpha=0.7)

    # Station labels - adjust font size and padding if they overlap
    # This loop applies to both, but specific font sizes/alignments might differ
    for label, angle_rad_val in zip(ax.get_xticklabels(), angles): # Use original angles for positioning
        if np.isclose(angle_rad_val, np.pi * 0.5) or np.isclose(angle_rad_val, np.pi * 1.5):
            label.set_horizontalalignment('center')
        elif (0 <= angle_rad_val < np.pi * 0.5) or (np.pi * 1.5 < angle_rad_val < np.pi * 2):
            label.set_horizontalalignment('left')
        else:
            label.set_horizontalalignment('right')
        
        label.set_fontsize(9 if competitorIndex != -1 else 8) # Slightly smaller for generic if needed
        label.set_rotation_mode('anchor')


    ax.tick_params(axis='y', labelsize=8, colors='dimgray')
    ax.tick_params(axis='x', pad=15 if competitorIndex != -1 else 20) # More padding for generic if labels are simpler

    # Legend position for generic plot was set earlier. For competitor plot:
    if competitorIndex != -1:
        legend = ax.get_legend() # Retrieve already created legend
        if legend:
                legend.set_loc('upper right')
                legend.set_bbox_to_anchor((1.27, 1.13)) # Consistent with your else block
                for text in legend.get_texts():
                    text.set_color('dimgray')
        else: # Generic plot legend
            legend = ax.get_legend()
            if legend:
                legend.set_loc('upper right')
                legend.set_bbox_to_anchor((1.25, 1.05)) # Try to fit inside or slightly outside
                for text in legend.get_texts():
                    text.set_color('dimgray')

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

##################################
# CreateGroupBarChart
##################################

def CreateGroupBarChart(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    if competitorIndex == -1:
        print("Error: CreateGroupBarChart requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']

    # 0. Get the competitor's time for each event
    competitor_event_times = []
    #station_names = runtimeVars['StationList'] # Use this for x-axis labels
    station_names = runtimeVars['StationList'].copy() # Copy to avoid modifying original list 
     
    # Ensure 'Time Adj' is included 
    station_names.append('Time Adj')

    for event in station_names:
        competitor_event_times.append(df.loc[competitorIndex, event])
     
    # 1. Get competitors with similar finish times
    competitor_net_time = df.loc[competitorIndex, 'Net Time']

    lower_bound_time = competitor_net_time * (1 - rl_data.TIME_SIMILARITY_PERCENTAGE)
    upper_bound_time = competitor_net_time * (1 + rl_data.TIME_SIMILARITY_PERCENTAGE)

    similarFinishers_df = df[
        (df['Net Time'] >= lower_bound_time) & 
        (df['Net Time'] <= upper_bound_time) &
        (df.index != competitorIndex) # Exclude the competitor themselves (using index)
    ].copy() # Use .copy() to avoid SettingWithCopyWarning if you modify it later

    # 2. Get the average time for similar finishers for each event
    similar_finishers_avg_times = []
    if not similarFinishers_df.empty:
        for event in station_names:
            # Ensure we only average valid (non-NaN) times
            valid_times = similarFinishers_df[event].dropna()
            if not valid_times.empty:
                similar_finishers_avg_times.append(valid_times.mean())
            else:
                similar_finishers_avg_times.append(np.nan) # Or 0, or competitor's time as fallback
    else:
        logger.error(f"No similar finishers found for {competitor_name}.")
        # Fallback: use competitor's times or NaNs if no similar finishers
        similar_finishers_avg_times = [np.nan] * len(station_names) # Or competitor_event_times

    # --- Create Grouped Bar Chart ---
    x = np.arange(len(station_names))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots(figsize=(14, 14)) # Adjusted figsize for better label fitting

    # Plot competitor's bars
    rects1 = ax.bar(x - width/2, competitor_event_times, width, 
                    label=f"{competitor_name}'s Time", color='cornflowerblue')

    # Plot similar finishers' average bars
    # Handle potential NaNs in similar_finishers_avg_times if no similar finishers or no data for an event
    # For plotting, replace NaN with 0 or another placeholder if necessary, or filter out.
    # Here, we'll plot them, NaNs will appear as gaps if not handled by bar function.
    # A better approach is to ensure similar_finishers_avg_times has numeric values (e.g. fallback to 0 or competitor time)
    
    # Ensure similar_finishers_avg_times has numeric values for plotting
    # If an average is NaN (e.g., no similar finishers or no data for that event), 
    # you might want to plot 0, or skip that bar, or use competitor's time.
    # For this example, let's replace NaN with 0 for plotting, but indicate this limitation.
    plotable_similar_times = [0 if np.isnan(t) else t for t in similar_finishers_avg_times]

    rects2 = ax.bar(x + width/2, plotable_similar_times, width, 
                    label='Avg. Similar Finishers', color='lightcoral')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('Time (seconds)')
    ax.set_title(f'Station Time Comparison: {competitor_name} vs. {similarFinishers_df.shape[0]} Similar Finishers (+/- {rl_data.TIME_SIMILARITY_PERCENTAGE*100:.0f}% Net Time)')
    ax.set_xticks(x)
    ax.set_xticklabels(station_names, rotation=45, ha="right") # Rotate for readability
    ax.legend()

    # Function to add labels on top of bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            if not np.isnan(height) and height > 0: # Only label if height is valid and positive
                ax.annotate(f'{height:.0f}s',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)

    autolabel(rects1)
    autolabel(rects2)

    #fig.tight_layout() # Adjust layout to make room for labels

    # Set Y-axis limit slightly above the max plotted value
    all_plotted_times = [t for t in competitor_event_times + plotable_similar_times if not np.isnan(t)]
    if all_plotted_times:
        ax.set_ylim(0, max(all_plotted_times) * 1.15) # Add 15% padding
    else:
        ax.set_ylim(0,100) # Default if no data

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

##############################
# CreateCumulativeTimeComparison
##############################
def CreateCumulativeTimeComparison(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
        
    if competitorIndex == -1:
        logger.error("Error: CreateCumulativeTimeComparison requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']

    #station_names = runtimeVars['StationList']
    station_names = runtimeVars['StationList'].copy() # Copy to avoid modifying original list 
    
    # Ensure 'Time Adj' is included 
    station_names.append('Time Adj')
    
    competitor_event_times = [df.loc[competitorIndex, event] for event in station_names]

    # --- Get Similar Finishers' Average Station Times ---
    competitor_net_time = df.loc[competitorIndex, 'Net Time']
    lower_bound_time = competitor_net_time * (1 - rl_data.TIME_SIMILARITY_PERCENTAGE)
    upper_bound_time = competitor_net_time * (1 + rl_data.TIME_SIMILARITY_PERCENTAGE)
    similarFinishers_df = df[
        (df['Net Time'] >= lower_bound_time) & 
        (df['Net Time'] <= upper_bound_time) &
        (df.index != competitorIndex)
    ].copy()

    similar_finishers_avg_station_times = []
    if not similarFinishers_df.empty:
        for event in station_names:
            valid_times = similarFinishers_df[event].dropna()
            if not valid_times.empty:
                similar_finishers_avg_station_times.append(valid_times.mean())
            else:
                competitor_event_time_for_fallback = df.loc[competitorIndex, event]
                similar_finishers_avg_station_times.append(competitor_event_time_for_fallback if not np.isnan(competitor_event_time_for_fallback) else 0)
    else:
        logger.info(f"No similar finishers found for {competitor_name}. Using competitor's times for comparison line.")
        similar_finishers_avg_station_times = [t if not np.isnan(t) else 0 for t in competitor_event_times]


    # Calculate cumulative times, prepend 0 for the start
    competitor_cumulative_times = np.concatenate(([0], np.cumsum(competitor_event_times)))
    similar_finishers_cumulative_avg = np.concatenate(([0], np.cumsum(similar_finishers_avg_station_times)))
    
    x_labels = ['Start'] + station_names
    x_ticks_positions = np.arange(len(x_labels))

    fig, ax = plt.subplots(figsize=(14, 14)) # Slightly adjusted figsize for labels

    # Plot Competitor Line
    line1, = ax.plot(x_ticks_positions, competitor_cumulative_times, marker='o', linestyle='-', 
                     label=f"{competitor_name}", color='dodgerblue', linewidth=2, markersize=5)
    # Plot Similar Finishers Line
    line2, = ax.plot(x_ticks_positions, similar_finishers_cumulative_avg, marker='x', linestyle='--', 
                     label='Avg. Similar Finishers', color='lightcoral', linewidth=2, markersize=5)

    # Add mm:ss labels to each point
    for i, txt_val in enumerate(competitor_cumulative_times):
        if i > 0: # Don't label the "Start" at 00:00 unless desired
            ax.annotate(rl_data.format_time_mm_ss(txt_val), 
                        (x_ticks_positions[i], competitor_cumulative_times[i]),
                        textcoords="offset points", xytext=(0,5), ha='center', fontsize=7, color=line1.get_color())

    for i, txt_val in enumerate(similar_finishers_cumulative_avg):
        if i > 0: # Don't label the "Start"
            ax.annotate(rl_data.format_time_mm_ss(txt_val), 
                        (x_ticks_positions[i], similar_finishers_cumulative_avg[i]),
                        textcoords="offset points", xytext=(0,-12), ha='center', fontsize=7, color=line2.get_color())


    # Fill between the lines to show difference
    ax.fill_between(x_ticks_positions, competitor_cumulative_times, similar_finishers_cumulative_avg, 
                    where=competitor_cumulative_times >= similar_finishers_cumulative_avg, 
                    facecolor='lightcoral', alpha=0.2, interpolate=True) # Label removed for cleaner legend
    ax.fill_between(x_ticks_positions, competitor_cumulative_times, similar_finishers_cumulative_avg, 
                    where=competitor_cumulative_times < similar_finishers_cumulative_avg, 
                    facecolor='lightgreen', alpha=0.2, interpolate=True) # Label removed

    ax.set_xlabel("Progression through Stations", fontsize=10)
    ax.set_ylabel("Cumulative Time (mm:ss)", fontsize=10)
    ax.set_title(f"Cumulative Race Time: {competitor_name} vs. {similarFinishers_df.shape[0]} Similar Finishers (+/- {rl_data.TIME_SIMILARITY_PERCENTAGE*100:.0f}% Net Time)")
    
    ax.set_xticks(x_ticks_positions)
    ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=9)
    
    # Format Y-axis ticks as mm:ss
    # Get current y-ticks, then reformat them
    def y_fmt(tick_val, pos):
        return rl_data.format_time_mm_ss(tick_val)
    
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(y_fmt))
    ax.tick_params(axis='y', labelsize=9)

    ax.grid(True, linestyle=':', alpha=0.6)
    
    # Create legend with just the line plots
    ax.legend(handles=[line1, line2], loc='upper left', fontsize=9)

    #fig.tight_layout(pad=1.0) # Add some padding

    # Determine y-axis limits after plotting everything to ensure labels fit
    all_cumulative_data = np.concatenate([competitor_cumulative_times, similar_finishers_cumulative_avg])
    min_data_val = 0
    max_data_val = np.nanmax(all_cumulative_data) if len(all_cumulative_data[~np.isnan(all_cumulative_data)]) > 0 else 300 # Default max if no data
    ax.set_ylim(min_data_val, max_data_val * 1.1) # Add 10% padding at the top

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

##############################
# CreateStationTimeDifferenceChart
##############################
def CreateStationTimeDifferenceChart(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    if competitorIndex == -1:
        print("Error: CreateStationTimeDifferenceChart requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']
        
    #station_names = runtimeVars['StationList']
    station_names = runtimeVars['StationList'].copy() # Copy to avoid modifying original list 
    
    # Ensure 'Time Adj' is included 
    station_names.append('Time Adj')
    
    competitor_event_times = np.array([df.loc[competitorIndex, event] for event in station_names])

    # --- Get Similar Finishers' Average Station Times ---
    competitor_net_time = df.loc[competitorIndex, 'Net Time']
    lower_bound_time = competitor_net_time * (1 - rl_data.TIME_SIMILARITY_PERCENTAGE)
    upper_bound_time = competitor_net_time * (1 + rl_data.TIME_SIMILARITY_PERCENTAGE)
    similarFinishers_df = df[
        (df['Net Time'] >= lower_bound_time) & 
        (df['Net Time'] <= upper_bound_time) &
        (df.index != competitorIndex)
    ].copy()

    similar_finishers_avg_station_times = []
    if not similarFinishers_df.empty:
        for event in station_names:
            valid_times = similarFinishers_df[event].dropna()
            if not valid_times.empty:
                similar_finishers_avg_station_times.append(valid_times.mean())
            else:
                # Fallback: if no similar finishers have data, use competitor's time (so difference is 0)
                similar_finishers_avg_station_times.append(df.loc[competitorIndex, event])
    else:
        print(f"No similar finishers found for {competitor_name}. Differences will be zero.")
        similar_finishers_avg_station_times = competitor_event_times.copy() # Difference will be 0
    
    similar_finishers_avg_station_times = np.array(similar_finishers_avg_station_times)

    # Calculate time differences (Competitor Time - Avg Similar Time)
    # Negative = Competitor was faster
    # Positive = Competitor was slower
    time_differences = competitor_event_times - similar_finishers_avg_station_times
    
    # Handle potential NaNs if any avg_time was NaN and not caught by fallback
    time_differences = np.nan_to_num(time_differences, nan=0.0)


    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Colors for bars: green if faster (negative diff), red if slower (positive diff)
    colors = ['mediumseagreen' if diff <= 0 else 'salmon' for diff in time_differences]
    
    bars = ax.bar(station_names, time_differences, color=colors)

    ax.axhline(0, color='grey', linewidth=0.8) # Add a horizontal line at y=0

    ax.set_xlabel("Workout Station")
    ax.set_ylabel("Time Difference (seconds)\n[Negative = Competitor Faster]")
    ax.set_title(f'Station Time Difference: {competitor_name} vs. {similarFinishers_df.shape[0]} Similar Finishers (+/- {rl_data.TIME_SIMILARITY_PERCENTAGE*100:.0f}% Net Time)')
    
    plt.xticks(rotation=45, ha="right")

    # Add labels on top/bottom of bars
    for bar_idx, bar in enumerate(bars):
        yval = bar.get_height()
        # For labels, show absolute difference but keep sign for direction
        label_text = f"{yval:.0f}s"
        if yval < 0:
            # Place label below the bar for negative values
            ax.text(bar.get_x() + bar.get_width()/2.0, yval, label_text, 
                    va='top', ha='center', fontsize=8, color='darkgreen')
        elif yval > 0:
            # Place label above the bar for positive values
            ax.text(bar.get_x() + bar.get_width()/2.0, yval, label_text, 
                    va='bottom', ha='center', fontsize=8, color='darkred')
        # Optionally, don't label if yval is 0 or very close to 0

    # Adjust y-limits for better visualization of differences
    if len(time_differences) > 0:
        max_abs_diff = np.nanmax(np.abs(time_differences))
        if max_abs_diff == 0 : max_abs_diff = 10 # Default if all diffs are zero
        ax.set_ylim(-max_abs_diff * 1.2, max_abs_diff * 1.2)
    else:
        ax.set_ylim(-50, 50) # Default if no data

    ax.grid(True, axis='y', linestyle=':', alpha=0.7)
    #fig.tight_layout()

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

#################################
# CreateCatBarCharts
#################################

def CreateCatBarCharts(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    # Check if file exists or force generation
    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation")
        return True

    # Check if 'Category' column exists and if there's more than one unique category
    if 'Category' not in df.columns:
        logger.debug(f"Category column not found in DataFrame. Skipping chart generation Skipping for {runtimeVars['eventDataList'][0]}.")
        return False

    unique_categories = sorted(df['Category'].dropna().unique())
    if len(unique_categories) <= 1:
        logger.debug(f"Not enough categories ({len(unique_categories)}) to generate a comparison chart. Skipping for {runtimeVars['eventDataList'][0]}.")
        return False

    #print(f"Generating Average Station Time by Category chart at {filepath}")

    station_names = runtimeVars['StationList']
    num_stations = len(station_names)
    num_categories = len(unique_categories)

    # --- Data Preparation: Calculate average time per station for each category ---
    category_avg_times = {} # Dict to store: {'Category A': [avg_station1, avg_station2,...], ...}

    # Define colors - ensure you have enough for the max number of categories you expect
    # These are example colors; you can customize them
    default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    category_colors = {cat: default_colors[i % len(default_colors)] for i, cat in enumerate(unique_categories)}

    for category_name in unique_categories:
        category_df = df[df['Category'] == category_name]
        avg_times_for_this_category = []
        for event in station_names:
            if event in category_df.columns:
                valid_times = category_df[event].dropna()
                if not valid_times.empty:
                    avg_times_for_this_category.append(valid_times.mean())
                else:
                    avg_times_for_this_category.append(np.nan) # Or 0 if preferred for missing data
            else:
                avg_times_for_this_category.append(np.nan) # Event column doesn't exist for some reason
        category_avg_times[category_name] = avg_times_for_this_category
    
    # --- Plotting ---
    fig, ax = plt.subplots(figsize=(14, 14)) # Wider figure for more stations/categories

    bar_width = 0.8 / num_categories # Dynamically adjust bar width
    x_indices = np.arange(num_stations) # Base x positions for stations

    rects_list = [] # To store bar objects for legend

    for i, category_name in enumerate(unique_categories):
        offsets = (i - (num_categories - 1) / 2.0) * bar_width
        avg_times = category_avg_times[category_name]
        # Handle potential NaNs for plotting (e.g., replace with 0)
        plot_times = [0 if np.isnan(t) else t for t in avg_times] 
        
        rects = ax.bar(x_indices + offsets, plot_times, bar_width, 
                       label=category_name, color=category_colors[category_name])
        rects_list.append(rects)

        # Optional: Add text labels on top of bars (can get very crowded)
        # for bar_idx, bar_rect in enumerate(rects):
        #     height = bar_rect.get_height()
        #     if height > 0:
        #         ax.text(bar_rect.get_x() + bar_rect.get_width() / 2., height + 5, # 5s offset
        #                 f'{int(height)}s', ha='center', va='bottom', fontsize=7, rotation=0)


    ax.set_ylabel('Average Time (seconds)', fontsize=10)
    ax.set_title(f"{runtimeVars['eventDataList'][1]}\nAverage Station Times by Age Category", fontsize=14)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(station_names, rotation=45, ha="right", fontsize=9)
    ax.legend(title="Age Category", fontsize=8, title_fontsize=9, loc='upper center')

    # Determine appropriate y-limit
    max_avg_time_plotted = 0
    for cat_times in category_avg_times.values():
        valid_cat_times = [t for t in cat_times if not np.isnan(t)]
        if valid_cat_times:
            max_avg_time_plotted = max(max_avg_time_plotted, max(valid_cat_times))
    
    ax.set_ylim(0, max_avg_time_plotted * 1.15 if max_avg_time_plotted > 0 else 100) # Add 15% padding

    ax.grid(True, axis='y', linestyle=':', alpha=0.7)
    #fig.tight_layout()

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

#############################
## CreatePacingTable
#############################
   
def CreatePacingTable(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation")
        return True
    
    #logger.debug(f"Generating Pacing Table for event {runtimeVars['eventDataList'][0]}")

    station_names = runtimeVars['StationList']
    num_stations = len(station_names)
    if num_stations == 0:
        logger.error("Error: StationList is empty. Cannot generate pacing table.")
        return False

    target_percentiles = np.arange(0.1, 1.0, 0.1) 
    COHORT_POSITION_WINDOW_PERCENTAGE = 0.05

    # --- Data Preparation and Cleaning ---
    df_cleaned = df.copy()
    df_cleaned['Net Time'] = pd.to_numeric(df_cleaned['Net Time'], errors='coerce')
    for event in station_names:
        df_cleaned[event] = pd.to_numeric(df_cleaned[event], errors='coerce')
    
    if 'Time Adj' in df_cleaned.columns:
        df_cleaned['Time Adj'] = pd.to_numeric(df_cleaned['Time Adj'], errors='coerce')
    else:
        df_cleaned['Time Adj'] = 0 

    df_cleaned.dropna(subset=['Net Time'], inplace=True)
    if df_cleaned.empty:
        logger.error("No valid numeric Net Time data to generate pacing table.")
        return False

    #df_for_pacing_calcs = df_cleaned[df_cleaned['Time Adj'].fillna(0) == 0].copy()
    #df_to_use_for_cohorts_and_percentiles = df_for_pacing_calcs
    df_to_use_for_cohorts_and_percentiles = df_cleaned
    #if df_for_pacing_calcs.empty:
    #    print("Warning: No athletes found with Time Adj == 0. Pacing table will be based on all athletes.")
    #    df_to_use_for_cohorts_and_percentiles = df_cleaned
    #    if df_to_use_for_cohorts_and_percentiles.empty:
    #        logger.error("Critical: No data left. Cannot generate table.")
    #        return False
    
    df_sorted = df_to_use_for_cohorts_and_percentiles.sort_values(by='Net Time').reset_index(drop=True)
    total_ranked_athletes = len(df_sorted)

    if total_ranked_athletes == 0:
        logger.error("No ranked athletes to process after filtering.")
        return False

    raw_avg_station_times_data = {station: {} for station in station_names}
    target_net_times_for_columns = {}

    for p_val in target_percentiles:
        percentile_key_name = f'Top {int(p_val*100)}%'
        target_net_time_for_percentile = df_to_use_for_cohorts_and_percentiles['Net Time'].quantile(p_val)
        target_net_times_for_columns[percentile_key_name] = target_net_time_for_percentile
        
        if pd.isna(target_net_time_for_percentile):
            for station in station_names:
                raw_avg_station_times_data[station][percentile_key_name] = np.nan
            continue

        lower_rank_percentile = max(0, p_val - COHORT_POSITION_WINDOW_PERCENTAGE)
        upper_rank_percentile = min(1, p_val + COHORT_POSITION_WINDOW_PERCENTAGE)
        start_index = int(lower_rank_percentile * total_ranked_athletes)
        end_index = int(np.ceil(upper_rank_percentile * total_ranked_athletes))
        end_index = min(end_index, total_ranked_athletes)

        #logger.info(f"Processing {percentile_key_name} {total_ranked_athletes}, {start_index}, {end_index} ")

        if start_index >= end_index and total_ranked_athletes > 0:
            target_index = int(p_val * (total_ranked_athletes -1) )
            num_either_side = max(1, int(COHORT_POSITION_WINDOW_PERCENTAGE * total_ranked_athletes / 2))
            start_index = max(0, target_index - num_either_side)
            end_index = min(total_ranked_athletes, target_index + num_either_side + 1)

        cohort_df = df_sorted.iloc[start_index:end_index]
      
        cohort_df = cohort_df[cohort_df['Time Adj'].fillna(0) == 0].copy()
        if cohort_df.empty:
            logger.info("Warning: No athletes found with Time Adj == 0 for percentile {percentile_key_name} .")

        
        #df_for_pacing_calcs = df_cleaned[df_cleaned['Time Adj'].fillna(0) == 0].copy()
        #df_to_use_for_cohorts_and_percentiles = df_for_pacing_calcs
        #if df_for_pacing_calcs.empty:
        #    print("Warning: No athletes found with Time Adj == 0. Pacing table will be based on all athletes.")
        #    df_to_use_for_cohorts_and_percentiles = df_cleaned
        #    if df_to_use_for_cohorts_and_percentiles.empty:
        #        print("Critical: No data left. Cannot generate table.")
        #        return False
        
        for station in station_names:
            avg_station_time_seconds = np.nan
            if not cohort_df.empty and station in cohort_df.columns:
                valid_station_times = cohort_df[station].dropna()
                if not valid_station_times.empty:
                    avg_station_time_seconds = valid_station_times.mean()
            raw_avg_station_times_data[station][percentile_key_name] = avg_station_time_seconds

    # --- Truing-Up Logic ---
    adjusted_station_times_data = {station: {} for station in station_names}
    # This will store the sum of the *final adjusted* station times for each percentile
    final_sum_of_adjusted_station_times = {} 

    for p_key in target_net_times_for_columns.keys():
        target_net_time_col = target_net_times_for_columns[p_key]
        if pd.isna(target_net_time_col):
            for station in station_names:
                adjusted_station_times_data[station][p_key] = np.nan
            final_sum_of_adjusted_station_times[p_key] = np.nan # Store NaN for this column's sum
            continue

        current_sum_of_raw_avgs = 0
        valid_station_count_for_sum = 0
        for station in station_names:
            raw_avg = raw_avg_station_times_data[station].get(p_key, np.nan)
            if not pd.isna(raw_avg):
                current_sum_of_raw_avgs += raw_avg
                valid_station_count_for_sum += 1
        
        if valid_station_count_for_sum == 0:
            for station in station_names:
                adjusted_station_times_data[station][p_key] = np.nan
            final_sum_of_adjusted_station_times[p_key] = np.nan # Store NaN
            continue

        difference = target_net_time_col - current_sum_of_raw_avgs
        # Apply sign of difference to the rounding buffer
        rounding_buffer = 6 if difference >= 0 else -6
        diff_per_station = (difference + rounding_buffer) / num_stations

        current_col_adjusted_sum = 0 # Initialize sum for this percentile column
        for station in station_names:
            raw_avg = raw_avg_station_times_data[station].get(p_key, np.nan)
            if not pd.isna(raw_avg):
                adjusted_time = raw_avg + diff_per_station
                # Ensure adjusted times are not negative
                final_adjusted_time_for_station = max(0, adjusted_time)
                adjusted_station_times_data[station][p_key] = final_adjusted_time_for_station
                current_col_adjusted_sum += final_adjusted_time_for_station # Sum the final adjusted values
            else:
                adjusted_station_times_data[station][p_key] = np.nan
        
        final_sum_of_adjusted_station_times[p_key] = current_col_adjusted_sum # Store the precise sum

    # --- Prepare data for output table ---
    pacing_table_data_list_of_dicts = []
    header_dict = {'Station': 'Station'}
    for p_val_float in target_percentiles:
        header_dict[f'Top {int(p_val_float*100)}%'] = f'Top {int(p_val_float*100)}%'
    pacing_table_data_list_of_dicts.append(header_dict)

    for station in station_names:
        station_pacing_row = {'Station': station}
        for p_key in target_net_times_for_columns.keys():
            adjusted_time_val = adjusted_station_times_data[station].get(p_key, np.nan)
            station_pacing_row[p_key] = rl_data.format_time_mm_ss(adjusted_time_val)
        pacing_table_data_list_of_dicts.append(station_pacing_row)

    # Sum of *Adjusted* Average Station Times row - uses the re-calculated sum
    sum_adjusted_station_times_row = {'Station': 'TARGET TIME'} # Clarified label
    for p_key in target_net_times_for_columns.keys(): # Ensure consistent column order
        sum_val = final_sum_of_adjusted_station_times.get(p_key, np.nan)
        sum_adjusted_station_times_row[p_key] = rl_data.format_time_mm_ss(sum_val)
    pacing_table_data_list_of_dicts.append(sum_adjusted_station_times_row)

    #excluding actual target time...
    # Target Net Time (Quantile) row
    #target_net_time_quantiles_row = {'Station': 'TARGET NET TIME (Quantile)'}
    #for p_key, time_val in target_net_times_for_columns.items():
    #    target_net_time_quantiles_row[p_key] = rl_data.format_time_mm_ss(time_val)
    #pacing_table_data_list_of_dicts.append(target_net_time_quantiles_row)
    
    if pacing_table_data_list_of_dicts:
        df_columns = list(header_dict.values())
        data_for_df = []
        for row_dict_idx in range(1, len(pacing_table_data_list_of_dicts)):
            row_data = []
            current_row_dict = pacing_table_data_list_of_dicts[row_dict_idx]
            for col_header_val in df_columns: # Iterate in the order of headers
                 row_data.append(current_row_dict.get(col_header_val, "N/A")) # Use .get for safety
            data_for_df.append(row_data)

        pacing_df_for_csv = pd.DataFrame(data_for_df, columns=df_columns)
        
        try:
            pacing_df_for_csv.to_csv(filepath, index=False)
            #logger.debug(f"Saved pacing table to {filepath}")
        except Exception as e:
            logger.error(f"Error saving pacing table to CSV: {e}")
    else:
        logger.error("No pacing table data generated to save.")

    return pacing_table_data_list_of_dicts

###############################
#
# Non Standard output function! Non standard because the df is pacing table.
#
# CreatePacingPng
#
###############################

def CreatePacingPng(df_input_pacing_table, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()
    # config = session.get('ouptut_config', {}) # If needed for forcePng

    if os.path.isfile(filepath): # and not config.get('forcePng', False):
        logger.debug(f"Pacing chart {filepath} already exists. Skipping generation.")
        return True

    if df_input_pacing_table is None or df_input_pacing_table.empty:
        logger.error("Input pacing table DataFrame is empty or None. Cannot generate chart.")
        return False
        
    event_display_name = runtimeVars.get('eventDataList', [None, "Event Unknown"])[1]
    #logger.debug(f"Generating Pacing PNG for event {event_display_name} at {filepath}")

    df_pacing = df_input_pacing_table.copy()

    if 'Station' in df_pacing.columns:
        df_pacing.set_index('Station', inplace=True)
    
    excluded_summary_rows = ['TARGET NET TIME', 'SUM OF (ADJUSTED) STATION TIMES', 'TARGET TIME']
    rows_to_drop = [row for row in excluded_summary_rows if row in df_pacing.index]
    if rows_to_drop:
        df_pacing.drop(rows_to_drop, inplace=True)

    if df_pacing.empty:
        # ... (handling for empty plot as before) ...
        logger.error("Pacing table is empty after removing summary rows. No stations to plot.")
        fig, ax = plt.subplots(figsize=(14, 9))
        ax.text(0.5, 0.5, "No station pacing data available to plot.", 
                horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title(f"{event_display_name}\nPacing Guide - No Data", fontsize=15, pad=20)
        try:
            plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2); plt.close(fig)
        except Exception as e: logger.critical(f"Error saving empty pacing chart {filepath}: {e}"); plt.close(fig)
        return True

    percentile_columns = [col for col in df_pacing.columns if str(col).startswith('Top ')]
    if not percentile_columns:
        logger.critical("No percentile columns found in the processed pacing table DataFrame.")
        return False
        
    def time_str_to_seconds(time_str):
        if pd.isna(time_str) or not isinstance(time_str, str) or str(time_str).lower() == 'n/a': return np.nan
        try:
            parts = str(time_str).split(':')
            if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
            return np.nan 
        except ValueError: return np.nan

    for col in percentile_columns:
        df_pacing[col] = df_pacing[col].apply(time_str_to_seconds).astype(float)

    stations_to_plot = df_pacing.index.tolist()
    
    fig, ax = plt.subplots(figsize=(14, 10)) # Increased height slightly for labels
    
    num_station_lines = len(stations_to_plot)
    palette = sns.color_palette("husl", num_station_lines) if num_station_lines > 0 else []
    
    x_values_numeric = np.arange(len(percentile_columns)) # For positioning text

    for i, station in enumerate(stations_to_plot):
        if station in df_pacing.index:
            station_data_seconds = df_pacing.loc[station, percentile_columns]
            x_values_labels = [str(col).replace('Top ', '').replace('% Pace', '%') for col in percentile_columns] # Shorter labels for x-axis
            
            line_color = palette[i % len(palette)] if palette else 'blue' # Default color if palette fails

            if not station_data_seconds.isna().all():
                line, = ax.plot(x_values_labels, station_data_seconds.values, 
                                marker='o', markersize=4, linestyle='-', linewidth=1.5, 
                                label=station, color=line_color) # Store line object if needed for legend
                
                # Add direct label to the line
                # Position label near the last valid data point of the line
                last_valid_idx = None
                for k in range(len(station_data_seconds.values) - 1, -1, -1):
                    if pd.notna(station_data_seconds.values[k]):
                        last_valid_idx = k
                        break
                
                if last_valid_idx is not None:
                    x_pos = x_values_numeric[last_valid_idx]
                    y_pos = station_data_seconds.values[last_valid_idx]
                    
                    # Small offset to avoid overlapping the line/marker
                    # Adjust dx, dy based on line slope or position for better placement
                    # For simplicity, a small horizontal offset
                    ax.text(x_pos + 0.1, y_pos, station, fontsize=7.5, color=line_color,
                            verticalalignment='center', horizontalalignment='left',
                            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.6))


    ax.set_xlabel("Target Finish Percentile", fontsize=11)
    ax.set_ylabel("Average Station Pace (mm:ss)", fontsize=11)
    ax.set_title(f"{event_display_name}\nStation Pacing Guide by Target Finish Percentile", fontsize=14, pad=15)
    
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(rl_data.format_time_mm_ss))
    
    ax.tick_params(axis='x', rotation=30, labelsize=8.5, pad=5)
    ax.tick_params(axis='y', labelsize=8.5)
    
    ax.grid(True, linestyle=':', alpha=0.5)
    
    # Legend is now less critical due to direct labels, but can be kept as an option
    # If kept, make it very subtle or place it well outside. For now, let's disable it
    # as direct labels are preferred for accessibility.
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=min(6, num_station_lines), fancybox=True, shadow=False, fontsize=7)

    # Adjust layout to make space for direct labels if they go outside plot area
    # And to ensure title and axis labels are not cramped
    fig.subplots_adjust(left=0.1, right=0.9, top=0.90, bottom=0.15) # Adjust right to give space for labels


    try:
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        #logger.info(f"Saved pacing chart with direct line labels to {filepath}")
        plt.close(fig)
        return True
    except Exception as e:
        logger.critical(f"Error saving pacing chart {filepath}: {e}")
        if 'fig' in locals(): plt.close(fig)
        return False

###############################
#
# Non Standard output function! 
#
# MakeFullPdfReport
#
###############################

def MakeFullPdfReport(filepath, outputDict, html_filepath, competitorAnalysis ):

    logger = rl_data.get_logger()
 
    if os.path.isfile(filepath):
        #logger.debug(f"File {filepath} already exists. Skipping generation")
        return True

    try:
        #in theorey this could all gointo a separate fucntion
        doc = pymupdf.open()  # PDF with the text pictures

        #first output text (Can work on format)
        rect_x1 = 50
        rect_y1 = 50
        rect_x2 = 800  # trial
        rect_y2 = 800 # error
        rect = (rect_x1, rect_y1, rect_x2, rect_y2)

        # if competitor Analysis enabled.
        if(competitorAnalysis == True):
            page = doc.new_page()

            #open html file html_info_comp_filepaths
            with open(html_filepath, 'r') as f:
                stringHtml = f.read()
            page.insert_htmlbox(rect, stringHtml)

        for i, f_path_str in enumerate(outputDict['filename']):
            if (".png" in f_path_str): # Check extension case-insensitively
                #logger.debug(f"Processing image for PDF: {f_path_str}")
                try:
                    img_doc = pymupdf.open(f_path_str)  # Open to get dimensions
                    img_rect = img_doc[0].rect
                    img_doc.close()

                    page = doc.new_page(width=img_rect.width, height=img_rect.height)
                    page.insert_image(img_rect, filename=f_path_str) # Direct insertion
                except Exception as e:
                    logger.critical(f"Error processing image {f_path_str} for PDF: {e}")
            else:
                logger.info(f"File type not supported for PDF image insertion: {f_path_str}")
            
        doc.save(filepath, garbage=4, deflate=True)
        logger.debug(f"Saving PDF {filepath}")
        return True
    
    except Exception as e:
        logger.critical(f"Error creating PDF {filepath}: {e}", exc_info=True)

#############################
# Show Scatter Plot
#############################
def ShowScatterPlot(df, filepath, runtimeVars, stationName, competitorIndex ):
    
    logger = rl_data.get_logger()

    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        #logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    #remove category for corralation info
    dfcorr = df.copy(deep=True)

    #next level tidying for correlation
    tidyTheDataCorr(dfcorr, runtimeVars)

    #get corrolation info
    corr_matrix = dfcorr.corr().at[stationName,'Net Time']

    q1ListX = [] #fastest quatile
    q2ListX = []
    q3ListX = []
    q4ListX = [] #slowest quatile

    q1ListY = [] #fastest quatile
    q2ListY = []
    q3ListY = []
    q4ListY = [] #slowest quatile
    maxPos=0

    # For each competitor.
    for index in df.index:

        if df[stationName][index] <  df[stationName].quantile(0.25) :
            #Add to fastest quartile list
            q1ListX.append(df[stationName][index])
            q1ListY.append(df['Pos'][index])
            if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]
        
        elif df[stationName][index] <  df[stationName].quantile(0.50) :
            #Add to q2 list
            q2ListX.append(df[stationName][index])
            q2ListY.append(df['Pos'][index])
            if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]
            
        elif df[stationName][index] <  df[stationName].quantile(0.75) :
            #Add to q3 list
            q3ListX.append(df[stationName][index])
            q3ListY.append(df['Pos'][index])
            if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]

        elif df[stationName][index] <  df[stationName].quantile(0.98):
            #Add to slowest quartile list
            q4ListX.append(df[stationName][index])
            q4ListY.append(df['Pos'][index])
            if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]

    plt.figure(figsize=(10, 10))

    plt.scatter(x=q1ListX, y=q1ListY, c ="blue",  label="0%-24%")
    plt.scatter(x=q2ListX, y=q2ListY, c ="brown", label="25%-49%")
    plt.scatter(x=q3ListX, y=q3ListY, c ="green", label="50%-74%")
    plt.scatter(x=q4ListX, y=q4ListY, c ="red",   label="75%-98%")
    
    if (competitorIndex != -1):
        plt.plot([df.loc[competitorIndex,stationName]], [df.loc[competitorIndex,'Pos']], marker='+', markersize=20.0, markeredgewidth=2.0, color='navy', linewidth=0.0)

        #coorinates via trial an error.
        plt.text(df[stationName].min()*1.1, maxPos+1.0,'+='+ df.loc[competitorIndex,'Name'] , fontsize = 10, color='navy')

    #conver corr float to str
    if (corr_matrix):
        corrstr = "{:1.2f}".format(corr_matrix)
    
    plt.title(runtimeVars['eventDataList'][1] + ' ' + stationName + ' Corr. ' + corrstr)
    plt.ylabel("Ovearll Position")
    plt.xlabel("Station Time")
    plt.legend()
    plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

    # Output/Show depending of global variable setting. 
    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
    plt.close()

    return True

# Chart creatation above this line.
#######################################################################################


#############################
#############################
# This function will now be the primary one to prepare data for any visual page
# that might use lazy loading (even if images are pre-generated).
#############################
#############################

def prepare_visualization_data_for_template( competitorDetails):
    logger = rl_data.get_logger()

    runtimeVars = session.get('runtime', {})
    outputVars = session.get('output_config', {}) 
    
    pending_image_tasks = []
    ready_outputs_content = [] # For non-image content like HTML tables, download links

    event_name_slug = slugify(competitorDetails['event'])
    competitor_name_slug = "generic"
    
    for element in rl_data.EVENT_DATA_LIST: 
        if element[0] == competitorDetails['event']:
            runtimeVars['eventDataList'] = element
            break

    if not runtimeVars['eventDataList']:
        logger.critical(f"Event details not found for: {competitorDetails['event']}")
        return render_template("error.html", message=f"Event configuration for {competitorDetails['event']} not found.")

    # Configure StationList based on year
    if runtimeVars['eventDataList'][2]=="2023": # Assuming index 2 is year
        runtimeVars['StationList'] = rl_data.STATIONLIST23
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART23
    elif runtimeVars['eventDataList'][2]=="2024":
        runtimeVars['StationList'] = rl_data.STATIONLIST24
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART24
    elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][5]=="KL":
        runtimeVars['StationList'] = rl_data.STATIONLIST25
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART25
    elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][7]=="CRU_FIT_GAM" :
        runtimeVars['StationList'] = rl_data.STATIONLISTCRU25
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTARTCRU25
    else:
        logger.error(f"ERROR: Event not found {runtimeVars['eventDataList'][2]} {runtimeVars['eventDataList'][5]} {runtimeVars['eventDataList'][7]}") 

        
    logger.info(f"Preparing event page: {runtimeVars['eventDataList'][0]}")
   
    # --- End of Essential Setup ---
    # --- Start of Main Processing ---

    # Store minimal snapshot for async calls if needed (though for pre-generated, less critical)
    session['async_runtime_vars_snapshot'] = {
        'eventDataList': runtimeVars['eventDataList'],
        'StationList': runtimeVars['StationList'],
        'competitorName': None,
        'competitorRaceNo': None
    }

    if outputVars.get('competitorAnalysis', False):
        logger.critical("competitorAnalysis is not supported for generic page.")
        return render_template("error.html", message=f"competitorAnalysis is not supported for generic page.")

    for output_conf in OUTPUT_CONFIGS:
        
        # Competitor not supported
        if  output_conf['is_competitor_specific']:
            #skip
            continue
                
        # Check if this output type is enabled
        if not outputVars.get(output_conf['id'], False): 
            continue

        output_dir_path_obj = Path(getattr(rl_data, output_conf['output_dir_const']))
        
        #if this function requires category data, but event has none, then skip
        if output_conf['requires_category_data'] == True and runtimeVars['eventDataList'][6] == "NO_CAT":
                logger.debug(f"No category data, skipping {output_conf['id']} {output_conf['function_name']} {output_conf['id']} {output_conf['output_dir_const']} {output_conf['filename_template']}")
                pass
      
        # --- Handle PNGs and PNG Collections for Lazy Loading ---
        elif output_conf['output_type'] == 'png' or output_conf['output_type'] == 'png_collection':
            items_to_generate_for_this_conf = []
            # ... (your existing logic for populating items_to_generate_for_this_conf) ...
            if output_conf['generates_multiple_files']:
                num_files_key = output_conf.get('num_files_generated_key')
                iteration_items = runtimeVars.get(num_files_key, []) if num_files_key else ["default_item_for_multi"]
                for item_name in iteration_items:
                    items_to_generate_for_this_conf.append({'station_name': item_name if num_files_key else None})
            else:
                items_to_generate_for_this_conf.append({'station_name': None})

            for item_params in items_to_generate_for_this_conf:
                station_name_actual = item_params['station_name']
                station_name_slug = slugify(station_name_actual) if station_name_actual else ""

                current_filename = output_conf['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug,
                    STATION_NAME_SLUG=station_name_slug
                ).replace("__", "_").replace("_.", ".")
                
                full_disk_path = output_dir_path_obj / Path(current_filename)
                final_image_url = url_for('static', filename=str(output_dir_path_obj / Path(current_filename)))
                placeholder_id = f"ph_{output_conf['id']}_{event_name_slug}_{station_name_slug}".replace("__","_").rstrip('_')
                
                display_name = output_conf['name']
                if station_name_actual: display_name += f" - {station_name_actual}"
                
                # CRITICAL: Check if file exists on disk
                image_exists_on_disk = os.path.isfile(full_disk_path)

                pending_image_tasks.append({
                    'placeholder_id': placeholder_id,
                    'display_name': display_name,
                    'html_description': output_conf['html_string_template'].format(
                                            EVENT_NAME=runtimeVars['eventDataList'][1]),
                    'generation_params': { # These are sent to the AJAX endpoint
                        'output_id': output_conf['id'],
                        'event_name_actual': runtimeVars['eventDataList'][0],
                        'competitor_name_actual': runtimeVars.get('competitorName'),
                        'competitor_race_no_actual': runtimeVars.get('competitorRaceNo'),
                        'station_name_actual': station_name_actual,
                        'target_filename': current_filename 
                    },
                    'expected_image_url': final_image_url,
                    'image_already_exists': image_exists_on_disk # This is the key for this variation
                })
    
    # Sort tasks by priority if you have 'load_priority' in OUTPUT_CONFIGS
    if pending_image_tasks:
        pending_image_tasks.sort(key=lambda task: task.get('load_priority', 99))

    page_title = runtimeVars['eventDataList'][1]

    return {
        "title": page_title,
        "pending_image_tasks": pending_image_tasks,
        "ready_content_list": ready_outputs_content,
        "event_name": runtimeVars['eventDataList'][1],
        "competitorDetails":  None 
    }


#############################
#############################
# This is your new main entry point when a user requests a competitor page
#############################

def prepare_competitor_visualization_page(competitorDetails):
    logger = rl_data.get_logger()
    
    runtimeVars = session.get('runtime', {})
    outputVars = session.get('output_config', {}) 

    # --- 1. Essential Setup: Event details, DF loading, Competitor Index ---
    if not outputVars.get('competitorAnalysis'):
        logger.critical("prepare_competitor_visualization_page called without competitorAnalysis True in config.")
        return render_template("error.html", message="Configuration error.")

    for element in rl_data.EVENT_DATA_LIST: 
        if element[0] == competitorDetails['event']:
            runtimeVars['eventDataList'] = element
            break
        
    if not runtimeVars.get('eventDataList'):
        logger.critical(f"Event details not found for: {competitorDetails['event']}")
        return render_template("error.html", message=f"Event configuration for {competitorDetails['event']} not found.")

    # Configure StationList based on year
    if runtimeVars['eventDataList'][2]=="2023": # Assuming index 2 is year
        runtimeVars['StationList'] = rl_data.STATIONLIST23
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART23
    elif runtimeVars['eventDataList'][2]=="2024":
        runtimeVars['StationList'] = rl_data.STATIONLIST24
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART24
    elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][5]=="KL":
        runtimeVars['StationList'] = rl_data.STATIONLIST25
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART25
    elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][7]=="CRU_FIT_GAM" :
        runtimeVars['StationList'] = rl_data.STATIONLISTCRU25
        runtimeVars['StationListStart'] = rl_data.STATIONLISTSTARTCRU25
    else:
        logger.error(f"ERROR: Event not found {runtimeVars['eventDataList'][2]} {runtimeVars['eventDataList'][5]} {runtimeVars['eventDataList'][7]}") 

    logger.info(f"Preparing competitor page for event: {runtimeVars['eventDataList'][0]}")
    
    indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(runtimeVars['eventDataList'][0] + '.csv')
    try:
        df_raw = pd.read_csv(indatafile)
        df = prepare_data_for_processing(df_raw)
        tidyTheData(df=df, filename=indatafile)
    except FileNotFoundError:
        logger.critical(f"Data file not found: {indatafile}")
        return render_template("error.html", message=f"Data file not found for {runtimeVars['eventDataList'][0]}.")
    except Exception as e:
        logger.critical(f"Error tidying data for {indatafile}: {e}", exc_info=True)
        return render_template("error.html", message="Error processing event data.")

    runtimeVars['competitorName'] = competitorDetails.get('competitor')
    runtimeVars['competitorRaceNo'] = competitorDetails.get('race_no')
    
    competitorIndex = getCompetitorIndex(df=df)
    if competitorIndex == -1:
        logger.error(f"Competitor {runtimeVars['competitorName']} not found in {runtimeVars['eventDataList'][0]}.")
        return render_template("error.html", message=f"Competitor {runtimeVars['competitorName']} completed data not found in {runtimeVars['eventDataList'][0]}.")
    
    # --- End of Essential Setup ---

    pending_image_tasks = []
    ready_outputs_content = [] # For HTML snippets like the info table

    event_name_slug = slugify(runtimeVars['eventDataList'][0])
    competitor_name_slug = slugify(runtimeVars['competitorName'])

    # Store necessary parts of runtimeVars for the async endpoint
    # Only store what's absolutely needed to reconstruct context for generating a single image
    session['async_runtime_vars_snapshot'] = {
        'eventDataList': runtimeVars['eventDataList'],
        'StationList': runtimeVars['StationList'],
        'competitorName': runtimeVars['competitorName'],
        'competitorRaceNo': runtimeVars['competitorRaceNo']
        # Avoid storing the large 'df' in session if possible. Reload it in the async endpoint.
    }


    for output_conf in OUTPUT_CONFIGS:
        if not outputVars.get(output_conf['id'], False): 
            logger.info(f"Skipping {output_conf['id']} for {runtimeVars['eventDataList'][0]} with {outputVars.get(output_conf['id'], False)}")
            continue # Skip if not enabled in config
        else:
            logger.info(f"Generating {output_conf['id']} for {runtimeVars['eventDataList'][0]} with {outputVars.get(output_conf['id'], False)}")
        
        if not output_conf['is_competitor_specific']: 
            logger.info(f"Skipping {output_conf['id']} competitor {output_conf['is_competitor_specific']}")
            continue # Only competitor specific items for this route
        else:
            logger.info(f"Generating {output_conf['id']} competitor {output_conf['is_competitor_specific']}")
            
        # --- Filename and URL Construction ---
        # This will be used by JavaScript to know the final URL, and by the async endpoint to save the file
        output_dir_path_obj = Path(getattr(rl_data, output_conf['output_dir_const']))

        if output_conf['id'] == 'html_info_comp':
            # Generate this HTML snippet directly as it's small and part of initial page
            # Assuming GenerateCompInfoTable returns the HTML string or saves to a temp file read here
            # For simplicity, let's assume it can return HTML string.
            # Filepath here is more for if it *were* to save, but we need the HTML content.
            temp_html_filename = output_conf['filename_template'].format(
                EVENT_NAME_SLUG=event_name_slug,
                COMPETITOR_NAME_SLUG=competitor_name_slug)
            temp_html_filepath = output_dir_path_obj / temp_html_filename
            
            html_content = GenerateCompInfoTable(df=df, filepath=temp_html_filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex)
            if html_content: # Assuming GenerateCompInfoTable returns the HTML string
                ready_outputs_content.append({
                    'id': output_conf['id'],
                    'name': output_conf['name'],
                    'html': html_content
                })
            continue # Move to next output_conf

        if output_conf['output_type'] == 'pdf_download':
            # For PDFs, we'll provide a button/link that triggers generation on click via AJAX
            pdf_filename = output_conf['filename_template'].format(
                EVENT_NAME_SLUG=event_name_slug,
                COMPETITOR_NAME_SLUG=competitor_name_slug
            )
            # The FILE_URL will point to an endpoint that generates and serves the PDF
            # e.g., /download_pdf?type=competitor_pdf_report&event=...&competitor=...
            pdf_generation_trigger_url = url_for('generate_and_download_pdf_route', 
                                                 output_id=output_conf['id'],
                                                 event_name_actual=runtimeVars['eventDataList'][0],
                                                 competitor_name_actual=runtimeVars['competitorName'],
                                                 competitor_race_no_actual=runtimeVars['competitorRaceNo']
                                                 )
            
            html_desc = output_conf['html_string_template'].format(
                FILE_URL=pdf_generation_trigger_url, # This is now a trigger URL
                EVENT_NAME=runtimeVars['eventDataList'][1],
                COMPETITOR_NAME=runtimeVars['competitorName']
            ).replace("{FILE_URL}\" download", f"{pdf_generation_trigger_url}\" target=\"_blank\"") # Open in new tab
            ready_outputs_content.append({'id': output_conf['id'], 'name': output_conf['name'], 'html': html_desc})
            continue
    
        if output_conf['id'] == 'html_note_comp':
            html_desc = output_conf['html_string_template'].format(
                EVENT_DESCRIPTION=runtimeVars['eventDataList'][1],
                EVENT_LINK=runtimeVars['eventDataList'][0],
            )
            ready_outputs_content.append({'id': output_conf['id'], 'name': output_conf['name'], 'html': html_desc})
            continue

        # Handle PNGs and PNG Collections for lazy loading
        if output_conf['output_type'] == 'png' or output_conf['output_type'] == 'png_collection':
            items_to_generate_for_this_conf = []
            if output_conf['generates_multiple_files']:
                num_files_key = output_conf.get('num_files_generated_key')
                iteration_items = runtimeVars.get(num_files_key, []) if num_files_key else ["default"]
                for item_name in iteration_items:
                    items_to_generate_for_this_conf.append({'station_name': item_name if num_files_key else None})
                    #logger.info(f"Generateing {output_conf['id']} item_name: {item_name}")
            else:
                items_to_generate_for_this_conf.append({'station_name': None}) # Single file
            #logger.info(f"Generateing {output_conf['id']} items_to_generate_for_this_conf: {items_to_generate_for_this_conf}")
         
            for item_params in items_to_generate_for_this_conf:
                station_name = item_params['station_name']
                station_name_slug = slugify(station_name) if station_name else ""

                current_filename = output_conf['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug,
                    COMPETITOR_NAME_SLUG=competitor_name_slug,
                    STATION_NAME_SLUG=station_name_slug
                ).replace("__", "_").replace("_.", ".") # Clean up potential double underscores or trailing if station is empty

                placeholder_id = f"ph_{output_conf['id']}_{event_name_slug}_{competitor_name_slug}_{station_name_slug}".replace("__","_").rstrip('_')
                
                # Construct the final URL the image will have once generated
                # Ensure rl_data.APP_STATIC_FOLDER is defined as the absolute path to your static folder
                final_image_url = url_for('static', filename=str(output_dir_path_obj / Path(current_filename)))
                
                display_name = output_conf['name']
                if station_name:
                    display_name += f" - {station_name}"
                
                # Check if image already exists to potentially serve it immediately or skip AJAX
                full_disk_path = Path(output_dir_path_obj) / current_filename
                image_already_exists = os.path.isfile(full_disk_path)

                #logger.info(f"Generateing {output_conf['id']} full_disk_path: {full_disk_path}")
                
                pending_image_tasks.append({
                    'placeholder_id': placeholder_id,
                    'display_name': display_name,
                    'html_description': output_conf['html_string_template'].format(
                                            EVENT_NAME=runtimeVars['eventDataList'][1],
                                            COMPETITOR_NAME=runtimeVars['competitorName']),
                    'generation_params': { # Params for the AJAX POST request
                        'output_id': output_conf['id'],
                        'event_name_actual': runtimeVars['eventDataList'][0], # Pass actual event name
                        'competitor_name_actual': runtimeVars['competitorName'],
                        'competitor_race_no_actual': runtimeVars['competitorRaceNo'],
                        'station_name_actual': station_name, # Will be None if not a per-station chart
                        'target_filename': current_filename # For the server to know what to generate
                    },
                    'expected_image_url': final_image_url,
                    'image_already_exists': image_already_exists, # New flag for JS
                    'load_priority': output_conf.get('load_priority', 99) # Get priority, default to low if missing
                })
                
                # After populating pending_image_tasks, sort it:
                if pending_image_tasks:
                    pending_image_tasks.sort(key=lambda task: task.get('load_priority', 99)) 
                    # Using .get with a default ensures sorting doesn't fail if priority is missing for an item
    
    # Save runtimeVars that might have been updated by setup
    session['runtime'] = runtimeVars 
    session['output_config'] = outputVars

    page_title = runtimeVars['eventDataList'][1]
    if runtimeVars.get('competitorName'):
        page_title += f" - {runtimeVars['competitorName']}"

    return render_template('visual_lazy_load.html', 
                           title=page_title,
                           pending_image_tasks=pending_image_tasks,
                           ready_content_list=ready_outputs_content,
                           event_name=runtimeVars['eventDataList'][1]
                           )

# This function will be called via AJAX by the client for each image
# Or by a background task system
def generate_single_output_file(params): # df_override for testing or specific cases
    logger = rl_data.get_logger()
    # Reload necessary context from session or pass minimally via params
    # For simplicity, we'll assume session still holds some relevant info if needed,
    # but ideally, params should be self-sufficient or df reloaded.
    #runtimeVars = session.get('runtime', {}) # Could be a snapshot stored specifically for async tasks
    #general_config = session.get('output_config', {})
    
    # Get specific output configuration
    output_id = params.get('output_id')
    output_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == output_id), None)
    if not output_conf:
        logger.critical(f"No output configuration found for id: {output_id}")
        return {"success": False, "error": "Invalid output configuration."}

    # Reconstruct necessary runtime variables (or ensure they are passed/retrieved correctly)
    # This part is critical: the async task needs the same context as the sync generation
    event_name_actual = params.get('event_name_actual')
    
    # Construct filepath
    event_name_slug = slugify(event_name_actual)
    competitor_name_slug = slugify(params.get('competitor_name_actual', 'generic'))
    #station_name_slug = slugify(params.get('station_name_actual', ''))

    filename = params.get('target_filename') # Use the filename passed from client
    if not filename: # Fallback if not provided
        filename = output_conf['filename_template'].format(
            EVENT_NAME_SLUG=event_name_slug,
            COMPETITOR_NAME_SLUG=competitor_name_slug,
            #STATION_NAME_SLUG=station_name_slug
        ).replace("__", "_").replace("_.", ".")
        
    output_dir_path_obj = Path(getattr(rl_data, output_conf['output_dir_const']))
    target_filepath = output_dir_path_obj / Path(filename)

    # Check if file already exists (double check, JS might have done this)
    if os.path.isfile(target_filepath):
        logger.info(f"Image {target_filepath} already exists, serving.")
        # Construct URL to return
        image_url = '/' +  str(target_filepath)
        return {"success": True, "image_url": image_url, "message": "Image already existed."}
   
    temp_runtimeVars = {
        'StationList': [],
        'eventDataList': [],
        'competitorName':"",
        'competitorRaceNo':""
        } # Minimal runtimeVars for the single function call
    event_details_found = False
    for element in rl_data.EVENT_DATA_LIST:
        if element[0] == event_name_actual:
            temp_runtimeVars['eventDataList'] = element # Full eventDataList for context
            # Set StationList based on year from eventDataList
            if element[2] == "2023": 
                temp_runtimeVars['StationList'] = rl_data.STATIONLIST23
            elif element[2] == "2024": 
                temp_runtimeVars['StationList'] = rl_data.STATIONLIST24
            elif element[2]=="2025" and element[5]=="KL":
                temp_runtimeVars['StationList'] = rl_data.STATIONLIST25
            elif element[2]=="2025" and element[7]=="CRU_FIT_GAM" :
                temp_runtimeVars['StationList'] = rl_data.STATIONLISTCRU25
            else:
                logger.error(f"ERROR: Event not found {element[2]} {element[5]} {element[7]}") 

            event_details_found = True
            break
    if not event_details_found:
        return {"success": False, "error": f"Event details not found for {event_name_actual} in async."}

    # Load DataFrame 
    #indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(event_name_actual + '.csv')

    #find cvsfile.
    in_cvs_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'duration_csv_generic'), None)
    in_cvs_filename = in_cvs_conf['filename_template'].format( 
            EVENT_NAME_SLUG=event_name_slug,
            ).replace("__", "_").replace("_.", ".")
    in_cvs_dir_path_obj = Path(getattr(rl_data, in_cvs_conf['output_dir_const']))
    in_df_file = in_cvs_dir_path_obj / Path(in_cvs_filename)
    
    try:
        df = pd.read_csv(in_df_file)
        #tidyTheData(df=df, filename=indatafile) # Requires tidyTheData to be stateless or use temp_runtimeVars
    except Exception as e:
        logger.critical(f"Error loading/tidying data in async for {event_name_actual}: {e}")
        return {"success": False, "error": "Data processing failed."}

    competitorIndex = -1
    if output_conf.get('is_competitor_specific'):
        temp_runtimeVars['competitorName'] = params.get('competitor_name_actual')
        temp_runtimeVars['competitorRaceNo'] = params.get('competitor_race_no_actual')
        # IMPORTANT: getCompetitorIndex needs runtimeVars from session, or pass them explicitly
        competitorIndex = getCompetitorIndex(df=df, runtimeVars_override=temp_runtimeVars) # Modify func to accept override
        if competitorIndex == -1:
            logger.critical(f"Competitor not found for async generation. {temp_runtimeVars['competitorName']}")
            return {"success": False, "error": "Competitor not found for async generation."}

    # Call the specific generation function
    try:
        func_to_call = globals().get(output_conf['function_name'])
        if func_to_call:
            #logger.info(f"Async calling {output_conf['function_name']} for {target_filepath}")
            
            # Prepare arguments for the standardized function signature
            call_args = {
                'df': df,
                'filepath': target_filepath,
                'runtimeVars': temp_runtimeVars, # Use the minimal, reconstructed runtimeVars
                'competitorIndex': competitorIndex
            }
            # Add station_name only if the function expects it (e.g. ShowScatterPlot)
            if output_conf['function_name'] == 'ShowScatterPlot':
                call_args['stationName'] = params.get('station_name_actual')
            
            # Call the function
            success_flag = func_to_call(**call_args) # Pass args as keywords

            if success_flag:
                image_url = '/' +  str(target_filepath)
                return {"success": True, "image_url": image_url}
            else:
                return {"success": False, "error": f"{output_conf['function_name']} reported failure."}
        else:
            logger.critical(f"Function {output_conf['function_name']} not found in async worker.")
            return {"success": False, "error": "Generation function not found."}
    except Exception as e:
        logger.critical(f"Error during async generation of {output_conf['function_name']}: {e}", exc_info=True)
        return {"success": False, "error": "Internal server error during image generation."}
####
#
# Only used to generatel when competitor details are none
# ie used to geneate all generic files.
#
####
def redline_vis_generate(competitorDetails):

    logger = rl_data.get_logger()
    
    runtimeVars = session.get('runtime', {})
    outputVars = session.get('output_config', {})
    outputDict = session.get("outputList", {})

    # --- Initial DataFrame Loading and Tidying ---

    if outputVars['competitorAnalysis']:
        #then only one event.
        for element in rl_data.EVENT_DATA_LIST: 
            if element[0] == competitorDetails['event']:
                runtimeVars['eventDataList'] = element
                break
        
        #only want one file if competitor Analysis
        thisFileList = [runtimeVars['eventDataList']]

    elif (competitorDetails != None):
        #then generic analysis of only one event.
        details = competitorDetails

        for element in rl_data.EVENT_DATA_LIST:
            if (element[0] == details['event']):
                runtimeVars['eventDataList'] = element
                break 

        #only want one file if competitor Analysis
        thisFileList = [runtimeVars['eventDataList']]

    else: # Generic analysis all events

        #configure the complete file list for the next loop
        thisFileList = rl_data.EVENT_DATA_LIST


    #Loop through each file, 
    for eventDataList in thisFileList:

        #make sure up to date for each loop.
        runtimeVars['eventDataList'] = eventDataList

        #configure for 2023 format or 2024 format
        if (eventDataList[2]=="2023"):
            runtimeVars['StationList'] = rl_data.STATIONLIST23
            runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART23
        elif (eventDataList[2]=="2024"):
            runtimeVars['StationList'] = rl_data.STATIONLIST24
            runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART24
        elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][5]=="KL":
            runtimeVars['StationList'] = rl_data.STATIONLIST25
            runtimeVars['StationListStart'] = rl_data.STATIONLISTSTART25
        elif runtimeVars['eventDataList'][2]=="2025" and runtimeVars['eventDataList'][7]=="CRU_FIT_GAM" :
            runtimeVars['StationList'] = rl_data.STATIONLISTCRU25
            runtimeVars['StationListStart'] = rl_data.STATIONLISTSTARTCRU25
        else:
            logger.error(f"ERROR: Event not found {runtimeVars['eventDataList'][2]} {runtimeVars['eventDataList'][5]} {runtimeVars['eventDataList'][7]}") 

        logger.debug(f"eventDataList[0] {eventDataList[0]}")

        indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(eventDataList[0] + '.csv')
        try:
            df_raw = pd.read_csv(indatafile)
            df = prepare_data_for_processing(df_raw)
            
            tidyTheData(df=df, filename=indatafile) # Pass filename for logging if tidyTheData uses it
        except FileNotFoundError:
            logger.critical(f"Data file not found: {indatafile}")
            return None # Or handle error appropriately

        # Determine competitorIndex if in competitor analysis mode
        competitorIndex = -1
        if outputVars['competitorAnalysis']:

            runtimeVars['competitorName']=competitorDetails.get('competitor')
            runtimeVars['competitorRaceNo']=competitorDetails.get('race_no')
        
            competitorIndex = getCompetitorIndex(df=df) # Your function to find the index
            if competitorIndex == -1:
                logger.error(f"Competitor not found: {runtimeVars['competitorName']}")
                return "Competitor not found." 
    

        # --- Loop through OUTPUT_CONFIGS to generate outputs ---
        # Reset lists that will be populated by this generation pass for the current event
        outputDict['filename'] = []
        outputDict['id'] = []
        html_info_comp_filepaths = ""

        for output_conf in OUTPUT_CONFIGS:

            # Check if this type of output is Not enabled in general_config
            if( outputVars.get(output_conf['id'], False) == False ):
                #logger.info(f"Output type not enabled: {output_conf['id']}")
                continue

            # Skip if mode doesn't match (e.g., trying to generate generic in competitor mode, or vice-versa)
            if outputVars['competitorAnalysis'] != output_conf['is_competitor_specific']:
                logger.debug(f"CompetitorAnalysis mode does not match output mode: {outputVars['competitorAnalysis']} {output_conf['id']}")
                continue 
            
            # Skip if competitor is required but not found
            if output_conf['is_competitor_specific'] and competitorIndex == -1:
                logger.error(f"Competitor not found: {runtimeVars['competitorName']}")
                continue

            # --- Filename and Path Construction ---
            event_name_slug = slugify(eventDataList[0])
            competitor_name_slug = slugify(runtimeVars['competitorName']) 
            
            # For scatter plots that are per-station
            if output_conf['id'] == 'scatter_generic_collection' :
                for station_idx, station_name in enumerate(runtimeVars['StationList']):
                    
                    #logger.debug(f"Contiinue for {output_conf['id']} {station_idx} {station_name}")
                    
                    station_name_slug = slugify(station_name)
                    current_filename = output_conf['filename_template'].format(
                        EVENT_NAME_SLUG=event_name_slug,
                        STATION_NAME_SLUG=station_name_slug) # Important for per-station files
                       
                    output_dir = getattr(rl_data, output_conf['output_dir_const'])
                    filepath = Path(output_dir) / Path(current_filename)
                    if (ShowScatterPlot(df, filepath, runtimeVars, station_name, competitorIndex) == True):
                        outputDict['filename'].append(str(filepath))
                        outputDict['id'].append(output_conf['id'])

            elif output_conf['id'] == 'scatter_comp_collection' :
                for station_idx, station_name in enumerate(runtimeVars['StationList']):
                    
                    #logger.debug(f"Contiinue for {output_conf['id']} {station_idx} {station_name}")

                    station_name_slug = slugify(station_name)
                    current_filename = output_conf['filename_template'].format(
                        EVENT_NAME_SLUG=event_name_slug,
                        COMPETITOR_NAME_SLUG=competitor_name_slug,
                        STATION_NAME_SLUG=station_name_slug # Important for per-station files
                    )                        
                    output_dir = getattr(rl_data, output_conf['output_dir_const'])
                    filepath = Path(output_dir) / Path(current_filename)
                    if (ShowScatterPlot(df, filepath, runtimeVars, station_name, competitorIndex) == True):
                        outputDict['filename'].append(str(filepath))
                        outputDict['id'].append(output_conf['id'])
                        
            elif output_conf['function_name'] == 'CreatePacingPng':
                
                pacing_table_csv_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pacing_table_csv_generic'), None)
                
                #get the filename
                output_dir = getattr(rl_data, pacing_table_csv_conf['output_dir_const'])
                pacing_table_csv_file = pacing_table_csv_conf['filename_template'].format(EVENT_NAME_SLUG=event_name_slug)
                pacing_table_csv_generic = Path(output_dir) / Path(pacing_table_csv_file)
                
                try:
                    df_for_chart = pd.read_csv(pacing_table_csv_generic)
                except FileNotFoundError:
                    logger.critical(f"Data file not found: {pacing_table_csv_generic}")
                    return None # Or handle error appropriately
                
                #Get the output filename
                current_filename = output_conf['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug
                )                        
                output_dir = getattr(rl_data, output_conf['output_dir_const'])
                filepath = Path(output_dir) / Path(current_filename)
                    
                #df_for_chart = pd.DataFrame(pacing_data_list_of_dicts[1:]) # Skip header
                #df_for_chart.columns = list(pacing_data_list_of_dicts[0].values()) # Set columns from header
                df_for_chart.set_index('Station', inplace=True) # Set Station as index

                # Now call CreatePacingPng
                success_flag = CreatePacingPng(df_input_pacing_table=df_for_chart, 
                                            filepath=filepath, 
                                            runtimeVars=runtimeVars, 
                                            competitorIndex=-1) # competitorIndex is not used by CreatePacingPng
                if success_flag:
                    outputDict['filename'].append(str(filepath))
                    outputDict['id'].append(output_conf['id'])

            #if this function requires category data, but event has none, then skip
            elif output_conf['requires_category_data'] == True and eventDataList[6] == "NO_CAT":
                logger.debug(f"No category data, skipping {output_conf['id']} {output_conf['function_name']} {output_conf['id']} {output_conf['output_dir_const']} {output_conf['filename_template']}")
                continue
                        
            else: # Single file output
                filename = output_conf['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug,
                    COMPETITOR_NAME_SLUG=competitor_name_slug
                )
                output_dir = getattr(rl_data, output_conf['output_dir_const'])
                filepath = Path(output_dir) / Path(filename)

                # Call the function
                try:
                    # Example: func_to_call = getattr(chart_generators, output_conf['function_name'])
                    func_to_call = globals().get(output_conf['function_name']) # If in current module

                    if output_conf['function_name'] == 'MakeFullPdfReport':
                        #ensure not called here, as this is a special case
                        # has to be last and has not standard parameter.
                        #logger.debug(f"Speical Case, no action in this loop: {output_conf['id']}")
                        pass
                         
                    elif output_conf['function_name'] == 'GenerateCompInfoTable':
                        logger.debug(f"Calling {output_conf['function_name']} for {filepath}")

                        # Keep Standardized 
                        func_to_call(df=df,  filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex)
                        
                        #save filepath for future use
                        html_info_comp_filepaths = filepath

                    elif func_to_call:
                        logger.debug(f"Calling {output_conf['function_name']} for {filepath}")
                        # Adapt arguments as needed for each function
                        # Standardized call might be:
                        if(func_to_call(df=df,  filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex)==True):
                            if output_conf['output_type'] == 'png' or output_conf['output_type'] == 'png_collection':
                                outputDict['filename'].append(str(filepath))
                                outputDict['id'].append(output_conf['id'])

                    else:
                        logger.error(f"Function {output_conf['function_name']} not found.")
                except Exception as e:
                    logger.critical(f"Error calling {output_conf['function_name']}: {e}", exc_info=True)

       
        # --- PDF Generation (after all relevant PNGs are made for this event) ---
        if (outputVars['pdf_report_generic'] or outputVars['pdf_report_comp']) and outputDict['filename']: # Only if PNGs were generated
            pdf_config_item = None

            event_name_slug = slugify(eventDataList[0])
            if outputVars['competitorAnalysis'] and outputVars['pdf_report_comp']:
                pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_comp'), None)
                competitor_name_slug = slugify(runtimeVars['competitorName']) 
                pdf_filename = pdf_config_item['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug,
                    COMPETITOR_NAME_SLUG=competitor_name_slug
                )
            elif outputVars['competitorAnalysis'] == False and outputVars['pdf_report_generic']:
                pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_generic'), None)
                pdf_filename = pdf_config_item['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug
                )
            else:
                logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']} and {outputVars['pdf_report_comp']}")

            if pdf_config_item:

                pdf_output_dir = getattr(rl_data, pdf_config_item["output_dir_const"])
                pdf_filepath = Path(pdf_output_dir) / Path(pdf_filename)

                if(MakeFullPdfReport(filepath=pdf_filepath,  outputDict=outputDict, html_filepath=html_info_comp_filepaths, competitorAnalysis=outputVars['competitorAnalysis'])==True):
                   
                    #Me thinks this is pointless!!!
                    outputDict['filename'].append(str(pdf_filepath))
                    outputDict['id'].append(pdf_config_item['id'])
            else:
                logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']} and {outputVars['pdf_report_comp']}")
        else:
            logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']}, {outputVars['pdf_report_comp']} and {outputDict['filename']} is empty")


    # Save data back to session after processing this event
    session['runtime'] = runtimeVars
    session["outputList"] = outputDict
        
    print(f"redline_vis_generate: return True")

        
    # This function is now more of a controller for a single event. 
    # The return values might be used by an outer loop if you process multiple events.
    return True       

#
# functions below this line are called by external files.

# used when regenerating all generic output for all events.
def redline_vis_generate_generic():

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_generate_generic")

    # --- Initialize session variables ---
    redline_vis_generate_generic_init()
  
    #Generate generic documnets.
    return redline_vis_generate(competitorDetails = None)



# used when generating generic event html 
def redline_vis_generate_generic_init():

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_generate_generic_eventhtml")

   # session configuration variable
    output_config = {
        #competitor or generic switch
        'competitorAnalysis'  : False, # if analysis is generic of compeitor based.

        #generic png
        'pie_generic'                   : True, 
        'bar_stacked_dist_generic'      : True,
        'violin_generic'                : True,  
        'radar_median_generic'          : True,  
        'cutoff_bar_generic'            : True,  
        'histogram_nettime_generic'     : True,  
        'catbar_avgtime_generic'        : True,  
        'correlation_bar_generic'       : True,  
        'heatmap_correlation_generic'   : True, 
        'scatter_generic_collection'    : True,
        'pacing_chart_png_generic'      : True,
        'station_hist_generic_part1'    : True,
        'station_hist_generic_part2'    : True,
                
        #generic non-png
        'duration_csv_generic'          : True, 
        'pacing_table_csv_generic'      : True, 
        'pdf_report_generic'            : True,
        
        #competitor png
        #'pie_comp'                      : False, 
        #'bar_stacked_dist_comp'         : False, 
        #'violin_comp'                   : False, 
        #'radar_percentile_comp'         : False,
        #'histogram_nettime_comp'        : False, 
        #'bar_sim_comp'                  : False, 
        #'cumul_sim_comp'                : False, 
        #'diff_sim_comp'                 : False, 
        #'scatter_comp_collection'       : False,
        #'station_hist_comp_part1'       : False,
        #'station_hist_comp_part2'       : False,
        
        #Competitor-png
        #'html_info_comp'                : False,
        #'pdf_report_comp'               : False,
        #'html_note_comp'                : False,
        
    }
    
    # Value always initialised as below but will be updated in function
    runtime = {
        'StationCutOffCount': [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to StationList Entries
        'StationList': [],
        'StationListStart': [],
        'eventDataList': [],
        'competitorName': " ",
        'competitorRaceNo': " "
    }
    
    # Creating updated file list.
    outputDict = {
        'id': [],
        'filename': [],
    }

    #clear the search results - not sure if this is needed.
    session.pop("outputList", None)
    session.pop('runtime', None)
    session.pop('output_config', None)
    session.pop('async_runtime_vars_snapshot', None)
    
    #re-assign    
    session["outputList"] = outputDict
    session['runtime'] = runtime
    session['output_config'] = output_config
 
    return True

# used when generating generic event html 
def redline_vis_generate_competitor_init():

    logger = rl_data.get_logger()
    logger.debug(f"def redline_vis_generate_competitor_init()")

# session configuration variable
    output_config = {
        #competitor or generic switch
        'competitorAnalysis'  : True,
        
        #generic png
        #'pie_generic'                   : False, 
        #'bar_stacked_dist_generic'      : False,  
        #'violin_generic'                : False,  
        #'radar_median_generic'          : False,  
        #'cutoff_bar_generic'            : False,  
        #'histogram_nettime_generic'     : False,  
        #'catbar_avgtime_generic'        : False,  
        #'correlation_bar_generic'       : False,  
        #'heatmap_correlation_generic'   : False, 
        #'scatter_generic_collection'    : False,
        #'station_hist_generic_part1'    : False,
        #'station_hist_generic_part2'    : False,

        
        #generic non-png
        #'duration_csv_generic'          : False, 
        #'pacing_table_csv_generic'      : False, 
        #'pdf_report_generic'            : False,
        #'pacing_chart_png_generic'      : False,
        
        #competitor png
        'bar_stacked_dist_comp'         : True, 
        'pie_comp'                      : True, 
        'violin_comp'                   : True, 
        'radar_percentile_comp'         : True,
        'histogram_nettime_comp'        : True,
        'bar_sim_comp'                  : True, 
        'cumul_sim_comp'                : True, 
        'diff_sim_comp'                 : True, 
        'scatter_comp_collection'       : True,
        'station_hist_comp_part1'       : True,
        'station_hist_comp_part2'       : True,

        #Competitor-png
        'html_info_comp'                : True,
        'pdf_report_comp'               : True,
        'html_note_comp'                : True,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        'StationCutOffCount': [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to StationList Entries
        'StationList': [],
        'StationListStart': [],
        'eventDataList': [],
        'competitorName': " ",
        'competitorRaceNo': " "
    }
    
    # Creating updated file list.
    outputDict = {
        'id': [],
        'filename': [],
    }

    #clear the search results - not sure if this is needed.
    session.pop("outputList", None)
    session.pop('runtime', None)
    session.pop('output_config', None)
    session.pop('async_runtime_vars_snapshot', None)
    
    #re-assign    
    session["outputList"] = outputDict
    session['runtime'] = runtime
    session['output_config'] = output_config
 
    return True