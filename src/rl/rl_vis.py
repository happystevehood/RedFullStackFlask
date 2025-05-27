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

# local inclusion.
import rl.rl_data as rl_data

# Otherwise get this warning - UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail
mpl.use('agg')
 
#Boolean to decide if output warningsto log
OutputInfo=False


#############################
# Tidy the data/data frame
#############################
def tidyTheData(df, filename):

    logger = rl_data.get_logger()
    runtimeVars = session.get('runtime', {})

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
    runtimeVars['EventCutOffCount'][:] = [0 for _ in runtimeVars['EventCutOffCount']]

    # Index to last item
    MyIndex = len(runtimeVars['EventListStart']) - 1

    #iterate the event list in reverse order
    for event in runtimeVars['EventListStart'][::-1]:

        #Note Event = runtimeVars['EventListStart'][MyIndex] below, may be tidier ways to write

        #reorganise data such that each event a duration in reverse format
        for x in df.index:

            # do not write to start time
            if MyIndex != 0:

                #if time format wrong, it causes excpetions.
                try:

                    df.loc[x,event] = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,event]                                   ) ,"%H:%M:%S.%f") 
                                                            - datetime.strptime(rl_data.convert_to_standard_time(df.loc[x,runtimeVars['EventListStart'][MyIndex-1]]) ,"%H:%M:%S.%f"))
 
                    # was originally 10 seconds, changeing to 45 seconds.....
                    #if value less than 45 seconds, then somthing wrong, data not trust worthy so want to drop the row.
                    if df.loc[x,event] < 45.0:
                        #print data...
                        if(OutputInfo == True): logger.debug(f"Removed Low value {filename} {x} {event} {df.loc[x,event]} {df.loc[x,'Pos']}")
                                                
                        #drop the row
                        df.drop(x, inplace = True)

                    # else if event is greater than 7 minutes
                    elif (df.loc[x,event] > 420.0):
                        
                        #Increment the CutOff event counter (minus 1 due the diff in lists EventListStart and EventCutOffCount)
                        runtimeVars['EventCutOffCount'][MyIndex-1] = runtimeVars['EventCutOffCount'][MyIndex-1] + 1

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
    for event in runtimeVars['EventList']:
        meanEventList.append(df[event].mean())

    # now I need to search for 2 NaN's side by side.

    # Index to last item
    MyIndex = len(runtimeVars['EventListStart']) - 1

    #iterate the event list in reverse order
    for event in runtimeVars['EventListStart'][::-1]:

        #Note Event = runtimeVars['EventListStart'][MyIndex] below, may be tidier ways to write

        #reorganise data such that each event a duration in reverse format
        for x in df.index:

            # do not check first element
            if MyIndex != 0:

                    #if two consecutive are non numbers. 
                    if (pd.isnull(df.loc[x,runtimeVars['EventListStart'][MyIndex]]) and pd.isnull(df.loc[x,runtimeVars['EventListStart'][MyIndex-1]])):
                        # then need to calculate the duration of two events.

                        #if time format wrong, it causes excpetions.
                        try: 

                            twoEventDuration = timedelta.total_seconds(datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,event]                                   ),"%H:%M:%S.%f") 
                                                                     - datetime.strptime(rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars['EventListStart'][MyIndex-2]]),"%H:%M:%S.%f"))
                            #change from 60 seconds to 90 seconds
                            if (twoEventDuration < 90.0):
                                if(OutputInfo == True): logger.debug(f"2 EventDurLow {filename} {x} {event} {twoEventDuration}")
                                #drop the row
                                df.drop(x, inplace = True)
                            else:        
                                df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] = (twoEventDuration * meanEventList[MyIndex-2] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])
                                df.loc[x,runtimeVars['EventListStart'][MyIndex]]  = (twoEventDuration * meanEventList[MyIndex-1] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])

                        except (ValueError, TypeError):
                                #This will catch the competitors where NET time is "DNF" etc....

                                #Set Time values to None
                                df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] = float("nan")
                                df.loc[x,runtimeVars['EventListStart'][MyIndex]] = float("nan")

                                #print(f"tidyTheData ValueError, TypeError: {x} {event} {MyIndex} {rl_data.convert_to_standard_time(dforig.loc[x,event])} {rl_data.convert_to_standard_time(dforig.loc[x,runtimeVars['EventListStart'][MyIndex-2]])}")

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
                if(OutputInfo == True): logger.debug(f"Removed Low NetTime {filename} {x} {df.loc[x,'Net Time']} {df.loc[x,'Pos']}")
                #drop the row
                df.drop(x, inplace = True)
                # added as this can cause problems dur the next calculations below.
                continue
               
            #Reset Calculated time for this index
            calculatedNetTime = 0.0

            #iterate the event list in reverse order
            for event in runtimeVars['EventListStart']:
                #print(f"event in {x} {event}")
                calculatedNetTime = calculatedNetTime + df.loc[x,event] 

            #Store the event time.
            df.loc[x,'Calc Time'] = calculatedNetTime    

            #if NetTime - Calculated time is more than 13 seconds
            if (abs(df.loc[x,'Net Time'] - calculatedNetTime) > 13):                               
                if(OutputInfo == True):  logger.debug(f"Warning: NetTime Mismatch {filename} {abs(df.loc[x,'Net Time'] - calculatedNetTime)}, {x}"  )

        except (ValueError, TypeError):
                 #Set Time values to None
                #df.loc[x,'Calc Time'] = float("nan")
                #df.loc[x,'Net Time'] = float("nan")

                #drop the row
                df.drop(x, inplace = True)

    #On a column by colum basis 
    for event in runtimeVars['EventList'][::1]:
        #add a rank column per event
        df[event + ' Rank'] = df[event].rank(ascending=True)

    #add a Rank Average Column initialised to 0
    df['Average Rank'] = 0.0

    # Calculate the Average Ranks per competitor
    for x in df.index:

        RankTotal = 0
        for event in runtimeVars['EventList'][::1]:
            
            #add a running total of Rank
            RankTotal = RankTotal + df.loc[x, event + ' Rank']

        #write the rank average to the df.
        df.loc[x,'Average Rank'] = RankTotal / len(runtimeVars['EventList'])
    
 ################################
