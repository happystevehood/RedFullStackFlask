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
import seaborn as sns

from datetime import datetime, timedelta

#pdf creation
import os, pymupdf
from pathlib import Path
import re
from flask import session

from slugify import slugify 

# local inclusion.
import rl.rl_data as rl_data
from rl.rl_dict import OUTPUT_CONFIGS

# Otherwise get this warning - UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail
mpl.use('agg')
 
#Boolean to decide if output warningsto log
OutputInfo=False


#############################
# Tidy df functions 
#############################
def tidyTheData(df, filename):

    logger = rl_data.get_logger()
    runtimeVars = session.get("runtime", {})

    #Clean a few uneeded columns first.
    #if 'Fav' in df.columns:
    #    df.drop('Fav', axis=1, inplace = True)

    if 'Share' in df.columns:
        df.drop('Share', axis=1, inplace = True)

    #Rename Columns so consistent across years....etc
    df.rename(columns={'Net Pos':'Pos'},inplace=True)
    df.rename(columns={'Net Cat Pos':'Cat Pos'},inplace=True)
    df.rename(columns={'Sled Push & Pull':'Sled Push Pull'},inplace=True)
    df.rename(columns={'Ski Erg':'Ski'},inplace=True)
    df.rename(columns={'Row Erg':'Row'},inplace=True)
    df.rename(columns={'Bike Erg':'Bike'},inplace=True)
    df.rename(columns={'Battle Rope Whips':'Battle Whip'},inplace=True)
    df.rename(columns={'SandbagGauntlet':'Sandbag Gauntlet'},inplace=True)
    df.rename(columns={'Deadball Burpee Over Target':'Deadball Burpee'},inplace=True)

    #in 2023 doubles "The Mule" Column is called "Finish Column"
    df.rename(columns={'Finish':'The Mule'},inplace=True)

    #name_column = df.pop('Name')  # Remove the Name column and store it
    #df.insert(1, 'Name', name_column)  # Insert it at position 2 (leftmost)

    #make a copy of original data frame during tidying process.
    dforig = df.copy(deep=True)

    #add a  column to calculate the times based on sum of each event.
    df.insert(len(df.columns), 'Calc Time', 0.0)

    #Reset the CutOffEvent count value to 0
    runtimeVars["EventCutOffCount"][:] = [0 for _ in runtimeVars["EventCutOffCount"]]

    # Index to last item
    MyIndex = len(runtimeVars["EventListStart"]) - 1

    #iterate the event list in reverse order
    for event in runtimeVars["EventListStart"][::-1]:

        #Note Event = runtimeVars["EventListStart"][MyIndex] below, may be tidier ways to write

        #reorganise data such that each event a duration in reverse format
        for x in df.index:

            # do not write to start time
            if MyIndex != 0:

                #if time format wrong, it causes excpetions.
                try:

                    df.loc[x,event] = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,event]                                   ) ,"%H:%M:%S.%f") 
                                                            - datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,runtimeVars["EventListStart"][MyIndex-1]]) ,"%H:%M:%S.%f"))
 
                    # was originally 10 seconds, changeing to 45 seconds.....
                    #if value less than 45 seconds, then somthing wrong, data not trust worthy so want to drop the row.
                    if df.loc[x,event] < 45.0:
                        #print data...
                        if(OutputInfo == True): logger.info(f"Removed Low value {filename} {x} {event} {df.loc[x,event]} {df.loc[x,'Pos']}")
                                                
                        #drop the row
                        df.drop(x, inplace = True)

                    # else if event is greater than 7 minutes
                    elif (df.loc[x,event] > 420.0):
                        
                        #Increment the CutOff event counter (minus 1 due the diff in lists EventListStart and EventCutOffCount)
                        runtimeVars["EventCutOffCount"][MyIndex-1] = runtimeVars["EventCutOffCount"][MyIndex-1] + 1

                except (ValueError):
                        #One of the values in not a string so write NaN to the value.
                        #print('ValueError', df.loc[x,event], df.loc[x,EventListStart[MyIndex-1]])
                        df.loc[x,event] = float("nan")

                except (TypeError):
                        #One of the values in not a string so write NaN to the value.
                        #print('TypeError', df.loc[x,event], df.loc[x,EventListStart[MyIndex-1]])
                        df.loc[x,event] = float("nan")
                        
        MyIndex = MyIndex - 1


    #Now I want to get the mean time of each event duration in seconds, so can create a ratio of 2 event times
    meanEventList = []
   
    # get the median time for each event.
    for event in runtimeVars["EventList"]:
        meanEventList.append(df[event].mean())

    # now I need to search for 2 NaN"s side by side.

    # Index to last item
    MyIndex = len(runtimeVars["EventListStart"]) - 1

    #iterate the event list in reverse order
    for event in runtimeVars["EventListStart"][::-1]:

        #Note Event = runtimeVars["EventListStart"][MyIndex] below, may be tidier ways to write

        #reorganise data such that each event a duration in reverse format
        for x in df.index:

            # do not check first element
            if MyIndex != 0:

                    #if two consecutive are non numbers. 
                    if (pd.isnull(df.loc[x,runtimeVars["EventListStart"][MyIndex]]) and pd.isnull(df.loc[x,runtimeVars["EventListStart"][MyIndex-1]])):
                        # then need to calculate the duration of two events.

                        #if time format wrong, it causes excpetions.
                        try: 

                            twoEventDuration = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,event]                                   ),"%H:%M:%S.%f") 
                                                                     - datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars["EventListStart"][MyIndex-2]]),"%H:%M:%S.%f"))
                            #change from 60 seconds to 90 seconds
                            if (twoEventDuration < 90.0):
                                if(OutputInfo == True): logger.info(f"2 EventDurLow {filename} {x} {event} {twoEventDuration}")
                                #drop the row
                                df.drop(x, inplace = True)
                            else:        
                                df.loc[x,runtimeVars["EventListStart"][MyIndex-1]] = (twoEventDuration * meanEventList[MyIndex-2] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])
                                df.loc[x,runtimeVars["EventListStart"][MyIndex]]  = (twoEventDuration * meanEventList[MyIndex-1] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])

                        except (ValueError, TypeError):
                                #This will catch the competitors where NET time is "DNF" etc....

                                #Set Time values to None
                                df.loc[x,runtimeVars["EventListStart"][MyIndex-1]] = float("nan")
                                df.loc[x,runtimeVars["EventListStart"][MyIndex]] = float("nan")

                                #print(f"tidyTheData ValueError, TypeError: {x} {event} {MyIndex} {rl_data.convert_to_standard_time(dforig.loc[x,event])} {rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars["EventListStart"][MyIndex-2]])}")

        MyIndex = MyIndex - 1

    # convert Net Time Column to float in seconds.
    for x in df.index:

        #if time format wrong, it causes excpetions.
        try:

            df.loc[x,'Net Time'] =  timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,'Net Time']),"%H:%M:%S.%f") 
                                                          - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f"))
            df.loc[x,'Start']    =  timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,'Start'])   ,"%H:%M:%S.%f") 
                                                          - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f"))
          
            #time Adjust format is the samve
            if ('Time Adj' in df.columns and pd.isna(df.loc[x, "Time Adj"]) == False):
                #print(f"Time Adj 1: {df.loc[x,'Time Adj']}")
                timeAdj = df.loc[x,"Time Adj"].replace("+", "")
                df.loc[x,'Time Adj'] = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,'Time Adj']),"%H:%M:%S.%f") 
                                                             - datetime.strptime(rl_data.convert_to_standard_time("00:00:00.0")        ,"%H:%M:%S.%f"))
            else:
                df.loc[x,'Time Adj'] = 0.0

            #if net time less than 15 minutes (used to be 6 minutes)
            if ((df.loc[x,'Net Time']) < 900.0):
                #print data...
                if(OutputInfo == True): logger.info(f"Removed Low NetTime {filename} {x} {df.loc[x,'Net Time']} {df.loc[x,'Pos']}")
                #drop the row
                df.drop(x, inplace = True)
                # added as this can cause problems dur the next calculations below.
                continue
               
            #Reset Calculated time for this index
            calculatedNetTime = 0.0

            #iterate the event list in reverse order
            for event in runtimeVars["EventListStart"]:
                #print(f"event in {x} {event}")
                calculatedNetTime = calculatedNetTime + df.loc[x,event] 

            #Store the event time.
            df.loc[x,'Calc Time'] = calculatedNetTime    

            #if NetTime - Calculated time is more than 13 seconds
            if (abs(df.loc[x,'Net Time'] - calculatedNetTime) > 13):                               
                if(OutputInfo == True):  logger.info(f"Warning: NetTime Mismatch {filename} {abs(df.loc[x,'Net Time'] - calculatedNetTime)}, {x}"  )

        except (ValueError, TypeError):
                 #Set Time values to None
                #df.loc[x,'Calc Time'] = float("nan")
                #df.loc[x,'Net Time'] = float("nan")

                #drop the row
                df.drop(x, inplace = True)

    #On a column by colum basis 
    for event in runtimeVars["EventList"][::1]:
        #add a rank column per event
        df[event + ' Rank'] = df[event].rank(ascending=True)

    #add a Rank Average Column initialised to 0
    df['Average Rank'] = 0.0

    # Calculate the Average Ranks per competitor
    for x in df.index:

        RankTotal = 0
        for event in runtimeVars["EventList"][::1]:
            
            #add a running total of Rank
            RankTotal = RankTotal + df.loc[x, event + ' Rank']

        #write the rank average to the df.
        df.loc[x,'Average Rank'] = RankTotal / len(runtimeVars["EventList"])

    session["runtime"] = runtimeVars
    
 ##############################################################