# Ouyput the compentitors data
# returns a competitor index
################################
def competitorDataOutput(df):

    runtimeVars = session.get('runtime', {})

    runtimeVars['stringPdf'] = '<table class="styled-table">'

    #initialise return value to -1
    compIndex = -1

    #search for the competitor name in the dataframe
    
    # get mask based on substring matching competitor name.
 
     #if relay 
    if 'Member1' in df.columns:
        nameMask = df['Name'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem1Mask = df['Member1'].str.contains(runtimeVars['competitorName'], na=False, regex=False) 
        mem2Mask = df['Member2'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        mem3Mask = df['Member3'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        mem4Mask = df['Member4'].str.contains(runtimeVars['competitorName'], na=False, regex=False)
        compMask = nameMask | mem1Mask | mem2Mask | mem3Mask | mem4Mask & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False, regex=False)

    else:
        compMask = df['Name'].str.contains(runtimeVars['competitorName'], regex=False) & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False, regex=False)

    #dataframe with matching competitors and race number
    compDF = df[compMask]

    #if there is at least one match.
    if (len(compDF.index) > 0):

        #get the index of first match.
        compIndex = df[compMask].index.values.astype(int)[0]
    
        #if category column exist.
        if 'Category' in df.columns:
            compCat = df.loc[compIndex, "Category"]

        if 'Member1' in df.columns:

            runtimeVars['stringPdf'] += '<tr><td><strong>Team Name </strong></td><td>' +  df.loc[compIndex, "Name"].title() + "</td></tr>"
            runtimeVars['stringPdf'] += '<tr><td><strong>Members </strong></td><td>' +  df.loc[compIndex, "Member1"].title() +  df.loc[compIndex, "Member2"].title() +  df.loc[compIndex, "Member3"].title() +  df.loc[compIndex, "Member4"].title() + "</td></tr>"
            
        else:
             runtimeVars['stringPdf'] += '<tr><td><strong>Competitor Name </strong></td><td>' +  df.loc[compIndex, "Name"].title()  + "</td></tr>"

        runtimeVars['stringPdf'] += '<tr><td><strong>Gender          </strong></td><td>' +  df.loc[compIndex, "Gender"]  + "</td></tr>"

        if 'Category' in df.columns:
            runtimeVars['stringPdf'] += '<tr><td><strong>Category        </strong></td><td>' +  compCat  + "</td></tr>"

        runtimeVars['stringPdf'] += '<tr><td><strong>Event           </strong></td><td>' +  runtimeVars['eventDataList'][1] + "</td></tr>"
        runtimeVars['stringPdf'] += '<tr><td><strong>Wave            </strong></td><td>' +  df.loc[compIndex, "Wave"] + "</td></tr>"
        runtimeVars['stringPdf'] += '<tr><td><strong>Position        </strong></td><td>' +  str(df.loc[compIndex, "Pos"]) + ' of '+ str(len(df.index)) + ' finishers.'+ "</td></tr>"

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
            runtimeVars['stringPdf'] += '<tr><td><strong>Cat Pos         </strong></td><td>' +  str(df.loc[compIndex, "Cat Pos"])+ ' of '+ str(df['Category'].value_counts()[compCat]) + ' finishers.' + "</td></tr>"
            
        runtimeVars['stringPdf'] += '<tr><td><strong>Calc Time</strong></td><td>' + rl_data.format_seconds(df.loc[compIndex, "Calc Time"]) + "</td></tr>"
        runtimeVars['stringPdf'] += '<tr><td><strong>Time Adj</strong></td><td>' + rl_data.format_seconds(df.loc[compIndex, "Time Adj"]) + "</td></tr>"
        runtimeVars['stringPdf'] += '<tr><td><strong>Net Time</strong></td><td>' + rl_data.format_seconds(df.loc[compIndex, "Net Time"]) + "</td></tr>"
        runtimeVars['stringPdf'] += '<tr><td><strong>Average Event Rank </strong></td><td>{:.1f}'.format(df.loc[compIndex, "Average Rank"]) + "</td></tr>"

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
                
            #filter by category
            dfcat = df[df['Category']==compCat].copy()

            #On a column by colum basis 
            for event in runtimeVars['EventList']:
                #add a rank column per event
                dfcat.loc[:, event + ' CatRank'] = dfcat[event].rank(ascending=True)

            #add a Rank Average Column initialised to 0
            dfcat['Average Cat Rank'] = 0.0

            # Calculate the Average Ranks per competitor
            for x in dfcat.index:
                RankTotal = 0
                for event in runtimeVars['EventList'][::1]:
                    #add a running total of Rank
                    RankTotal = RankTotal + dfcat.loc[x, event + ' CatRank']

                #write the rank average to the df.
                dfcat.loc[x,'Average Cat Rank'] = RankTotal / len(runtimeVars['EventList'])

            runtimeVars['stringPdf'] += '<tr><td><strong>Average Event CatRank </strong></td><td>{:.1f}'.format(dfcat.loc[compIndex, "Average Cat Rank"]) + "</td></tr>"

        runtimeVars['stringPdf'] += '</table><br>'

        #if category column exist.
        if (('Category' in df.columns) and (compCat != "All Ages")):
            # Create the pandas DataFrame
            tableDF = pd.DataFrame(index=runtimeVars['EventList'],columns=['Time', 'Rank', 'CatRank'])
        else:
            tableDF = pd.DataFrame(index=runtimeVars['EventList'],columns=['Time', 'Rank'])

        for event in runtimeVars['EventList']:
            # Format individual float values directly
            time_val = compDF.loc[compIndex, event]
            rank_val = compDF.loc[compIndex, f"{event} Rank"]

            tableDF.loc[event, 'Time'] = f"{time_val:.1f}" if pd.notnull(time_val) else ''
            tableDF.loc[event, 'Rank'] = f"{rank_val:.1f}" if pd.notnull(rank_val) else ''

            # Only handle CatRank if needed
            if ('Category' in df.columns) and (compCat != "All Ages"):
                catrank_val = dfcat.loc[compIndex, f"{event} CatRank"]
                tableDF.loc[event, 'CatRank'] = f"{catrank_val:.1f}" if pd.notnull(catrank_val) else ''

        #forcibly remove the style attribute from string
        runtimeVars['stringPdf'] += re.sub( ' style=\"text-align: right;\"','',tableDF.to_html())
        runtimeVars['stringPdf'] += '<br>'
    else:

        logger = rl_data.get_logger()
        logger.warning(f"No data for the selected competitor {runtimeVars['competitorName']} in the selected event {runtimeVars['eventDataList'][0]}")

    return compIndex

################################
# Tidy the data/data frame part 2
################################
def tidyTheData2(df):

    runtimeVars = session.get('runtime', {})

    ####Remove Rank columns as dont need anymore
    for event in runtimeVars['EventList'][::1]:
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

    #Remove boring columns
    df.drop(columns=['Race No','Name', 'Gender', 'Wave'], inplace=True)

    if 'Team' in df.columns:
        df.drop('Team', axis=1, inplace = True)

    if 'Member1' in df.columns:
        df.drop('Member1', axis=1, inplace = True)
        df.drop('Member2', axis=1, inplace = True)
        df.drop('Member3', axis=1, inplace = True)
        df.drop('Member4', axis=1, inplace = True)

    if 'Cat Pos' in df.columns:
        df.drop('Cat Pos', axis=1, inplace = True)

    if 'Cat Pos' in df.columns:
        df.drop('Cat Pos', axis=1, inplace = True)

    if 'Net Gender Pos' in df.columns:
        df.drop('Net Gender Pos', axis=1, inplace = True)

    #if 'Time Adj' in df.columns:
    #    df.drop('Time Adj', axis=1, inplace = True)

    #drop rows with empty data 
    df.dropna(inplace = True )

#############################
# Correlation
#############################

def ShowCorrInfo(df,competitorIndex=-1):
    #remove category for corralation info

    config = session.get('config', {})
    runtimeVars = session.get('runtime', {})

    dfcorr = df.copy(deep=True)

    #next level tidying
    tidyTheData2(dfcorr)

    if 'Pos' in dfcorr.columns:
        dfcorr.drop('Pos', axis=1, inplace = True)
    
    if 'Category' in dfcorr.columns:
        dfcorr.drop('Category', axis=1, inplace = True)

    #get rid of this in place of 'Calc Time'
    if 'Time Adj' in dfcorr.columns:
        dfcorr.drop('Time Adj', axis=1, inplace = True)

    #get corrolation info
    corr_matrix = dfcorr.corr()

    #if a competitor is selected dont show correlation bar chart    
    if(competitorIndex == -1):

        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Corr' + '.png')
        #for PDF creation
        runtimeVars['pngList'].append(str(filepath))
        runtimeVars['pngStrings'].append(rl_data.pngStringEventBarCorr)

        #check if file exists
        if (os.path.isfile(filepath) == False):

            plt.figure(figsize=(10, 10))
            
            # Shows a nice correlation barchar
            heatmap = sns.barplot( data=corr_matrix['Net Time'])
            
            for i in heatmap.containers:
                heatmap.bar_label(i,fmt='%.2f')
            
            plt.xticks(rotation=70)
            plt.ylabel('Total Time')

            heatmap.set_title('Event Correlation V Total Time ' + runtimeVars['eventDataList'][1], fontdict={'fontsize':12}, pad=10);

            # Output/Show depending of global variable setting with pad inches
            if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
            if ( config['pltShow'] ):   plt.show()
            if ( config['pltPngOut'] or  config['pltShow']):   plt.close()
    
    #get the highest and lowest correlation events
    #Correction works better with Calculated time compared with Net Time compared with 
    corr_matrix = corr_matrix[['Net Time']].sort_values(by='Net Time', ascending=False)

    #depending if a competitor is selected
    if (competitorIndex == -1):
        runtimeVars['pngStrings'].append(rl_data.pngStringEventScatterPlot)
    else:
        runtimeVars['pngStrings'].append(rl_data.pngStringEventScatterPlotCompetitor)

    if (config['allScatter'] == False):

        #Show scatter chart with higest correlation.
        ShowScatterPlot(df, corr_matrix.index[1], corr=corr_matrix.at[corr_matrix.index[1],'Net Time'],competitorIndex=competitorIndex)

        #Show scatter chart with lowest correlation.
        ShowScatterPlot(df, corr_matrix.index[-1], corr=corr_matrix.at[corr_matrix.index[-1],'Net Time'],competitorIndex=competitorIndex)
        runtimeVars['pngStrings'].append("")

    else:
        for event in corr_matrix.index:
            #skip next time scatter plot
            if (event != 'Net Time'):
                #Show scatter Plot
                ShowScatterPlot(df, event, corr=corr_matrix.at[event,'Net Time'],competitorIndex=competitorIndex )

                #add empty line EXCEPT FOR ONE STATION
                if (event != 'Run'): #this could be any
                    runtimeVars['pngStrings'].append("")

    if( config['showHeat'] ):

        #get corrolation info
        corr_matrix = dfcorr.corr()

        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'CorrHeat' + '.png')

        #for PDF creation
        runtimeVars['pngList'].append(str(filepath)) 
        runtimeVars['pngStrings'].append(rl_data.pngStringEventHeatCorr)

        #check if file exists
        if (os.path.isfile(filepath) == False):
        
            plt.figure(figsize=(10, 10))
            heatmap = sns.heatmap(corr_matrix, vmin=-0, vmax=1, annot=True, cmap='BrBG')
            heatmap.set_title('Correlation Heatmap ' + runtimeVars['eventDataList'][1], fontdict={'fontsize':12}, pad=12);

            # Output/Show depending of global variable setting with pad inches
            if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
            if ( config['pltShow'] ):   plt.show()
            if ( config['pltPngOut'] or  config['pltShow']):   plt.close()


############################
# Histogram Age Categories
#############################

def ShowHistAgeCat(df):

    runtimeVars = session.get('runtime', {})

    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Hist' + '.png')
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))
    runtimeVars['pngStrings'].append(rl_data.pngStringEventHistogram)

    # check if file exists
    if (os.path.isfile(filepath) == False): 

        config = session.get('config', {}) 

        # set num of categories to be 3 by default
        num_cat        = 3

        plt.figure(figsize=(10, 10))

        # do for 2023
        if (runtimeVars['eventDataList'][2]=='2023'):

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
            if (runtimeVars['eventDataList'][2]=='2024'):

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
        plt.title(runtimeVars['eventDataList'][1] + ' Time Distrbution')
        plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

        # Output/Show depending of global variable setting.
        if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
        if ( config['pltShow'] ):   plt.show()
        if ( config['pltPngOut'] or  config['pltShow']):   plt.close()

#############################
# Bar chart Events
#############################
def ShowBarChartEvent(df, competitorIndex=-1):
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    # --- Filename Generation ---
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    if competitorIndex == -1:
        filename = f"{event_name_for_file}_BarChart.png"
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(filename)
        if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
        if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
        runtimeVars['pngStrings'].append(rl_data.pngStringEventBarChart) 
    else:
        competitor_name_from_df = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Competitor"
        competitor_name_for_file = competitor_name_from_df.replace(" ", "_").replace(",", "").replace("'", "")
        filename = f"{event_name_for_file}_{competitor_name_for_file}_BarChart.png"
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename)
        if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
        if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
        runtimeVars['pngStrings'].append(rl_data.pngStringEventBarChartCompetitor)
    
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars

    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation.")
        return
        
    #print(f"Generating Bar Chart with Top Legends for event {runtimeVars['eventDataList'][0]} at {filepath}")

    station_names = runtimeVars['EventList']
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

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
        #print(f"Saved square bar chart with top legends to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    if config.get('pltPngOut', False) or config.get('pltShow', False):
        plt.close(fig)
    
    session['runtime'] = runtimeVars

#############################
# Violin chart Events
#############################

def ShowViolinChartEvent(df, competitorIndex=-1):
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    # --- Filename Generation ---
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    if competitorIndex == -1:
        filename = f"{event_name_for_file}_Violin.png"
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(filename)
        if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
        if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
        runtimeVars['pngStrings'].append(rl_data.pngStringEventViolinChart)
    else:
        competitor_name = df.loc[competitorIndex, 'Name'] if 'Name' in df.columns else "Competitor"
        competitor_name_for_file = competitor_name.replace(" ", "_").replace(",", "").replace("'", "")
        filename = f"{event_name_for_file}_{competitor_name_for_file}_Violin.png"
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename)
        if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
        if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
        runtimeVars['pngStrings'].append(rl_data.pngStringEventViolinChartCompetitor)
    
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars

    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation.")
        return
        
    #print(f"Generating Violin Chart for event {runtimeVars['eventDataList'][0]} at {filepath}")

    station_data_df = df[runtimeVars['EventList']].copy()
    for col in runtimeVars['EventList']:
        station_data_df[col] = pd.to_numeric(station_data_df[col], errors='coerce')

    all_station_times_flat = station_data_df.values.flatten()
    all_station_times_flat = all_station_times_flat[~np.isnan(all_station_times_flat)] 
    
    cutoff_time = 600.0 
    if len(all_station_times_flat) > 0:
        pass 

    df_melted = station_data_df.melt(var_name='Station', value_name='Time (s)')
    df_melted['Station'] = pd.Categorical(df_melted['Station'], categories=runtimeVars['EventList'], ordered=True)
    df_melted_filtered = df_melted[df_melted['Time (s)'] < cutoff_time].dropna(subset=['Time (s)'])

    plt.figure(figsize=(12, 12))
    ax = plt.gca() # Get current axes to use for annotations later

    if not df_melted_filtered.empty:
        sns.violinplot(ax=ax, x='Station', y='Time (s)', data=df_melted_filtered, 
                       order=runtimeVars['EventList'], 
                       inner='quartile', 
                       cut=1,          
                       hue='Station',         
                       palette='viridis',     
                       legend=False,          
                       linewidth=1.5,   
                       density_norm='width')
    else:
        print("Warning: All data filtered out by cutoff time. Plotting empty chart structure.")
        ax.set_xticks(np.arange(len(runtimeVars['EventList'])))
        ax.set_xticklabels(runtimeVars['EventList'], rotation=90, fontsize=9)

    if competitorIndex != -1:
        compList_station_times_raw = [] # Store raw times for labeling
        compList_station_times_plot = [] # Store potentially clamped times for plotting marker

        for event in runtimeVars['EventList']:
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

        x_positions = np.arange(len(runtimeVars['EventList']))
        
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
    
    plt.tight_layout(pad=1.0)

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.3)
        #print(f"Saved violin chart to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    if config.get('pltPngOut', False) or config.get('pltShow', False):
        plt.close()
    
    session['runtime'] = runtimeVars