# Input a df using runtimeVars["competitorRaceNo"] and runtimeVars["competitorName"]
# returns a competitor index
#############################################################
def competitorDataOutput(df):

    runtimeVars = session.get("runtime", {})

    #initialise return value to -1
    compIndex = -1

    #search for the competitor name in the dataframe
    
    # get mask based on substring matching competitor name.
 
     #if relay 
    if 'Member1' in df.columns:
        nameMask = df['Name'].str.contains(runtimeVars["competitorName"], na=False, regex=False) 
        mem1Mask = df['Member1'].str.contains(runtimeVars["competitorName"], na=False, regex=False) 
        mem2Mask = df['Member2'].str.contains(runtimeVars["competitorName"], na=False, regex=False)
        mem3Mask = df['Member3'].str.contains(runtimeVars["competitorName"], na=False, regex=False)
        mem4Mask = df['Member4'].str.contains(runtimeVars["competitorName"], na=False, regex=False)
        compMask = nameMask | mem1Mask | mem2Mask | mem3Mask | mem4Mask & df['Race No'].astype(str).str.contains(runtimeVars["competitorRaceNo"], na=False, regex=False)

    else:
        compMask = df['Name'].str.contains(runtimeVars["competitorName"], regex=False) & df['Race No'].astype(str).str.contains(runtimeVars["competitorRaceNo"], na=False, regex=False)

    #dataframe with matching competitors and race number
    compDF = df[compMask]

    #if there is at least one match.
    if (len(compDF.index) > 0):

        #get the index of first match.
        compIndex = df[compMask].index.values.astype(int)[0]
 
    else:

        logger = rl_data.get_logger()
        logger.warning(f"No data for the selected competitor {runtimeVars["competitorName"]} in the selected event {runtimeVars["eventDataList"][0]}")

    return compIndex

################################
# Tidy the data/data frame for Correlation
def tidyTheDataCorr(df):

    runtimeVars = session.get("runtime", {})

    ####Remove Rank columns as dont need anymore
    for event in runtimeVars["EventList"][::1]:
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

    if 'Member1' in df.columns:
        df.drop('Member1', axis=1, inplace = True)
        df.drop('Member2', axis=1, inplace = True)
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

    #Remove boring columns
    df.drop(columns=['Race No','Name', 'Gender', 'Wave'], inplace=True)

    #drop rows with empty data 
    df.dropna(inplace = True )


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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    #ignore competitorIndex, I guess could return error if not -1, but not today

    df.to_csv(filepath, index=False)
    logger.debug(f"Saved {filepath}")

    return True
 ################################