#############################
# Bar chart Cut Off Events
#############################

def ShowBarChartCutOffEvent(df):

    runtimeVars = session.get('runtime', {})

    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'CutOffBar' + '.png')
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))
    runtimeVars['pngStrings'].append(rl_data.pngStringEventBarChartCutoff)

    # check if file exists  
    if (os.path.isfile(filepath) == False):
        config = session.get('config', {})

        fig, ax = plt.subplots(figsize=(10, 10))

        #null list
        cutOffEventList = []
        MyIndex = 0

        for event in runtimeVars['EventList'][::]:
             #add percentage to list
            cutOffEventList.append((100*runtimeVars['EventCutOffCount'][MyIndex]) / len(df.index))
            MyIndex = MyIndex + 1

        ax.bar(runtimeVars['EventList'], cutOffEventList,       color='red'   , label='Partipants > 7min')

        for container in ax.containers:
            ax.bar_label(container,fmt='%.1f%%')

        plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)
        plt.tick_params(axis='x', labelrotation=90)
        plt.ylabel('Num Participants')
        plt.title(runtimeVars['eventDataList'][1] + ' Station 7 Min Stats')
        plt.legend() 

        # Output/Show depending of global variable setting with some padding
        if ( config['pltPngOut'] ): plt.savefig(filepath , bbox_inches='tight', pad_inches = 0.5)
        if ( config['pltShow'] ):   plt.show()
        if ( config['pltPngOut'] or  config['pltShow']):   plt.close()

#############################
# PieChartAverage
#############################
def ShowPieChartAverage(df,competitorIndex=-1):

    config = session.get('config', {})
    runtimeVars = session.get('runtime', {})

    # Just do Generic pie chart based on mean time per event.
    if(competitorIndex==-1):

        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Pie' + '.png')
        #for PDF creation
        runtimeVars['pngList'].append(str(filepath))
        runtimeVars['pngStrings'].append(rl_data.pngStringEventPieChart)

        # check if file exists
        if (os.path.isfile(filepath) == False):

            plt.figure(figsize=(10, 10))

            meanEventList = []
            meanEventListLabel = []
            totalMeanTime = 0.0
        
            # get the median time for each event.
            for event in runtimeVars['EventList']:
                meanEventList.append(df[event].mean())
                totalMeanTime = totalMeanTime + int(df[event].mean())

                eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df[event].mean())//60 ,int(df[event].mean())%60)
                meanEventListLabel.append(eventLabelString)

            totalMeanTimeString = "{:1d}m {:2d}s".format(int(totalMeanTime)//60 ,int(totalMeanTime)%60)
            plt.title(runtimeVars['eventDataList'][1] + ' Average Station Breakdown : ' + totalMeanTimeString )
        
            #create pie chart = Use Seaborn's color palette 'Set2'
            plt.pie(meanEventList, labels = meanEventListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))
            
            # Output/Show depending of global variable setting. 
            if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
            if ( config['pltShow'] ):   plt.show()
            if ( config['pltPngOut'] or  config['pltShow']):   plt.close()

    # else do competitor specific pie chart based on actual time per event.
    else:

        filepath = Path(rl_data.PNG_COMP_DIR) / Path(runtimeVars['eventDataList'][0] + runtimeVars['competitorName'] + 'Pie' + '.png')

        #for PDF creation
        runtimeVars['pngList'].append(str(filepath))
        runtimeVars['pngStrings'].append(rl_data.pngStringEventPieChartCompetitor)

        # check if file exists  
        if (os.path.isfile(filepath) == False):

            plt.figure(figsize=(10, 10))

            compEventList = []
            compEventListLabel = []

            # get the median time for each event.
            for event in runtimeVars['EventList']:
            
                compEventList.append(df.loc[competitorIndex,event])
                eventLabelString = "{}\n{:1d}m {:2d}s".format(event, int(df.loc[competitorIndex,event])//60 ,int(df.loc[competitorIndex,event])%60)
                compEventListLabel.append(eventLabelString)

            totalCompTimeString = "{:1d}m {:2d}s".format(int(df.loc[competitorIndex,'Calc Time'])//60 ,int(df.loc[competitorIndex,'Calc Time'])%60)
            plt.title(runtimeVars['eventDataList'][1] + ' ' + df.loc[competitorIndex,'Name'] + ' Stations: ' + totalCompTimeString )

            #create pie chart = Use Seaborn's color palette 'Set2'
            plt.pie(compEventList, labels = compEventListLabel, startangle = 0, autopct='%1.1f%%', colors=sns.color_palette('Set2'))

            # Output/Show depending of global variable setting. 
            if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.3)
            if ( config['pltShow'] ):   plt.show()
            if ( config['pltPngOut'] or  config['pltShow']):   plt.close()


#############################
# Show Scatter Plot
#############################
def ShowScatterPlot(df, eventName, corr, competitorIndex=-1):
        
    runtimeVars = session.get('runtime', {})

    if (competitorIndex == -1):
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + eventName + 'Scat' + '.png')
    else:
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(runtimeVars['eventDataList'][0] + eventName + runtimeVars['competitorName'] + 'Scat' + '.png')
    
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

    # check if file exists
    if (os.path.isfile(filepath) == False):

        config = session.get('config', {})

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

            if df[eventName][index] <  df[eventName].quantile(0.25) :
                #Add to fastest quartile list
                q1ListX.append(df[eventName][index])
                q1ListY.append(df['Pos'][index])
                if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]
            
            elif df[eventName][index] <  df[eventName].quantile(0.50) :
                #Add to q2 list
                q2ListX.append(df[eventName][index])
                q2ListY.append(df['Pos'][index])
                if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]
                
            elif df[eventName][index] <  df[eventName].quantile(0.75) :
                #Add to q3 list
                q3ListX.append(df[eventName][index])
                q3ListY.append(df['Pos'][index])
                if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]

            elif df[eventName][index] <  df[eventName].quantile(0.98):
                #Add to slowest quartile list
                q4ListX.append(df[eventName][index])
                q4ListY.append(df['Pos'][index])
                if(df['Pos'][index]> maxPos): maxPos = df['Pos'][index]

        plt.figure(figsize=(10, 10))

        plt.scatter(x=q1ListX, y=q1ListY, c ="blue",  label="0%-24%")
        plt.scatter(x=q2ListX, y=q2ListY, c ="brown", label="25%-49%")
        plt.scatter(x=q3ListX, y=q3ListY, c ="green", label="50%-74%")
        plt.scatter(x=q4ListX, y=q4ListY, c ="red",   label="75%-98%")
        
        if (competitorIndex != -1):
            plt.plot([df.loc[competitorIndex,eventName]], [df.loc[competitorIndex,'Pos']], marker='+', markersize=20.0, markeredgewidth=2.0, color='navy', linewidth=0.0)

            #coorinates via trial an error.
            plt.text(df[eventName].min()*1.1, maxPos+1.0,'+='+ df.loc[competitorIndex,'Name'] , fontsize = 10, color='navy')

        #conver corr float to str
        if (corr):
            corrstr = "{:1.2f}".format(corr)
        
        plt.title(runtimeVars['eventDataList'][1] + ' ' + eventName + ' Corr. ' + corrstr)
        plt.ylabel("Ovearll Position")
        plt.xlabel("Station Time")
        plt.legend()
        plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

        # Output/Show depending of global variable setting. 
        if ( config['pltPngOut'] ): plt.savefig(filepath , bbox_inches='tight', pad_inches = 0.3)
        if ( config['pltShow'] ):   plt.show()
        if ( config['pltPngOut'] or  config['pltShow']):   plt.close()