# Create a competitor info file.
################################
def GenerateCompInfoTable(df, filepath, runtimeVars, competitorIndex=-1 ):

    logger = rl_data.get_logger()
    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True



    stringHtml = '<table class="styled-table">'

    #If we have a competitor indx.
    if (competitorIndex != -1):
    
        #if category column exist.
        if 'Category' in df.columns:
            compCat = df.loc[competitorIndex, "Category"]

        if 'Member1' in df.columns:

            stringHtml += '<tr><td><strong>Team Name </strong></td><td>' +  df.loc[competitorIndex, "Name"].title() + "</td></tr>"
            stringHtml += '<tr><td><strong>Members </strong></td><td>' +  df.loc[competitorIndex, "Member1"].title() +  df.loc[competitorIndex, "Member2"].title() +  df.loc[competitorIndex, "Member3"].title() +  df.loc[competitorIndex, "Member4"].title() + "</td></tr>"
            
        else:
             stringHtml += '<tr><td><strong>Competitor Name </strong></td><td>' +  df.loc[competitorIndex, "Name"].title()  + "</td></tr>"

        stringHtml += '<tr><td><strong>Gender          </strong></td><td>' +  df.loc[competitorIndex, "Gender"]  + "</td></tr>"

        if 'Category' in df.columns:
            stringHtml += '<tr><td><strong>Category        </strong></td><td>' +  compCat  + "</td></tr>"

        stringHtml += '<tr><td><strong>Event           </strong></td><td>' +  runtimeVars["eventDataList"][1] + "</td></tr>"
        stringHtml += '<tr><td><strong>Wave            </strong></td><td>' +  df.loc[competitorIndex, "Wave"] + "</td></tr>"
        stringHtml += '<tr><td><strong>Position        </strong></td><td>' +  str(df.loc[competitorIndex, "Pos"]) + ' of '+ str(len(df.index)) + ' finishers.'+ "</td></tr>"

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
            stringHtml += '<tr><td><strong>Cat Pos         </strong></td><td>' +  str(df.loc[competitorIndex, "Cat Pos"])+ ' of '+ str(df['Category'].value_counts()[compCat]) + ' finishers.' + "</td></tr>"
            
        stringHtml += '<tr><td><strong>Calc Time</strong></td><td>' + rl_data.format_time_mm_ss(df.loc[competitorIndex, "Calc Time"]) + "</td></tr>"
        stringHtml += '<tr><td><strong>Time Adj</strong></td><td>' + rl_data.format_time_mm_ss(df.loc[competitorIndex, "Time Adj"]) + "</td></tr>"
        stringHtml += '<tr><td><strong>Net Time</strong></td><td>' + rl_data.format_time_mm_ss(df.loc[competitorIndex, "Net Time"]) + "</td></tr>"
        stringHtml += '<tr><td><strong>Average Event Rank </strong></td><td>{:.1f}'.format(df.loc[competitorIndex, "Average Rank"]) + "</td></tr>"

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
                
            #filter by category
            dfcat = df[df['Category']==compCat].copy()

            #On a column by colum basis 
            for event in runtimeVars["EventList"]:
                #add a rank column per event
                dfcat.loc[:, event + ' CatRank'] = dfcat[event].rank(ascending=True)

            #add a Rank Average Column initialised to 0
            dfcat['Average Cat Rank'] = 0.0

            # Calculate the Average Ranks per competitor
            for x in dfcat.index:
                RankTotal = 0
                for event in runtimeVars["EventList"][::1]:
                    #add a running total of Rank
                    RankTotal = RankTotal + dfcat.loc[x, event + ' CatRank']

                #write the rank average to the df.
                dfcat.loc[x,'Average Cat Rank'] = RankTotal / len(runtimeVars["EventList"])

            stringHtml += '<tr><td><strong>Average Event CatRank </strong></td><td>{:.1f}'.format(dfcat.loc[competitorIndex, "Average Cat Rank"]) + "</td></tr>"

        stringHtml += '</table><br>'

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
            # Create the pandas DataFrame
            tableDF = pd.DataFrame(index=runtimeVars["EventList"],columns=['Time', 'Rank', 'CatRank'])
        else:
            tableDF = pd.DataFrame(index=runtimeVars["EventList"],columns=['Time', 'Rank'])

        for event in runtimeVars["EventList"]:
            # Format individual float values directly
            time_val = rl_data.format_time_mm_ss(df.loc[competitorIndex, event])
            rank_val = df.loc[competitorIndex, f"{event} Rank"]

            tableDF.loc[event, 'Time'] = f"{time_val}" if pd.notnull(time_val) else ''
            tableDF.loc[event, 'Rank'] = f"{rank_val:.1f}" if pd.notnull(rank_val) else ''

            # Only handle CatRank if needed
            if ('Category' in df.columns) and (compCat != "All Ages"):
                catrank_val = dfcat.loc[competitorIndex, f"{event} CatRank"]
                tableDF.loc[event, 'CatRank'] = f"{catrank_val:.1f}" if pd.notnull(catrank_val) else ''

        #forcibly remove the style attribute from string
        stringHtml += re.sub( ' style=\"text-align: right;\"','',tableDF.to_html())
        stringHtml += '<br>'

        with open(filepath, "w") as file:
            file.write(stringHtml)

        logger.debug(f"Saved {filepath}")

    else:

        logger.warning(f"No data for the selected competitor {runtimeVars["competitorName"]} in the selected event {runtimeVars["eventDataList"][0]}")
        return False

    return True
    

#############################
# Correlation
#############################

def CreateCorrBar(df, filepath, runtimeVars, competitorIndex=-1):
    logger = rl_data.get_logger()

    #remove category for corralation info


    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    dfcorr = df.copy(deep=True)

    #next level tidying for correlation
    tidyTheDataCorr(dfcorr)

    #get corrolation info
    corr_matrix = dfcorr.corr()

    #if a competitor is selected dont show correlation bar chart    
    if(competitorIndex == -1):

        plt.figure(figsize=(10, 10))
        
        # Shows a nice correlation barchar
        heatmap = sns.barplot( data=corr_matrix['Net Time'])
        
        for i in heatmap.containers:
            heatmap.bar_label(i,fmt='%.2f')
        
        plt.xticks(rotation=70)
        plt.ylabel('Total Time')

        heatmap.set_title('Event Correlation V Total Time ' + runtimeVars["eventDataList"][1], fontdict={'fontsize':12}, pad=10);

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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
    
    #if a competitor is selected dont show correlation bar chart    
    if(competitorIndex == -1):

        dfcorr = df.copy(deep=True)

        #next level tidying for correlation
        tidyTheDataCorr(dfcorr)
        
        #get corrolation info
        corr_matrix = dfcorr.corr()

        plt.figure(figsize=(10, 10))
        heatmap = sns.heatmap(corr_matrix, vmin=-0, vmax=1, annot=True, cmap='BrBG')
        heatmap.set_title('Correlation Heatmap ' + runtimeVars["eventDataList"][1], fontdict={'fontsize':12}, pad=12);

        # Output/Show depending of global variable setting with pad inches
        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
        plt.close()

    return True

############################
# Show Histogram Age Categories
#############################