#############################
# Bar chart Events
#############################

def ShowRadar(df, competitorIndex=-1):
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    # --- Filename Generation (simplified for clarity in this snippet) ---
    if competitorIndex == -1:
        event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
        filename = f"{event_name_for_file}Radar.png" # New filename
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(filename)
        runtimeVars['pngStrings'].append(rl_data.pngStringEventRadarChart) # Ensure this string is appropriate
    else:
        competitor_name_for_file = df.loc[competitorIndex, 'Name'].replace(" ", "_").replace(",", "").replace("'", "")
        event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
        filename = f"{event_name_for_file}{competitor_name_for_file}Radar.png"
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename)
        runtimeVars['pngStrings'].append(rl_data.pngStringEventRadarChartCompetitor)
    
    runtimeVars['pngList'].append(str(filepath))

    # Check if file exists or force generation
    if not os.path.isfile(filepath):    
        num_vars = len(runtimeVars['EventList'])
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        
        fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True)) # Use consistent larger size

        if competitorIndex == -1:
            # --- Generic Radar: Median Actual Times (Y-axis in seconds) ---
            # Faster times (lower seconds) will be closer to the center.
            
            median_event_times_actual = []
            station_axis_labels = [] # For station names only on this plot

            for event in runtimeVars['EventList']:
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

            for event in runtimeVars['EventList']:
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



        if config.get('pltPngOut', False):
            plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        if config.get('pltShow', False):
            plt.show()
        
        if config.get('pltPngOut', False) or config.get('pltShow', False) : # Corrected logic
            plt.close(fig)

    session['runtime'] = runtimeVars



def ShowGroupBarChart(df, competitorIndex=-1):
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    if competitorIndex == -1:
        print("Error: ShowGroupBarChart requires a valid competitorIndex.")
        return

    # --- Filename Generation ---
    competitor_name = df.loc[competitorIndex, 'Name']
    competitor_name_for_file = competitor_name.replace(" ", "_").replace(",", "").replace("'", "")
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    filename = f"{event_name_for_file}_{competitor_name_for_file}BarSimilar.png" # More descriptive
    filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename)
    
    # Ensure pngStrings and pngList are handled correctly if they are part of runtimeVars
    if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
    if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
    
    runtimeVars['pngStrings'].append(rl_data.pngStringEventGroupBarChartCompetitor) # Make sure this constant exists
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars # Save early in case of return

    # Check if file exists or force generation
    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation.")
        return
    
    #print(f"Generating Group Bar Chart for {competitor_name} at {filepath}")

    # 0. Get the competitor's time for each event
    competitor_event_times = []
    station_names = runtimeVars['EventList'] # Use this for x-axis labels

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
        print(f"No similar finishers found for {competitor_name}.")
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

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        #print(f"Saved chart to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    # Always close the plot after saving/showing to free up memory
    plt.close(fig)

    session['runtime'] = runtimeVars # Save runtimeVars back to session


def ShowCumulativeTimeComparison(df, competitorIndex=-1):
    if competitorIndex == -1:
        print("Error: ShowCumulativeTimeComparison requires a valid competitorIndex.")
        return

    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    competitor_name = df.loc[competitorIndex, 'Name']
    competitor_name_for_file = competitor_name.replace(" ", "_").replace(",", "").replace("'", "")
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    filename = f"{event_name_for_file}_{competitor_name_for_file}CumulTime.png"
    filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename)
    
    if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
    if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
    # Ensure you have a unique string for this chart type if needed for your framework
    runtimeVars['pngStrings'].append(rl_data.pngStringEventCumulativeChartCompetitor) 
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars

    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation.")
        return
        
    #print(f"Generating Cumulative Time Chart for {competitor_name} at {filepath}")

    station_names = runtimeVars['EventList']
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
        print(f"No similar finishers found for {competitor_name}. Using competitor's times for comparison line.")
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

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        #print(f"Saved cumulative chart with mm:ss labels to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    plt.close(fig)
    session['runtime'] = runtimeVars


def ShowStationTimeDifferenceChart(df, competitorIndex =-1):

    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    if competitorIndex == -1:
        print("Error: ShowStationTimeDifferenceChart requires a valid competitorIndex.")
        return

    competitor_name = df.loc[competitorIndex, 'Name']
    competitor_name_for_file = competitor_name.replace(" ", "_").replace(",", "").replace("'", "")
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    filename = f"{event_name_for_file}_{competitor_name_for_file}StationTimeDiff.png"
    filepath = Path(rl_data.PNG_COMP_DIR) / Path(filename) # Assuming a directory

    if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
    if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
    # Add appropriate pngString for this new chart type
    runtimeVars['pngStrings'].append(rl_data.pngStringEventStationDiffChartCompetitor) 
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars

    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation.")
        return
        
    #print(f"Generating Station Time Difference Chart for {competitor_name} at {filepath}")

    station_names = runtimeVars['EventList']
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

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        #print(f"Saved station time difference chart to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    plt.close(fig)
    session['runtime'] = runtimeVars

def ShowCatBarCharts(df):
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})

    # --- Filename Generation ---
    event_name_for_file = runtimeVars['eventDataList'][0].replace(" ", "_").replace("/", "_")
    filename = f"{event_name_for_file}_StatByCategory.png"
    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(filename)
    
    if 'pngStrings' not in runtimeVars: runtimeVars['pngStrings'] = []
    if 'pngList' not in runtimeVars: runtimeVars['pngList'] = []
    
    # Check if 'Category' column exists and if there's more than one unique category
    if 'Category' not in df.columns:
        print("Category column not found in DataFrame. Skipping chart generation Skipping for {runtimeVars['eventDataList'][0]}.")
        return

    unique_categories = sorted(df['Category'].dropna().unique())
    if len(unique_categories) <= 1:
        print(f"Not enough categories ({len(unique_categories)}) to generate a comparison chart. Skipping for {runtimeVars['eventDataList'][0]}.")
        return

    # You might want a new specific pngString for this chart type
    runtimeVars['pngStrings'].append(rl_data.pngStringEventCatGroupBar) 
    runtimeVars['pngList'].append(str(filepath))
    session['runtime'] = runtimeVars
    
    # Check if file exists or force generation
    if os.path.isfile(filepath) and not config.get('forcePng', False):
        print(f"File {filepath} already exists. Skipping generation for {runtimeVars['eventDataList'][0]}.")
        return

    #print(f"Generating Average Station Time by Category chart at {filepath}")

    station_names = runtimeVars['EventList']
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
    fig.tight_layout()

    if config.get('pltPngOut', False):
        plt.savefig(filepath, bbox_inches='tight', pad_inches=0.2)
        #print(f"Saved category bar chart to {filepath}")
    if config.get('pltShow', False):
        plt.show()
    
    plt.close(fig)
    session['runtime'] = runtimeVars


import pandas as pd
import numpy as np
import os
from pathlib import Path
# Assuming session, rl_data, runtimeVars, df are defined elsewhere
# Assuming rl_data.format_time_mm_ss helper function is available

def format_time_mm_ss(seconds_total): # Keep your robust formatter
    if pd.isna(seconds_total) or not isinstance(seconds_total, (int, float, np.number)):
        return "N/A"
    try:
        seconds_total = int(round(float(seconds_total)))
    except (ValueError, TypeError):
        return "N/A"
    minutes = seconds_total // 60
    seconds = seconds_total % 60
    return f"{minutes:02d}:{seconds:02d}"

def CreatePacingTable(df):
    runtimeVars = session.get('runtime', {})

    event_name_for_file = runtimeVars['eventDataList'][0]
    filepath = Path(rl_data.CSV_GENERIC_DIR) / Path(f"PacingTable{event_name_for_file}.csv")

    if os.path.isfile(filepath):
        print(f"File {filepath} already exists. Skipping generation for {runtimeVars['eventDataList'][0]}.")
        return
    
    print(f"Generating Pacing Table for event {runtimeVars['eventDataList'][0]}")

    station_names = runtimeVars['EventList']
    target_percentiles = np.arange(0.1, 1.0, 0.1) # 10%, 20%, ..., 90%

    # Define the window around the target percentile's POSITION to select the cohort
    # e.g., for 10th percentile, with a 5% window, consider athletes from 5th to 15th percentile rank
    COHORT_POSITION_WINDOW_PERCENTAGE = 0.05 # +/- 5 percentile points from the target

    pacing_table_data_list_of_dicts = [] 

    # --- Data Preparation and Cleaning ---
    df_cleaned = df.copy()
    df_cleaned['Net Time'] = pd.to_numeric(df_cleaned['Net Time'], errors='coerce')
    for event in station_names:
        df_cleaned[event] = pd.to_numeric(df_cleaned[event], errors='coerce')
    
    if 'Time Adj' in df_cleaned.columns:
        df_cleaned['Time Adj'] = pd.to_numeric(df_cleaned['Time Adj'], errors='coerce')
    else:
        print("Warning: 'Time Adj' column not found. Assuming all Time Adj are 0.")
        df_cleaned['Time Adj'] = 0 

    df_cleaned.dropna(subset=['Net Time'], inplace=True)
    if df_cleaned.empty:
        print("No valid numeric Net Time data to generate pacing table.")
        runtimeVars['pacingTable'] = []
        session['runtime'] = runtimeVars
        return None

    # Filter out athletes with non-zero 'Time Adj'
    df_for_pacing_calcs = df_cleaned[df_cleaned['Time Adj'].fillna(0) == 0].copy()

    # Fallback if filtering results in an empty DataFrame
    df_to_use_for_cohorts_and_percentiles = df_for_pacing_calcs
    if df_for_pacing_calcs.empty:
        print("Warning: No athletes found with Time Adj == 0. Pacing table will be based on all athletes.")
        df_to_use_for_cohorts_and_percentiles = df_cleaned
        if df_to_use_for_cohorts_and_percentiles.empty:
            print("Critical: No data left. Cannot generate table.")
            runtimeVars['pacingTable'] = []
            session['runtime'] = runtimeVars
            return None
    
    # Sort by Net Time to easily get positional percentiles
    df_sorted = df_to_use_for_cohorts_and_percentiles.sort_values(by='Net Time').reset_index(drop=True)
    total_ranked_athletes = len(df_sorted)

    if total_ranked_athletes == 0:
        print("No ranked athletes to process after filtering.")
        runtimeVars['pacingTable'] = []
        session['runtime'] = runtimeVars
        return None

    # Header row
    header_dict = {'Station': 'Station'}
    for p_val in target_percentiles:
        header_dict[f'Top {int(p_val*100)}%'] = f'Top {int(p_val*100)}%'
    pacing_table_data_list_of_dicts.append(header_dict)

    sum_of_avg_station_times_per_percentile = {f'Top {int(p*100)}%': 0.0 for p in target_percentiles}

    for station in station_names:
        station_pacing_row = {'Station': station}
        for p_val in target_percentiles:
            percentile_key_name = f'Top {int(p_val*100)}%'
            
            # Define the positional window
            # Example for p_val = 0.1 (10th percentile) and window = 0.05 (5%)
            # Lower rank percentile: 0.1 - 0.05 = 0.05 (5th percentile)
            # Upper rank percentile: 0.1 + 0.05 = 0.15 (15th percentile)
            lower_rank_percentile = max(0, p_val - COHORT_POSITION_WINDOW_PERCENTAGE)
            upper_rank_percentile = min(1, p_val + COHORT_POSITION_WINDOW_PERCENTAGE)
            
            start_index = int(lower_rank_percentile * total_ranked_athletes)
            # For upper bound, make sure it includes up to that percentile, so use ceil or adjust index
            end_index = int(np.ceil(upper_rank_percentile * total_ranked_athletes)) 
            # Ensure end_index does not exceed total_ranked_athletes
            end_index = min(end_index, total_ranked_athletes)


            # Ensure start_index is less than end_index for slicing
            if start_index >= end_index and total_ranked_athletes > 0: # If window is too small or at extremes
                # Fallback: take a small number of athletes around the target_index
                target_index = int(p_val * (total_ranked_athletes -1) ) # -1 because of 0-based indexing
                num_either_side = max(1, int(COHORT_POSITION_WINDOW_PERCENTAGE * total_ranked_athletes / 2))
                start_index = max(0, target_index - num_either_side)
                end_index = min(total_ranked_athletes, target_index + num_either_side + 1)

            cohort_df = df_sorted.iloc[start_index:end_index]
            
            avg_station_time_seconds = np.nan 
            if not cohort_df.empty and station in cohort_df.columns:
                valid_station_times = cohort_df[station].dropna()
                if not valid_station_times.empty:
                    avg_station_time_seconds = valid_station_times.mean()
            
            station_pacing_row[percentile_key_name] = rl_data.format_time_mm_ss(avg_station_time_seconds)
            if not pd.isna(avg_station_time_seconds):
                sum_of_avg_station_times_per_percentile[percentile_key_name] += avg_station_time_seconds
        
        pacing_table_data_list_of_dicts.append(station_pacing_row)

    # Row for Sum of Average Station Times
    sum_avg_station_times_row = {'Station': 'SUM OF AVG STATION TIMES'}
    for p_key in sum_of_avg_station_times_per_percentile.keys():
        sum_avg_station_times_row[p_key] = rl_data.format_time_mm_ss(sum_of_avg_station_times_per_percentile[p_key])
    pacing_table_data_list_of_dicts.append(sum_avg_station_times_row)

    # Row for Actual Average Net Time of the Cohort (for comparison)
    # This is more complex as the cohort changes for each percentile
    # Instead, let's use the quantile Net Time of the df_to_use_for_cohorts_and_percentiles
    actual_net_time_quantiles_row = {'Station': 'TARGET NET TIME (Quantile)'}
    for p_val in target_percentiles:
        percentile_key_name = f'Top {int(p_val*100)}%'
        target_net_time_for_percentile = df_to_use_for_cohorts_and_percentiles['Net Time'].quantile(p_val)
        actual_net_time_quantiles_row[percentile_key_name] = rl_data.format_time_mm_ss(target_net_time_for_percentile)
    pacing_table_data_list_of_dicts.append(actual_net_time_quantiles_row)
    
    runtimeVars['pacingTable'] = pacing_table_data_list_of_dicts
    session['runtime'] = runtimeVars
    
    if pacing_table_data_list_of_dicts:
        # Create DataFrame using the first row (header_dict) as keys for columns
        pacing_df_for_csv = pd.DataFrame(pacing_table_data_list_of_dicts[1:])
        pacing_df_for_csv.columns = list(pacing_table_data_list_of_dicts[0].values())
        
        try:
            pacing_df_for_csv.to_csv(filepath, index=False)
            print(f"Saved pacing table to {filepath}")
        except Exception as e:
            print(f"Error saving pacing table to CSV: {e}")
    else:
        print("No pacing table data generated to save.")

    return pacing_table_data_list_of_dicts