def CreateHistAgeCat(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True



    # set num of categories to be 3 by default
    num_cat        = 3

    plt.figure(figsize=(10, 10))

    # do for 2023
    if (runtimeVars["eventDataList"][2]=="2023"):

        #Competitive singles Category columns colours
        Category_order = ["18 - 29", "30 - 39", "40+"]
        colors         = ['red'    , 'tan'    , 'lime']
    
    #else for 2024
    else:
        #Competitive singles Category 
        Category_order_single = ["18-24", "25-29", "30-34", "35-39", "40-44",  "45-49", "50+"]
        colors_single =         ['red'  , 'tan'  , 'lime' , 'blue' , 'purple', 'orange', 'grey']

        #Competitive Doubles & Team Relay Category 
        category_order_team = ["< 30", "30-44", "45+"]
        colors_team =         ['red' , 'tan'  , 'lime']

    #converting from seconds to minutes and making bins dvisible by 5
    binWidth = 5
    binMin = ((int(min(df['Net Time']))//60)//binWidth)*binWidth
    binMax = (((int(max(df['Net Time']))//60)+binWidth)//binWidth)*binWidth
    bins=np.arange(binMin,binMax, binWidth)

    #BinAllWidth
    binAllWidth = 20
    binAllMin = ((int(min(df['Net Time']))//60)//binWidth)*binWidth
    binAllMax = (((int(max(df['Net Time']))//60)+binWidth)//binWidth)*binWidth
    binsAll=np.arange(binAllMin,binAllMax, binAllWidth)

    catAll = list((df['Net Time'])/60.0)

    #if category column exist.
    if 'Category' in df.columns:

        #if 2024 style
        if (runtimeVars["eventDataList"][2]=="2024"):

            #need to setup for singles or teams
            #if single matches exist
            if (Category_order_single[0] in df['Category'].values):
                Category_order = Category_order_single
                colors = colors_single
                num_cat        = 7
            else:
                Category_order = category_order_team
                colors = colors_team
                num_cat        = 3            

        #create list per category
        cat0 = list((df[df['Category'] == Category_order[0]]['Net Time'])/60.0)
        cat1 = list((df[df['Category'] == Category_order[1]]['Net Time'])/60.0)
        cat2 = list((df[df['Category'] == Category_order[2]]['Net Time'])/60.0)

        if (num_cat == 7):
            cat3 = list((df[df['Category'] == Category_order[3]]['Net Time'])/60.0)
            cat4 = list((df[df['Category'] == Category_order[4]]['Net Time'])/60.0)
            cat5 = list((df[df['Category'] == Category_order[5]]['Net Time'])/60.0)
            cat6 = list((df[df['Category'] == Category_order[6]]['Net Time'])/60.0)

        #if cat0 not empty means there are categories.
        if cat0 != []:

            if (num_cat == 3):
                plt.hist([cat0,cat1,cat2], color=colors, label=Category_order, bins=bins)
                plt.legend()
            else:
                plt.hist([cat0,cat1,cat2,cat3,cat4,cat5,cat6], color=colors, label=Category_order, bins=bins)
                plt.legend()
                #sns.histplot(data=df, x='Net Time', hue='Category',  multiple="dodge", shrink=.8, palette=colors, hue_order=Category_order, legend=True)
        else:
            plt.hist(catAll,bins=binAllWidth)

    else:
        plt.hist(catAll,bins=binAllWidth)

    plt.xticks(bins)
    plt.xlabel('Time (Minutes)')
    plt.ylabel('Num. Participants')
    plt.title(runtimeVars["eventDataList"][1] + ' Time Distrbution')
    plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

    # Output/Show depending of global variable setting.
    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
    plt.close()

    return True

#############################
# Show Bar chart Events
#############################
def CreateBarChartEvent(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True



    #print(f"Generating Bar Chart with Top Legends for event {runtimeVars["eventDataList"][0]} at {filepath}")

    station_names = runtimeVars["EventList"]
    x_positions = np.arange(len(station_names))

    percentile_bands_data = {
        '70-90%': [df[event].quantile(0.90) for event in station_names],
        '50-70%': [df[event].quantile(0.70) for event in station_names],
        '30-50%': [df[event].quantile(0.50) for event in station_names],
        '10-30%': [df[event].quantile(0.30) for event in station_names],
        '01-10%': [df[event].quantile(0.10) for event in station_names],
        'Fastest': [df[event].min() for event in station_names]
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
        ax.set_title(f"{runtimeVars["eventDataList"][1]}\nStation Time Distribution", fontsize=13, pad=title_pad)
    else:
        competitor_title_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Selected Competitor"
        ax.set_title(f"{runtimeVars["eventDataList"][1]} - {competitor_title_name}\nPerformance vs. Time Percentiles", fontsize=13, pad=title_pad)
    
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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True


    

    #print(f"Generating Violin Chart for event {runtimeVars["eventDataList"][0]} at {filepath}")

    station_data_df = df[runtimeVars["EventList"]].copy()
    for col in runtimeVars["EventList"]:
        station_data_df[col] = pd.to_numeric(station_data_df[col], errors='coerce')

    all_station_times_flat = station_data_df.values.flatten()
    all_station_times_flat = all_station_times_flat[~np.isnan(all_station_times_flat)] 
    
    cutoff_time = 600.0 
    if len(all_station_times_flat) > 0:
        pass 

    df_melted = station_data_df.melt(var_name='Station', value_name='Time (s)')
    df_melted['Station'] = pd.Categorical(df_melted['Station'], categories=runtimeVars["EventList"], ordered=True)
    df_melted_filtered = df_melted[df_melted['Time (s)'] < cutoff_time].dropna(subset=['Time (s)'])

    plt.figure(figsize=(12, 12))
    ax = plt.gca() # Get current axes to use for annotations later

    if not df_melted_filtered.empty:
        sns.violinplot(ax=ax, x='Station', y='Time (s)', data=df_melted_filtered, 
                       order=runtimeVars["EventList"], 
                       inner='quartile', 
                       cut=1,          
                       hue='Station',         
                       palette='viridis',     
                       legend=False,          
                       linewidth=1.5,   
                       density_norm='width')
    else:
        print("Warning: All data filtered out by cutoff time. Plotting empty chart structure.")
        ax.set_xticks(np.arange(len(runtimeVars["EventList"])))
        ax.set_xticklabels(runtimeVars["EventList"], rotation=90, fontsize=9)

    if competitorIndex != -1:
        compList_station_times_raw = [] # Store raw times for labeling
        compList_station_times_plot = [] # Store potentially clamped times for plotting marker

        for event in runtimeVars["EventList"]:
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

        x_positions = np.arange(len(runtimeVars["EventList"]))
        
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
        plt.title(f"{runtimeVars["eventDataList"][1]} Station Time Distribution", fontsize=14)
    else:
        competitor_title_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Selected Competitor"
        plt.title(f"{runtimeVars["eventDataList"][1]} - {competitor_title_name}\nStation Time vs. Distribution", fontsize=14)
    
    plt.tight_layout(pad=1.0)

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()
    
    return True
#############################
# Show Bar chart Cut Off Events
#############################

def CreateBarChartCutOffEvent(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
    
    fig, ax = plt.subplots(figsize=(10, 10))

    #null list
    cutOffEventList = []
    MyIndex = 0

    for event in runtimeVars["EventList"][::]:
        #add percentage to list
        cutOffEventList.append((100*runtimeVars["EventCutOffCount"][MyIndex]) / len(df.index) )
        MyIndex = MyIndex + 1

    ax.bar(runtimeVars["EventList"], cutOffEventList,       color='red'   , label='Partipants > 7min')

    for container in ax.containers:
        ax.bar_label(container,fmt='%.1f%%')

    plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)
    plt.tick_params(axis='x', labelrotation=90)
    plt.ylabel('Num Participants')
    plt.title(runtimeVars["eventDataList"][1] + ' Station 7 Min Stats')
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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    


    # Just do Generic pie chart based on mean time per event.
    if(competitorIndex==-1):

        plt.figure(figsize=(10, 10))

        meanEventList = []
        meanEventListLabel = []
        totalMeanTime = 0.0
    
        # get the median time for each event.
        for event in runtimeVars["EventList"]:
            meanEventList.append(df[event].mean())
            totalMeanTime = totalMeanTime + int(df[event].mean())

            eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df[event].mean())//60 ,int(df[event].mean())%60)
            meanEventListLabel.append(eventLabelString)

        totalMeanTimeString = "{:1d}m {:2d}s".format(int(totalMeanTime)//60 ,int(totalMeanTime)%60)
        plt.title(runtimeVars["eventDataList"][1] + ' Average Station Breakdown : ' + totalMeanTimeString )
    
        #create pie chart = Use Seaborn's color palette 'Set2'
        plt.pie(meanEventList, labels = meanEventListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))
        
        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
        plt.close()

    # else do competitor specific pie chart based on actual time per event.
    else:

        plt.figure(figsize=(10, 10))

        compEventList = []
        compEventListLabel = []

        # get the median time for each event.
        for event in runtimeVars["EventList"]:
        
            compEventList.append(df.loc[competitorIndex,event])
            eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df.loc[competitorIndex,event])//60 ,int(df.loc[competitorIndex,event])%60)
            compEventListLabel.append(eventLabelString)

        totalCompTimeString = "{:1d}m {:2d}s".format(int(df.loc[competitorIndex,'Calc Time'])//60 ,int(df.loc[competitorIndex,'Calc Time'])%60)
        plt.title(runtimeVars["eventDataList"][1] + ' ' + df.loc[competitorIndex,'Name'] + ' Stations: ' + totalCompTimeString )

        #create pie chart = Use Seaborn's color palette 'Set2'
        plt.pie(compEventList, labels = compEventListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))

        plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
        plt.close()

    return True


#############################
# Show Radar Chart
#############################

def CreateRadar(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()

    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True


    
    num_vars = len(runtimeVars["EventList"])
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True)) # Use consistent larger size

    if competitorIndex == -1:
        # --- Generic Radar: Median Actual Times (Y-axis in seconds) ---
        # Faster times (lower seconds) will be closer to the center.
        
        median_event_times_actual = []
        station_axis_labels = [] # For station names only on this plot

        for event in runtimeVars["EventList"]:
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
        
        plt.title(f"{runtimeVars["eventDataList"][1]}\nMedian Performance Times (Seconds)", size=14, color='black', y=1.1)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1)) # Moved legend

    else: # competitorIndex != -1 (Individual Competitor Plot - kept as your preferred version)
        compEventPercentiles = []
        compEventLabels = [] 

        for event in runtimeVars["EventList"]:
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

        plt.title(f"{runtimeVars["eventDataList"][1]}\n{df.loc[competitorIndex,'Name']} Performance Rank Percentile",y=1.12,size=14, color='black')
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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    if competitorIndex == -1:
        print("Error: CreateGroupBarChart requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']


       
    #print(f"Generating Group Bar Chart for {competitor_name} at {filepath}")

    # 0. Get the competitor's time for each event
    competitor_event_times = []
    station_names = runtimeVars["EventList"] # Use this for x-axis labels

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
        logger.warning(f"No similar finishers found for {competitor_name}.")
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

    fig.tight_layout() # Adjust layout to make room for labels

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
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True
        
    if competitorIndex == -1:
        logger.warning("Error: CreateCumulativeTimeComparison requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']


       
    #print(f"Generating Cumulative Time Chart for {competitor_name} at {filepath}")

    station_names = runtimeVars["EventList"]
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
        logger.warning(f"No similar finishers found for {competitor_name}. Using competitor's times for comparison line.")
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

    fig.tight_layout(pad=1.0) # Add some padding

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
    logger = rl_data.get_logger()

    if os.path.isfile(filepath) :
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    if competitorIndex == -1:
        print("Error: CreateStationTimeDifferenceChart requires a valid competitorIndex.")
        return False

    competitor_name = df.loc[competitorIndex, 'Name']
        
    #print(f"Generating Station Time Difference Chart for {competitor_name} at {filepath}")

    station_names = runtimeVars["EventList"]
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
    fig.tight_layout()

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
        logger.info('Category column not found in DataFrame. Skipping chart generation Skipping for {runtimeVars["eventDataList"][0]}.')
        return False

    unique_categories = sorted(df['Category'].dropna().unique())
    if len(unique_categories) <= 1:
        logger.info(f"Not enough categories ({len(unique_categories)}) to generate a comparison chart. Skipping for {runtimeVars["eventDataList"][0]}.")
        return False

    #print(f"Generating Average Station Time by Category chart at {filepath}")

    station_names = runtimeVars["EventList"]
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
    ax.set_title(f"{runtimeVars["eventDataList"][1]}\nAverage Station Times by Age Category", fontsize=14)
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
    fig.tight_layout()

    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
    plt.close()

    return True

#############################
## CreatePacingTable
#############################

def CreatePacingTable(df, filepath, runtimeVars, competitorIndex=-1 ):
    logger = rl_data.get_logger()


    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation")
        return True
    
    #print(f"Generating Pacing Table for event {runtimeVars["eventDataList"][0]}")

    station_names = runtimeVars["EventList"]
    num_stations = len(station_names)
    if num_stations == 0:
        print("Error: EventList is empty. Cannot generate pacing table.")
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
        print("No valid numeric Net Time data to generate pacing table.")
        return False

    df_for_pacing_calcs = df_cleaned[df_cleaned['Time Adj'].fillna(0) == 0].copy()
    df_to_use_for_cohorts_and_percentiles = df_for_pacing_calcs
    if df_for_pacing_calcs.empty:
        print("Warning: No athletes found with Time Adj == 0. Pacing table will be based on all athletes.")
        df_to_use_for_cohorts_and_percentiles = df_cleaned
        if df_to_use_for_cohorts_and_percentiles.empty:
            print("Critical: No data left. Cannot generate table.")
            return False
    
    df_sorted = df_to_use_for_cohorts_and_percentiles.sort_values(by='Net Time').reset_index(drop=True)
    total_ranked_athletes = len(df_sorted)

    if total_ranked_athletes == 0:
        print("No ranked athletes to process after filtering.")
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

        #print(f"Processing {percentile_key_name} {total_ranked_athletes}, {start_index}, {end_index} ")

        if start_index >= end_index and total_ranked_athletes > 0:
            target_index = int(p_val * (total_ranked_athletes -1) )
            num_either_side = max(1, int(COHORT_POSITION_WINDOW_PERCENTAGE * total_ranked_athletes / 2))
            start_index = max(0, target_index - num_either_side)
            end_index = min(total_ranked_athletes, target_index + num_either_side + 1)

        cohort_df = df_sorted.iloc[start_index:end_index]
        
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
            #print(f"Saved pacing table to {filepath}")
        except Exception as e:
            print(f"Error saving pacing table to CSV: {e}")
    else:
        print("No pacing table data generated to save.")

    return pacing_table_data_list_of_dicts

###############################
#
# Non Standard output function!
#
# MakeFullPdfReport
#
###############################

def MakeFullPdfReport(filepath, outputList, html_filepath, competitorIndex=-1 ):

    logger = rl_data.get_logger()
 
    #print(f"Generating PDF report at {filepath}")

    if os.path.isfile(filepath):
        logger.debug(f"File {filepath} already exists. Skipping generation")
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
        if(competitorIndex != -1):
            page = doc.new_page()

            #open html file html_info_comp_filepaths
            with open(html_filepath, 'r') as f:
                stringHtml = f.read()
            page.insert_htmlbox(rect, stringHtml)

        for i, f_path_str in enumerate(outputList["filename"]):
            if (".png" in f_path_str): # Check extension case-insensitively
                #logger.debug(f"Processing image for PDF: {f_path_str}")
                try:
                    img_doc = pymupdf.open(f_path_str)  # Open to get dimensions
                    img_rect = img_doc[0].rect
                    img_doc.close()

                    page = doc.new_page(width=img_rect.width, height=img_rect.height)
                    page.insert_image(img_rect, filename=f_path_str) # Direct insertion
                except Exception as e:
                    logger.error(f"Error processing image {f_path_str} for PDF: {e}")
            else:
                logger.info(f"File type not supported for PDF image insertion: {f_path_str}")
            
        doc.save(filepath, garbage=4, deflate=True)
        logger.warning(f"Saving PDF {filepath}")

    except Exception as e:
        logger.error(f"Error creating PDF {filepath}: {e}", exc_info=True)

#############################
# Show Scatter Plot
#############################
def ShowScatterPlot(df, filepath, runtimeVars, stationName, competitorIndex ):
    
    logger = rl_data.get_logger()

    # Check if file exists or force generation
    if os.path.isfile(filepath) :
        logger.debug(f"File {filepath} already exists. Skipping generation.")
        return True

    #remove category for corralation info


    dfcorr = df.copy(deep=True)

    #next level tidying for correlation
    tidyTheDataCorr(dfcorr)

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
    
    plt.title(runtimeVars["eventDataList"][1] + ' ' + stationName + ' Corr. ' + corrstr)
    plt.ylabel("Ovearll Position")
    plt.xlabel("Station Time")
    plt.legend()
    plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

    # Output/Show depending of global variable setting. 
    plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
    plt.close()

    return True
 
#############################
# Start of redline visuation method
# competitorDetails will be search details of one competitor
#############################
def redline_vis_generate(competitorDetails):

    logger = rl_data.get_logger()
    
    runtimeVars = session.get("runtime", {})
    outputVars = session.get("ouptut_config", {})
    outputList = session["outputList"] 

    # --- Initial DataFrame Loading and Tidying ---

    if outputVars["competitorAnalysis"]:
        #then only one event.
        for element in rl_data.EVENT_DATA_LIST: 
            if element[0] == competitorDetails['event']:
                runtimeVars["eventDataList"] = element
                break
        
        #only want one file if competitor Analysis
        thisFileList = [runtimeVars["eventDataList"]]

    elif (competitorDetails != None):
        #then generic analysis of only one event.
        details = competitorDetails

        for element in rl_data.EVENT_DATA_LIST:
            if (element[0] == details['event']):
                runtimeVars["eventDataList"] = element
                break 

        #only want one file if competitor Analysis
        thisFileList = [runtimeVars["eventDataList"]]

    else: # Generic analysis all events

        #configure the complete file list for the next loop
        thisFileList = rl_data.EVENT_DATA_LIST

    #Loop through each file, 
    for eventDataList in thisFileList:

        #configure for 2023 format or 2024 format
        if (eventDataList[2]=="2023"):
            runtimeVars["EventList"] = rl_data.EVENTLIST23
            runtimeVars["EventListStart"] = rl_data.EVENTLISTSTART23

        else:
            runtimeVars["EventList"] = rl_data.EVENTLIST24
            runtimeVars["EventListStart"] = rl_data.EVENTLISTSTART24

        logger.debug(f"eventDataList[0] {eventDataList[0]}")

        indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(eventDataList[0] + '.csv')
        try:
            df = pd.read_csv(indatafile)
            tidyTheData(df=df, filename=indatafile) # Pass filename for logging if tidyTheData uses it
        except FileNotFoundError:
            logger.error(f"Data file not found: {indatafile}")
            return None # Or handle error appropriately

        # Determine competitorIndex if in competitor analysis mode
        competitorIndex = -1
        if outputVars["competitorAnalysis"]:

            runtimeVars["competitorName"]=competitorDetails.get('competitor')
            runtimeVars["competitorRaceNo"]=competitorDetails.get('race_no')
        
            competitorIndex = competitorDataOutput(df=df) # Your function to find the index
            if competitorIndex == -1:
                logger.warning(f"Competitor not found: {runtimeVars["competitorName"]}")
                return "Competitor not found." 
    

        # --- Loop through OUTPUT_CONFIGS to generate outputs ---
        # Reset lists that will be populated by this generation pass for the current event
        outputList["filename"] = []
        outputList["id"] = []
        html_info_comp_filepaths = ""

        for output_conf in OUTPUT_CONFIGS:

            # Check if this type of output is Not enabled in general_config
            if( outputVars.get(output_conf['id'], False) == False ):
                logger.info(f"Output type not enabled: {output_conf['id']}")
                continue

            # Skip if mode doesn't match (e.g., trying to generate generic in competitor mode, or vice-versa)
            if outputVars["competitorAnalysis"] != output_conf['is_competitor_specific']:
                logger.debug(f"CompetitorAnalysis mode does not match output mode: {outputVars["competitorAnalysis"]} {output_conf['id']}")
                continue 
            
            # Skip if competitor is required but not found
            if output_conf['is_competitor_specific'] and competitorIndex == -1:
                logger.warning(f"Competitor not found: {runtimeVars["competitorName"]}")
                continue

            # --- Filename and Path Construction ---
            event_name_slug = slugify(eventDataList[0])
            competitor_name_slug = slugify(runtimeVars["competitorName"]) 
            
            # For scatter plots that are per-station
            if output_conf['id'] == 'scatter_generic_collection' :
                for station_idx, station_name in enumerate(runtimeVars["EventList"]):
                    #logger.debug(f"Contiinue for {output_conf['id']} {station_idx} {station_name}")
                    station_name_slug = slugify(station_name)
                    current_filename = output_conf['filename_template'].format(
                        EVENT_NAME_SLUG=event_name_slug,
                        STATION_NAME_SLUG=station_name_slug) # Important for per-station files
                       
                    output_dir = getattr(rl_data, output_conf['output_dir_const'])
                    filepath = Path(output_dir) / Path(current_filename)
                    if (ShowScatterPlot(df, filepath, runtimeVars, station_name, competitorIndex) == True):
                        outputList["filename"].append(str(filepath))
                        outputList["id"].append(output_conf['id'])

            elif output_conf['id'] == 'scatter_comp_collection' :
                for station_idx, station_name in enumerate(runtimeVars["EventList"]):
                    
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
                        outputList["filename"].append(str(filepath))
                        outputList["id"].append(output_conf['id'])

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
                        logger.debug(f"Speical Case, skipping: {output_conf['id']}")
                        pass 
                    elif output_conf['function_name'] == 'GenerateCompInfoTable':
                        #logger.debug(f"Calling {output_conf['function_name']} for {filepath}")

                        # Keep Standardized 
                        func_to_call(df=df,  filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex)
                        
                        #save filepath for future use
                        html_info_comp_filepaths = filepath

                    elif func_to_call:
                        #logger.debug(f"Calling {output_conf['function_name']} for {filepath}")
                        # Adapt arguments as needed for each function
                        # Standardized call might be:
                        if(func_to_call(df=df,  filepath=filepath, runtimeVars=runtimeVars, competitorIndex=competitorIndex)==True):
                            outputList["filename"].append(str(filepath))
                            outputList["id"].append(output_conf['id'])

                    else:
                        logger.warning(f"Function {output_conf['function_name']} not found.")
                except Exception as e:
                    logger.error(f"Error calling {output_conf['function_name']}: {e}", exc_info=True)


        # --- PDF Generation (after all relevant PNGs are made for this event) ---
        if (outputVars["pdf_report_generic"] or outputVars["pdf_report_comp"]) and outputList["filename"]: # Only if PNGs were generated
            pdf_config_item = None

            event_name_slug = slugify(eventDataList[0])
            if outputVars["competitorAnalysis"] and outputVars["pdf_report_comp"]:
                pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_comp'), None)
                competitor_name_slug = slugify(runtimeVars["competitorName"]) 
                pdf_filename = pdf_config_item['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug,
                    COMPETITOR_NAME_SLUG=competitor_name_slug
                )
            elif outputVars["competitorAnalysis"] == False and outputVars["pdf_report_generic"]:
                pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_generic'), None)
                pdf_filename = pdf_config_item['filename_template'].format(
                    EVENT_NAME_SLUG=event_name_slug
                )
            else:
                logger.warning(f"No PDF configuration found for {outputVars["pdf_report_generic"]} and {outputVars["pdf_report_comp"]}")

            if pdf_config_item:

                pdf_output_dir = getattr(rl_data, pdf_config_item["output_dir_const"])
                pdf_filepath = Path(pdf_output_dir) / Path(pdf_filename)

                if(MakeFullPdfReport(filepath=pdf_filepath,  outputList=outputList, html_filepath=html_info_comp_filepaths, competitorIndex=competitorIndex)==True):
                   
                    #Me thinks this is pointless!!!
                    outputList["filename"].append(str(pdf_filepath))
                    outputList["id"].append(pdf_config_item["id"])
            else:
                logger.warning(f"No PDF configuration found for {outputVars['pdf_report_generic']} and {outputVars['pdf_report_comp']}")
        else:
            logger.warning(f"No PDF configuration found for {outputVars['pdf_report_generic']}, {outputVars['pdf_report_comp']} and {outputList["filename"]} is empty")


    # Save runtimeVars back to session after processing this event
    session["runtime"] = runtimeVars
    
    # This function is now more of a controller for a single event. 
    # The return values might be used by an outer loop if you process multiple events.
    return True       

#
# functions below this line are called by external files.

def redline_vis_competitor_html(competitorDetails, io_stringHtml, io_pngList, io_pngStrings):
    
    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_competitor_html {competitorDetails}")
    
    ouptut_config = {
 
        #competitor or generic switch
        "competitorAnalysis"  : True, # if analysis is generic of compeitor based.
        
        #generic non-png
        "duration_csv_generic"          : False, 
        "pacing_table_csv_generic"      : False, 
        "pdf_report_generic"            : False,

        #generic png
        "pie_generic"                   : False, 
        "bar_stacked_dist_generic"      : False,  
        "violin_generic"                : False,  
        "radar_median_generic"          : False,  
        "cutoff_bar_generic"            : False,  
        "histogram_nettime_generic"     : False,  
        "catbar_avgtime_generic"        : False,  
        "correlation_bar_generic"       : False,  
        "heatmap_correlation_generic"   : False, 
        "scatter_generic_collection"    : False,

        #Competitor-png
        "html_info_comp"                : True,
        "pdf_report_comp"               : False,

        #competitor png
        "pie_comp"                      : True, 
        "bar_stacked_dist_comp"         : True, 
        "violin_comp"                   : True, 
        "radar_percentile_comp"         : True, 
        "bar_sim_comp"                  : True, 
        "cumul_sim_comp"                : True, 
        "diff_sim_comp"                 : True, 
        "scatter_comp_collection"       : True,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "outputIdList": [],
        "outputFileList": [],
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    session["runtime"] = runtime

    # Store config in session
    session["ouptut_config"] = ouptut_config

    return redline_vis_generate(competitorDetails)

def redline_vis_competitor_pdf(competitorDetails, io_stringHtml, io_pngList, io_pngStrings):
    
    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_competitor_pdf {competitorDetails}")

    ouptut_config = {
 
        #competitor or generic switch
        "competitorAnalysis"  : True, # if analysis is generic of compeitor based.
        
        #generic non-png
        "duration_csv_generic"          : False, 
        "pacing_table_csv_generic"      : False, 
        "pdf_report_generic"            : False,

        #generic png
        "pie_generic"                   : False, 
        "bar_stacked_dist_generic"      : False,  
        "violin_generic"                : False,  
        "radar_median_generic"          : False,  
        "cutoff_bar_generic"            : False,  
        "histogram_nettime_generic"     : False,  
        "catbar_avgtime_generic"        : False,  
        "correlation_bar_generic"       : False,  
        "heatmap_correlation_generic"   : False, 
        "scatter_generic_collection"    : False,

        #Competitor-png
        "html_info_comp"                : True,
        "pdf_report_comp"               : True,

        #competitor png
        "pie_comp"                      : True, 
        "bar_stacked_dist_comp"         : True, 
        "violin_comp"                   : True, 
        "radar_percentile_comp"         : True, 
        "bar_sim_comp"                  : True, 
        "cumul_sim_comp"                : True, 
        "diff_sim_comp"                 : True, 
        "scatter_comp_collection"       : True,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    # Creating updated file list.
    outputList = {
        "id": [],
        "filename": [],
    }

    session["outputList"] = outputList
    session["runtime"] = runtime
    session["ouptut_config"] = ouptut_config

    return redline_vis_generate(competitorDetails)
  

    

# used when regenerating all generic output for all events.
def redline_vis_generic():

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_generic")

    ouptut_config = {
 
        #competitor or generic switch
        "competitorAnalysis"  : False, # if analysis is generic of compeitor based.
        
        #generic non-png
        "duration_csv_generic"          : True, 
        "pacing_table_csv_generic"      : True, 
        "pdf_report_generic"            : True,

        #generic png
        "pie_generic"                   : True, 
        "bar_stacked_dist_generic"      : True,  
        "violin_generic"                : True,  
        "radar_median_generic"          : True,  
        "cutoff_bar_generic"            : True,  
        "histogram_nettime_generic"     : True,  
        "catbar_avgtime_generic"        : True,  
        "correlation_bar_generic"       : True,  
        "heatmap_correlation_generic"   : True, 
        "scatter_generic_collection"    : True,

        #Competitor-png
        "html_info_comp"                : False,
        "pdf_report_comp"               : False,

        #competitor png
        "pie_comp"                      : False, 
        "bar_stacked_dist_comp"         : False, 
        "violin_comp"                   : False, 
        "radar_percentile_comp"         : False, 
        "bar_sim_comp"                  : False, 
        "cumul_sim_comp"                : False, 
        "diff_sim_comp"                 : False, 
        "scatter_comp_collection"       : False,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    # Creating updated file list.
    outputList = {
        "id": [],
        "filename": [],
    }

    session["outputList"] = outputList
    session["runtime"] = runtime
    session["ouptut_config"] = ouptut_config
  
    return redline_vis_generate(None)


# used when generating generic pdf (if not already generated)
def redline_vis_generic_eventpdf(details):

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_generic_eventpdf {details}")

    ouptut_config = {
 
        #competitor or generic switch
        "competitorAnalysis"  : False, # if analysis is generic of compeitor based.
        
        #generic non-png
        "duration_csv_generic"          : False, 
        "pacing_table_csv_generic"      : False, 
        "pdf_report_generic"            : True,

        #generic png
        "pie_generic"                   : True, 
        "bar_stacked_dist_generic"      : True,  
        "violin_generic"                : True,  
        "radar_median_generic"          : True,  
        "cutoff_bar_generic"            : True,  
        "histogram_nettime_generic"     : True,  
        "catbar_avgtime_generic"        : True,  
        "correlation_bar_generic"       : True,  
        "heatmap_correlation_generic"   : True, 
        "scatter_generic_collection"    : True,

        #Competitor-png
        "html_info_comp"                : False,
        "pdf_report_comp"               : False,

        #competitor png
        "pie_comp"                      : False, 
        "bar_stacked_dist_comp"         : False, 
        "violin_comp"                   : False, 
        "radar_percentile_comp"         : False, 
        "bar_sim_comp"                  : False, 
        "cumul_sim_comp"                : False, 
        "diff_sim_comp"                 : False, 
        "scatter_comp_collection"       : False,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    # Creating updated file list.
    outputList = {
        "id": [],
        "filename": [],
    }

    session["outputList"] = outputList
    session["runtime"] = runtime
    session["ouptut_config"] = ouptut_config

    return redline_vis_generate(details)
 

# used when generating generic event html 
def redline_vis_generic_eventhtml(details, io_stringHtml, io_pngList, io_pngStrings):

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_generic_eventhtml {details}")

    ouptut_config = {

        #competitor or generic switch
        "competitorAnalysis"  : False, # if analysis is generic of compeitor based.
        
        #generic non-png
        "duration_csv_generic"          : False, 
        "pacing_table_csv_generic"      : False, 
        "pdf_report_generic"            : False,

        #generic png
        "pie_generic"                   : True, 
        "bar_stacked_dist_generic"      : True,  
        "violin_generic"                : True,  
        "radar_median_generic"          : True,  
        "cutoff_bar_generic"            : True,  
        "histogram_nettime_generic"     : True,  
        "catbar_avgtime_generic"        : True,  
        "correlation_bar_generic"       : True,  
        "heatmap_correlation_generic"   : True, 
        "scatter_generic_collection"    : True,

        #Competitor-png
        "html_info_comp"                : False,
        "pdf_report_comp"               : False,

        #competitor png
        "pie_comp"                      : False, 
        "bar_stacked_dist_comp"         : False, 
        "violin_comp"                   : False, 
        "radar_percentile_comp"         : False, 
        "bar_sim_comp"                  : False, 
        "cumul_sim_comp"                : False, 
        "diff_sim_comp"                 : False, 
        "scatter_comp_collection"       : False,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    # Creating updated file list.
    outputList = {
        "id": [],
        "filename": [],
    }

    session["outputList"] = outputList
    session["runtime"] = runtime
    session["ouptut_config"] = ouptut_config
  
    return redline_vis_generate(details)

def redline_vis_developer():

    logger = rl_data.get_logger()
    logger.debug(f"redline_vis_developer")

    # session configuration variable
    ouptut_config = {
        #competitor or generic switch
        "competitorAnalysis"  : True, # if analysis is generic of compeitor based.

        #generic png
        "pie_generic"                   : True, 
        "bar_stacked_dist_generic"      : True,  
        "violin_generic"                : True,  
        "radar_median_generic"          : True,  
        "cutoff_bar_generic"            : True,  
        "histogram_nettime_generic"     : True,  
        "catbar_avgtime_generic"        : True,  
        "correlation_bar_generic"       : True,  
        "heatmap_correlation_generic"   : True, 
        "scatter_generic_collection"    : True,
        
        #generic non-png
        "duration_csv_generic"          : True, 
        "pacing_table_csv_generic"      : True, 
        "pdf_report_generic"            : True,

        #competitor png
        "pie_comp"                      : True, 
        "bar_stacked_dist_comp"         : True, 
        "violin_comp"                   : True, 
        "radar_percentile_comp"         : True, 
        "bar_sim_comp"                  : True, 
        "cumul_sim_comp"                : True, 
        "diff_sim_comp"                 : True, 
        "scatter_comp_collection"       : True,

        #Competitor-png
        "html_info_comp"                : True,
        "pdf_report_comp"               : True,
    }

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
    
    # Creating updated file list.
    outputList = {
        "id": [],
        "filename": [],
    }

    session["outputList"] = outputList
    session["runtime"] = runtime
    session["ouptut_config"] = ouptut_config


    #details = {"competitor": "STEPHANIE STEPHEN",  "race_no": "330", "event": "WomensSinglesCompetitive2024"}

    details = { "competitor": "STEPHEN ANTHONY CLEARY", "race_no": "425", "event": "MensSinglesCompetitive2024"}

    #details = {"competitor": "DENNIS OH", "race_no": "1387", "event": "MensDoubles2024"}

    #details = {"competitor": "DENNIS OH", "race_no": "1387", "event": "MensDoubles2024"}

    #details =  {"competitor": "JAMIE BARNETT", "race_no": "G1759", "event": "MensSinglesOpen2024"}
    #details =  {"competitor": "ANGIE LEK", "race_no": "95", "event": "WomensSinglesOpen2024"}

    #details =  {"competitor": None, "race_no": None, "event": "WomensSinglesOpen2024"}


    #competitor details set to False
    return redline_vis_generate(details)