#############################
# Start of redline visuation method
# competitorDetails will be search details of one competitor

#############################
def redline_vis_generate(competitorDetails, io_stringHtml, io_pngList, io_pngStrings):

    logger = rl_data.get_logger()

    #need to figure out why this needed.
    runtimeVars = session.get('runtime', {})
    config = session.get('config', {})
    #############################
    # Reading the file
    #############################

    # if competitor Analysis true.
    if(config['competitorAnalysis'] == True):
        #then a single competitor in a single file has already been selected
        #print("competitorDetails",competitorDetails,runtimeVars['competitorRaceNo'])

        for element in rl_data.EVENT_DATA_LIST:
            if (element[0] == competitorDetails['event']):
                runtimeVars['eventDataList'] = element
                break

        #only want one file if competitor Analysis
        thisFileList = [runtimeVars['eventDataList']]

    # doing general analysis of all files.
    elif (competitorDetails == None):

        #configure the complete file list for the next loop
        thisFileList = rl_data.EVENT_DATA_LIST

    else:
        #then a general analysis of one event has been selected
        details = competitorDetails

        for element in rl_data.EVENT_DATA_LIST:
            if (element[0] == details['event']):
                runtimeVars['eventDataList'] = element
                break

        #only want one file for this output
        thisFileList = [runtimeVars['eventDataList']]

    #Loop through each file, 
    for runtimeVars['eventDataList'] in thisFileList:

        #configure for 2023 format or 2024 format
        if (runtimeVars['eventDataList'][2]=='2023'):
            runtimeVars['EventList'] = rl_data.EVENTLIST23
            runtimeVars['EventListStart'] = rl_data.EVENTLISTSTART23

        else:
            runtimeVars['EventList'] = rl_data.EVENTLIST24
            runtimeVars['EventListStart'] = rl_data.EVENTLISTSTART24


        #reset PNG list
        del (runtimeVars['pngList'])[:]
        del (runtimeVars['pngStrings'])[:]

        dataOutputThisLoop=False
        runtimeVars['stringPdf'] = ""

        indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(runtimeVars['eventDataList'][0] + '.csv')

        #print("eventDataList[0]",runtimeVars['eventDataList'][0])

        #read in the data.
        df = pd.read_csv(indatafile)

        tidyTheData(df=df, filename=indatafile)
        
        # if competitor Analysis enabled.
        if(config['competitorAnalysis'] == True):

            runtimeVars['competitorName']=competitorDetails.get('competitor')
            runtimeVars['competitorRaceNo']=competitorDetails.get('race_no')

            #print(f"redline_vis_generate {runtimeVars['competitorName']} {runtimeVars['competitorRaceNo']}")

            competitorIndex = competitorDataOutput(df=df)

            #At least one match found
            if (competitorIndex != -1):

                #Outpuy the tidy1 data to csv
                if (config['csvDurationOut']): 
                    
                    outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + runtimeVars['eventDataList'][0] + '.csv')

                    # check if file exists
                    if (os.path.isfile(outdatafile) == False):
                        df.to_csv(outdatafile,index=False)

                #show the competitor plots.
                if(config['showPie']): ShowPieChartAverage(df=df,competitorIndex=competitorIndex )
                if(config['showBar']): ShowBarChartEvent(df=df,competitorIndex=competitorIndex)
                if(config['showViolin']): ShowViolinChartEvent(df=df,competitorIndex=competitorIndex)
                if(config['showRadar']): ShowRadar(df=df,competitorIndex=competitorIndex )
                if(config['showGroupBar']): ShowGroupBarChart(df=df,competitorIndex=competitorIndex )
                if(config['showCumulTime']): ShowCumulativeTimeComparison(df=df,competitorIndex=competitorIndex)
                if(config['showTimeDiff']): ShowStationTimeDifferenceChart(df=df,competitorIndex=competitorIndex)
                if(config['showCorr']): ShowCorrInfo(df=df,competitorIndex=competitorIndex )

                dataOutputThisLoop=True

        else:

            #Outpuy the tidy data to csv
            if (config['csvDurationOut']):
                
                outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + runtimeVars['eventDataList'][0] + '.csv')

                # check if file exists
                if (os.path.isfile(outdatafile) == False):
                    df.to_csv(outdatafile, index=False)

            #show the event plots.
            if(config['showHist']): ShowHistAgeCat(df=df)
            if(config['showPie']): ShowPieChartAverage(df=df)
            if(config['showBar']): ShowBarChartEvent(df=df)
            if(config['showViolin']): ShowViolinChartEvent(df=df)
            if(config['showRadar']): ShowRadar(df=df)
            if(config['showCatBar']): ShowCatBarCharts(df)
            if(config['showCorr']): ShowCorrInfo(df=df)
            if(config['showCutOffBar']): ShowBarChartCutOffEvent(df=df)
            if(config['createPacingTable']): CreatePacingTable(df)

            

            dataOutputThisLoop=True

        #if wanna output data this loop
        if (dataOutputThisLoop==True):

            #Outpuy the tidy2 data frame to csv
            if (config['csvDfOut']): 
                tidyTheData2(df=df)
                outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('df' + runtimeVars['eventDataList'][0] + '.csv')
                
                # check if file exists
                if (os.path.isfile(outdatafile) == False):
                    df.to_csv(outdatafile, index=False)

            #creates a pdf of the PNGs processed here for each event
            if (config['createPdf']):

                if(config['competitorAnalysis']==True and competitorIndex != -1):
                    filepath = Path(rl_data.PDF_COMP_DIR) /  Path(runtimeVars['eventDataList'][0] + runtimeVars['competitorName'] + '.pdf')
                else:
                    filepath = Path(rl_data.PDF_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] +  '.pdf')

                # check if file exists
                if (os.path.isfile(filepath) == False):            
                    doc = pymupdf.open()  # PDF with the text pictures

                    #first output text (Can work on format)
                    rect_x1 = 50
                    rect_y1 = 50
                    rect_x2 = 500  # trial
                    rect_y2 = 800 # error
                    rect = (rect_x1, rect_y1, rect_x2, rect_y2)

                    # if competitor Analysis enabled.
                    if(config['competitorAnalysis'] == True):
                        page = doc.new_page()
                        rc = page.insert_htmlbox(rect, runtimeVars['stringPdf'])


                    for i, f in enumerate(runtimeVars['pngList']):
                        img = pymupdf.open(f)  # open pic as document
                        rect = img[0].rect  # pic dimension
                        pdfbytes = img.convert_to_pdf()  # make a PDF stream
                        img.close()  # no longer needed
                        imgPDF = pymupdf.open("pdf", pdfbytes)  # open stream as PDF
                        page = doc.new_page(width = rect.width,  # new page with ...
                                        height = rect.height)  # pic dimension
                        page.show_pdf_page(rect, imgPDF, 0)  # image fills the page
                        
                    doc.save(filepath) 

            if (config['pltPngOut']):
                #update output variable
                io_stringHtml = runtimeVars['stringPdf']
                io_pngList = list(runtimeVars['pngList'])
                io_pngStrings = runtimeVars['pngStrings']


    #clean up the session runtime and config
    session.pop('runtime', None)
    session.pop('config', None)

    #just backup should never be called
    return io_stringHtml, io_pngList, io_pngStrings       

#
# functions below this line are called by external files.

def redline_vis_competitor_html(competitorDetails, io_stringHtml, io_pngList, io_pngStrings):
    
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_competitor_html {competitorDetails}")
    
    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

     # session configuration variable
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : False,
        "csvDurationOut" : False,
        "pltPngOut" : True,
        "createPdf" : False,
        "competitorAnalysis" : True,
        #generic & Competitor.
        "showPie" : True,
        "showBar" : True,
        "showViolin" : True,
        "showRadar" : True,
        "showCorr" : True,

        #generic only
        "showCutOffBar" : False,
        "showHist" : False,
        "showHeat" : False,
        "showCatBar": False, 
        "createPacingTable": False,  

        #competitor only
        "showGroupBar"  : True, 
        "showCumulTime" : True,
        'showTimeDiff' :  True,   
    }

    # Store config in session
    session['config'] = config

    return redline_vis_generate(competitorDetails, io_stringHtml, io_pngList, io_pngStrings)

def redline_vis_competitor_pdf(competitorDetails, io_stringHtml, io_pngList, io_pngStrings):
    
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_competitor_pdf {competitorDetails}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

    # session configuration variable
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : False,
        "csvDurationOut" : False,
        "pltPngOut" : True,
        "createPdf" : True,
        "competitorAnalysis" : True,
        #generic & Competitor.
        "showPie" : True,
        "showBar" : True,
        "showViolin" : True,
        "showRadar" : True,
        "showCorr" : True,

        #generic only
        "showCutOffBar" : False,
        "showHist" : False,
        "showHeat" : False,
        "showCatBar": False, 
        "createPacingTable": False, 

        #competitor only
        "showGroupBar"  : True, 
        "showCumulTime" : True,
        'showTimeDiff' :  True,
    }

    # Store config in session
    session['config'] = config

    return redline_vis_generate(competitorDetails, io_stringHtml, io_pngList, io_pngStrings)

# used when regenerating all generic output for all events.
def redline_vis_generic():

    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

     # session configuration variable
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : False,
        "csvDurationOut" : True,
        "pltPngOut" : True,
        "createPdf" : True,
        "competitorAnalysis" : False,
        #generic & Competitor.
        "showPie" : True,
        "showBar" : True,
        "showViolin" : True,
        "showRadar" : True,
        "showCorr" : True,

        #generic only
        "showCutOffBar" : True,
        "showHist" : True,
        "showHeat" : True,
        "showCatBar": True,  
        "createPacingTable": True,

        #competitor only
        "showGroupBar"  : False, 
        "showCumulTime" : False,
        'showTimeDiff' :  False,
    }

    # Store config in session
    session['config'] = config

    #local variables
    local_htmlString = " "
    local_pngList = []
    local_pngStrings = []

    #competitor details set to False
    return redline_vis_generate(None, local_htmlString, local_pngList,  local_pngStrings)


# used when generating generic pdf (if not already generated)
def redline_vis_generic_eventpdf(details, io_stringHtml, io_pngList, io_pngStrings):
 
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic_eventpdf {details}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

    # session configuration variable
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : False,
        "csvDurationOut" : False,
        "pltPngOut" : True,
        "createPdf" : True,
        "competitorAnalysis" : False,
        #generic & Competitor.
        "showPie" : True,
        "showBar" : True,
        "showViolin" : True,
        "showRadar" : True,
        "showCorr" : True,

        #generic only
        "showCutOffBar" : True,
        "showHist" : True,
        "showHeat" : True,
        "showCatBar": True,  
        "createPacingTable": True,

        #competitor only
        "showGroupBar"  : False, 
        "showCumulTime" : False,
        'showTimeDiff' :  False,
    }

    # Store config in session
    session['config'] = config

    #competitor details set to False
    return redline_vis_generate(details, io_stringHtml, io_pngList, io_pngStrings)

# used when generating generic event html (and generating string pdf and displaying pngs)
def redline_vis_generic_eventhtml(details, io_stringHtml, io_pngList, io_pngStrings):

    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic_eventhtml {details}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

    # session configuration variable will control output
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : False,
        "csvDurationOut" : True,
        "pltPngOut" : True,
        "createPdf" : False,
        "competitorAnalysis" : False,

        #generic & Competitor.
        "showPie" : True,
        "showBar" : True,
        "showViolin" : True,
        "showRadar" : True,
        "showCorr" : True,

        #generic only
        "showCutOffBar" : True,
        "showHist" : True,
        "showHeat" : True,
        "showCatBar": True, 
        "createPacingTable": True, 

        #competitor only
        "showGroupBar"  : False, 
        "showCumulTime" : False,
        'showTimeDiff' :  False,
    }

    # Store session config dictionary
    session['config'] = config

    #competitor details set to False
    return redline_vis_generate(details, io_stringHtml, io_pngList, io_pngStrings)


def redline_vis_developer():

    logger = rl_data.get_logger()
    logger.info(f"redline_vis_developer")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
        "pngStrings": [],
        "stringPdf": " ",
        "EventList": [],
        "EventListStart": [],
        "eventDataList": [],
        "competitorName": " ",
        "competitorRaceNo": " "
    }
   
    session['runtime'] = runtime

     # session configuration variable
    config = {
        "pltShow" : False,
        "allScatter" : True,
        "csvDfOut" : True,
        "csvDurationOut" :     True,
        "pltPngOut" :          True,
        "createPdf" : False,
        
        "competitorAnalysis" : False,

        #generic & Competitor.
        "showPie" : True,
        "showBar" : False,
        "showViolin" : False,
        "showRadar" : False,
        "showCorr" : False,

        #generic only
        "showCutOffBar" : False,
        "showHist" : False,
        "showHeat" : False,
        "showCatBar": False, 
        "createPacingTable": True,

        #competitor only
        "showGroupBar"  : False, 
        "showCumulTime" : False,
        'showTimeDiff' : False,
    }

    # Store config in session
    session['config'] = config

    #local variables
    local_htmlString = " "
    local_pngList = []
    local_pngStrings = []

    #details = {'competitor': "STEPHANIE STEPHEN",  'race_no': "330", 'event': "WomensSinglesCompetitive2024"}

    #details = { 'competitor': 'STEPHEN ANTHONY CLEARY', 'race_no': '425', 'event': 'MensSinglesCompetitive2024'}

    #details = {'competitor': 'DENNIS OH', 'race_no': '1387', 'event': 'MensDoubles2024'}

    #details = {'competitor': 'DENNIS OH', 'race_no': '1387', 'event': 'MensDoubles2024'}

    #details =  {'competitor': 'JAMIE BARNETT', 'race_no': 'G1759', 'event': 'MensSinglesOpen2024'}
    details =  {'competitor': 'ANGIE LEK', 'race_no': '95', 'event': 'WomensSinglesOpen2024'}

    #competitor details set to False
    return redline_vis_generate(details, local_htmlString, local_pngList,  local_pngStrings)