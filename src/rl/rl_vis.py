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
 
#Boolean to decide if output warningsto terminal
OutputInfo=False


#############################
# Tidy the data/data frame
#############################
def tidyTheData(df, filename):

    logger = rl_data.get_logger()
    runtimeVars = session.get('runtime', {})

    #Clean a few uneeded columns first.
    if 'Fav' in df.columns:
        df.drop('Fav', axis=1, inplace = True)

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
                    #2023 does not have decimal places
                    if (runtimeVars['eventDataList'][2]=='2023'):
                        df.loc[x,event] = timedelta.total_seconds(datetime.strptime(df.loc[x,event],"%H:%M:%S") - datetime.strptime(df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] ,"%H:%M:%S"))
                    #2024 time has decimal places
                    else:
                        df.loc[x,event] = timedelta.total_seconds(datetime.strptime(df.loc[x,event],"%H:%M:%S.%f") - datetime.strptime(df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] ,"%H:%M:%S.%f"))

                    #if value less than 10 seconds, then somthing wrong, data not trust worthy so want to drop the row.
                    if df.loc[x,event] < 10.0:
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
                            #2023 does not have decimal places
                            if (runtimeVars['eventDataList'][2]=='2023'):
                                twoEventDuration = timedelta.total_seconds(datetime.strptime(dforig.loc[x,event],"%H:%M:%S") - datetime.strptime(dforig.loc[x,runtimeVars['EventListStart'][MyIndex-2]] ,"%H:%M:%S"))
                            #2024 time has decimal places
                            else:
                                twoEventDuration = timedelta.total_seconds(datetime.strptime(dforig.loc[x,event],"%H:%M:%S.%f") - datetime.strptime(dforig.loc[x,runtimeVars['EventListStart'][MyIndex-2]] ,"%H:%M:%S.%f"))

                            if (twoEventDuration < 60.0):
                                    if(OutputInfo == True): logger.debug(f"2 EventDurLow {filename} {x} {event} {twoEventDuration}")
                                    #drop the row
                                    df.drop(x, inplace = True)

                            df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] = (twoEventDuration * meanEventList[MyIndex-2] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])
                            df.loc[x,runtimeVars['EventListStart'][MyIndex]]  = (twoEventDuration * meanEventList[MyIndex-1] )/(meanEventList[MyIndex-2] + meanEventList[MyIndex-1])

                        except (ValueError, TypeError):
                                #This will catch the competitors where NET time is "DNF" etc....

                                #Set Time values to None
                                df.loc[x,runtimeVars['EventListStart'][MyIndex-1]] = float("nan")
                                df.loc[x,runtimeVars['EventListStart'][MyIndex]] = float("nan")

        MyIndex = MyIndex - 1

    # convert Net Time Column to float in seconds.
    for x in df.index:

        #if time format wrong, it causes excpetions.
        try:
            #2023 does not have decimal places
            if (runtimeVars['eventDataList'][2]=='2023'):
                df.loc[x,'Net Time'] =  timedelta.total_seconds(datetime.strptime(df.loc[x,'Net Time'],"%H:%M:%S") - datetime.strptime("00:00:00","%H:%M:%S"))
                df.loc[x,'Start']    =  timedelta.total_seconds(datetime.strptime(df.loc[x,'Start']   ,"%H:%M:%S") - datetime.strptime("00:00:00","%H:%M:%S"))
            else:
                df.loc[x,'Net Time'] =  timedelta.total_seconds(datetime.strptime(df.loc[x,'Net Time'],"%H:%M:%S.%f") - datetime.strptime("00:00:00.0","%H:%M:%S.%f"))
                df.loc[x,'Start']    =  timedelta.total_seconds(datetime.strptime(df.loc[x,'Start']   ,"%H:%M:%S.%f") - datetime.strptime("00:00:00.0","%H:%M:%S.%f"))

            #time Adjust format is the samve
            if ('Time Adj' in df.columns and pd.isna(df.loc[x, "Time Adj"]) == False):
                timeAdj = df.loc[x,"Time Adj"].replace("+", "")
                df.loc[x,'Time Adj'] = timedelta.total_seconds(datetime.strptime(timeAdj   ,"%H:%M:%S") - datetime.strptime("00:00:00","%H:%M:%S"))
            else:
                df.loc[x,'Time Adj'] = 0.0

            #if net time less than 6 minutes
            if ((df.loc[x,'Net Time']) < 360.0):
                #print data...
                if(OutputInfo == True): logger.debug(f"Removed Low NetTime {filename} {x} {df.loc[x,'Net Time']} {df.loc[x,'Pos']}")
                #drop the row
                df.drop(x, inplace = True)

            #Reset Calculated time for this index
            calculatedNetTime = 0.0

            #iterate the event list in reverse order
            for event in runtimeVars['EventListStart']:
                #add each event time.
                calculatedNetTime = calculatedNetTime + df.loc[x,event] 

            #Store the event time.
            df.loc[x,'Calc Time'] = calculatedNetTime    

            #if NetTime - Calculated time is less than 12 seconds
            #if (abs(df.loc[x,'Net Time'] - calculatedNetTime) > 12):
                                
                #print ('NetTime Mismatch ', df.loc[x,'Net Time'], calculatedNetTime, abs(df.loc[x,'Net Time'] - calculatedNetTime), x  )

        except (ValueError, TypeError):
                #This will catch the competitors where NET time is "DNF" etc....

                #Set Time values to None
                #df.loc[x,'Calc Time'] = float("nan")
                #df.loc[x,'Net Time'] = float("nan")

                #drop the row
                df.drop(x, inplace = True)

    #gonna create some rank data.

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
    #print('competitorDataOutput competitorName',competitorName, competitorRaceNo)
    
    #if relay 
    if 'Member1' in df.columns:
        nameMask = df['Name'].str.contains(runtimeVars['competitorName'], na=False) 
        mem1Mask = df['Member1'].str.contains(runtimeVars['competitorName'], na=False) 
        mem2Mask = df['Member2'].str.contains(runtimeVars['competitorName'], na=False)
        mem3Mask = df['Member3'].str.contains(runtimeVars['competitorName'], na=False)
        mem4Mask = df['Member4'].str.contains(runtimeVars['competitorName'], na=False)
        compMask = nameMask | mem1Mask | mem2Mask | mem3Mask | mem4Mask & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False)

    else:
        compMask = df['Name'].str.contains(runtimeVars['competitorName']) & df['Race No'].astype(str).str.contains(runtimeVars['competitorRaceNo'], na=False)

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
        runtimeVars['stringPdf'] += '<tr><td><strong>Position        </strong></td><td>' +  str(df.loc[compIndex, "Pos"]) + ' of '+ str(df["Gender"].value_counts()[df.loc[compIndex, "Gender"]]) + ' finishers.'+ "</td></tr>"

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

        runtimeVars['stringPdf'] += '</table><br><br>'

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

        #style added directly to HTML for security reasons.
        #styled_table = tableDF.style.set_table_styles()
        #    [{'selector': 'th',
        #    'props': [('background-color', '#f2f2f2'), ('padding', '8px'), ('text-align', 'left')]},
        #    {'selector': 'td',
        #    'props': [('padding', '8px'), ('border', '1px solid #ddd')]}]
        #).set_properties(**{
        #    'border-collapse': 'collapse',
        #    'font-family': 'sans-serif',
        #    'font-size': '14px'
        #})

        #forcibly remove the style attribute from string
        runtimeVars['stringPdf'] += re.sub( ' style=\"text-align: right;\"','',tableDF.to_html())
        runtimeVars['stringPdf'] += '<br><br>'

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
    
    if( config['showHeat'] ):

        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'CorrHeat' + '.png')

        #for PDF creation
        runtimeVars['pngList'].append(str(filepath)) 

        #check if file exists
        if (os.path.isfile(filepath) == False):
        
            plt.figure(figsize=(10, 10))
            heatmap = sns.heatmap(corr_matrix, vmin=-0, vmax=1, annot=True, cmap='BrBG')
            heatmap.set_title('Correlation Heatmap ' + runtimeVars['eventDataList'][1], fontdict={'fontsize':12}, pad=12);

            # Output/Show depending of global variable setting with pad inches
            if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
            if ( config['pltShow'] ):   plt.show()
            if ( config['pltPngOut'] or  config['pltShow']):   plt.close()


    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Corr' + '.png')
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

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

    if (config['allScatter'] == False):
        #Show scatter chart with higest correlation.
        ShowScatterPlot(df, corr_matrix.index[1], corr=corr_matrix.at[corr_matrix.index[1],'Net Time'],competitorIndex=competitorIndex)

        #Show scatter chart with lowest correlation.
        ShowScatterPlot(df, corr_matrix.index[-1], corr=corr_matrix.at[corr_matrix.index[-1],'Net Time'],competitorIndex=competitorIndex)

    else:
        for event in corr_matrix.index:
            #skip next time scatter plot
            if (event != 'Net Time'):
                #Show scatter Plot
                ShowScatterPlot(df, event, corr=corr_matrix.at[event,'Net Time'],competitorIndex=competitorIndex )

############################
# Histogram Age Categories
#############################

def ShowHistAgeCat(df):

    runtimeVars = session.get('runtime', {})

    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Hist' + '.png')
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

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

            #Competitive Dobules Mixed Relay Category 
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

def ShowBarChartEvent(df,competitorIndex=-1):

    maxEventList = []
    q1EventList = []
    medianEventList = []
    q3EventList = []
    q4EventList = []
    minEventList = []
    compList= []
    maxTime = 0.0

    runtimeVars = session.get('runtime', {})

    if (competitorIndex == -1):
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Bar' + '.png')
    else:
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(runtimeVars['eventDataList'][0] + runtimeVars['competitorName'] + 'Bar' + '.png')
    
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

    # check if file exists
    if (os.path.isfile(filepath) == False):    

        config = session.get('config', {})

        # get the median time for each event.
        for event in runtimeVars['EventList']:

            maxEventList.append(df[event].quantile(0.90))
            q1EventList.append(df[event].quantile(0.70))
            medianEventList.append(df[event].quantile(0.50))
            q3EventList.append(df[event].quantile(0.30))
            q4EventList.append(df[event].quantile(0.10))
            minEventList.append(df[event].min())

            if (competitorIndex != -1):
                compList.append(df.loc[competitorIndex,event])
                if (df[event].quantile(0.90) > maxTime):
                    maxTime = df[event].quantile(0.90)

        fig, ax = plt.subplots(figsize=(10, 10))

        plt.bar(runtimeVars['EventList'], maxEventList,       color='grey'   , label='70%-90%')
        plt.bar(runtimeVars['EventList'], q1EventList,        color='red'    , label='50%-70%')
        plt.bar(runtimeVars['EventList'], medianEventList,    color='orange' , label='30%-50%')
        plt.bar(runtimeVars['EventList'], q3EventList,        color='green'  , label='10%-30%')
        plt.bar(runtimeVars['EventList'], q4EventList,        color='purple'  , label='0%-10%')
        plt.bar(runtimeVars['EventList'], minEventList,       color='blue'   , label='fastest')

        if (competitorIndex != -1):
            plt.plot(compList, marker='_', markersize=40.0, markeredgewidth=2.0, color='navy', linewidth=0.0)

            #coorinates via trial an error.
            plt.text(4.0,maxTime*1.02,'____='+ df.loc[competitorIndex,'Name'] , fontsize = 10, color='blue')


        #keep the y axis showing multiples of 60
        plt.yticks(range(0,int(max(maxEventList))+30,60))
        plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)

        plt.tick_params(axis='x', labelrotation=90)
        plt.ylabel('Time in Seconds')

        if (competitorIndex == -1):
            plt.title(runtimeVars['eventDataList'][1] + ' Bar Station Breakdown')
        else:
            plt.title(runtimeVars['eventDataList'][1] + ' ' + df.loc[competitorIndex,'Name'] + ' Bar Stations')
    
        plt.legend() 

        # Output/Show depending of global variable setting with some padding
        if ( config['pltPngOut'] ): plt.savefig(filepath, bbox_inches='tight', pad_inches = 0.5)
        if ( config['pltShow'] ):   plt.show()
        if ( config['pltPngOut'] or  config['pltShow']):   plt.close()


#############################
# Violin chart Events
#############################

def ShowViolinChartEvent(df,competitorIndex=-1):

    runtimeVars = session.get('runtime', {})

    if (competitorIndex == -1):
        filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'Violin' + '.png')
    else:
        filepath = Path(rl_data.PNG_COMP_DIR) / Path(runtimeVars['eventDataList'][0] + runtimeVars['competitorName'] + 'Violin' + '.png')

    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

    # check if file exists  
    if (os.path.isfile(filepath) == False):

        config = session.get('config', {})

        compList= []

        # compile list of comeptitor times.
        if (competitorIndex != -1):
            for event in runtimeVars['EventList']:
                compList.append(df.loc[competitorIndex,event])

        #Draw Violin plot. 600 value used to exclude outliers, but should be chosen algorithmically.
        g=sns.violinplot(data=df[df[runtimeVars['EventList']]<600.0][runtimeVars['EventList']] , inner='box', cut=1)
        g.figure.set_size_inches(10,10)

        if (competitorIndex != -1):
            plt.plot(compList, marker='_', markersize=40.0, markeredgewidth=2.0, color='navy', linewidth=0.0)

            #coorinates via trial an error.
            plt.text(4.0,645,'____='+ df.loc[competitorIndex,'Name'], color='navy' , fontsize = 10)

        plt.yticks(range(0,660+30,60))
        plt.tick_params(axis='x', labelrotation=90)
        plt.ylabel('Time in Seconds')
        plt.grid(color ='grey', linestyle ='-.', linewidth = 0.5, alpha = 0.4)
        
        if (competitorIndex == -1):
            plt.title(runtimeVars['eventDataList'][1] + ' Violin Station Breakdown')
        else:
            plt.title(runtimeVars['eventDataList'][1] + ' ' + df.loc[competitorIndex,'Name'] + ' Violin Stations')
    
        # Output/Show depending of global variable setting with some padding
        if ( config['pltPngOut'] ): plt.savefig(filepath , bbox_inches='tight', pad_inches = 0.5)
        if ( config['pltShow'] ):   plt.show()
        if ( config['pltPngOut'] or  config['pltShow']):   plt.close()


#############################
# Bar chart Cut Off Events
#############################

def ShowBarChartCutOffEvent(df):

    runtimeVars = session.get('runtime', {})

    filepath = Path(rl_data.PNG_GENERIC_DIR) / Path(runtimeVars['eventDataList'][0] + 'CutOffBar' + '.png')
    #for PDF creation
    runtimeVars['pngList'].append(str(filepath))

    # check if file exists  
    if (os.path.isfile(filepath) == False):
        config = session.get('config', {})

        fig, ax = plt.subplots(figsize=(10, 10))

        #null list
        cutOffEventList = []
        MyIndex = 0

        for event in runtimeVars['EventList'][::]:
            #print ('Event CutOff %s %d %d %2.2f' % (event, EventCutOffCount[MyIndex], len(df.index), EventCutOffCount[MyIndex] / len(df.index)))

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
# Start of redline visuation method
# competitorDetails will be search details of one competitor

#############################
def redline_vis_generate(competitorDetails, io_stringHtml, io_pngList):

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
        #print("details",details)

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

        dataOutputThisLoop=False
        runtimeVars['stringPdf'] = ""

        indatafile = Path(rl_data.CSV_INPUT_DIR) / Path(runtimeVars['eventDataList'][0] + '.csv')

        #read in the data.
        df = pd.read_csv(indatafile)

        tidyTheData(df=df, filename=indatafile)
        
        # if competitor Analysis enabled.
        if(config['competitorAnalysis'] == True):

            runtimeVars['competitorName']=competitorDetails.get('competitor')
            runtimeVars['competitorRaceNo']=competitorDetails.get('race_no')

            competitorIndex = competitorDataOutput(df=df)

            #At least one match found
            if (competitorIndex != -1):

                #Outpuy the tidy1 data to csv
                if (config['csvDurationOut']): 
                    
                    outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + runtimeVars['eventDataList'][0] + '.csv')

                    # check if file exists
                    if (os.path.isfile(outdatafile) == False):
                        df.to_csv(outdatafile)

                #show the competitor plots.
                if(config['showHist']): ShowHistAgeCat(df=df)
                if(config['showViolin']): ShowViolinChartEvent(df=df,competitorIndex=competitorIndex)
                if(config['showCutOffBar']): ShowBarChartCutOffEvent(df=df)
                if(config['showBar']): ShowBarChartEvent(df=df,competitorIndex=competitorIndex)
                if(config['showPie']): ShowPieChartAverage(df=df)
                if(config['showPie']): ShowPieChartAverage(df=df,competitorIndex=competitorIndex )
                if(config['showCorr']): ShowCorrInfo(df=df,competitorIndex=competitorIndex )

                dataOutputThisLoop=True

        else:

            #Outpuy the tidy data to csv
            if (config['csvDurationOut']):
                
                outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + runtimeVars['eventDataList'][0] + '.csv')

                # check if file exists
                if (os.path.isfile(outdatafile) == False):
                    df.to_csv(outdatafile)

            #show the event plots.
            if(config['showHist']): ShowHistAgeCat(df=df)
            if(config['showViolin']): ShowViolinChartEvent(df=df)
            if(config['showCutOffBar']): ShowBarChartCutOffEvent(df=df)
            if(config['showBar']): ShowBarChartEvent(df=df)
            if(config['showPie']): ShowPieChartAverage(df=df)
            if(config['showCorr']): ShowCorrInfo(df=df)

            dataOutputThisLoop=True

        #if wanna output data this loop
        if (dataOutputThisLoop==True):

            #Outpuy the tidy2 data frame to csv
            if (config['csvDfOut']): 
                tidyTheData2(df=df)
                outdatafile = Path(rl_data.CSV_GENERIC_DIR) / Path('df' + runtimeVars['eventDataList'][0] + '.csv')
                
                # check if file exists
                if (os.path.isfile(outdatafile) == False):
                    df.to_csv(outdatafile)

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
            
    #just backup should never be called
    return io_stringHtml, io_pngList       

#
# functions below this line are called by external files.

def redline_vis_competitor_html(competitorDetails, io_stringHtml, io_pngList):
    
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_competitor_html {competitorDetails}")
    
    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
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
        "showBar" : True,
        "showViolin" : True,
        "showCutOffBar" : True,
        "showHist" : True,
        "showPie" : True,
        "showCorr" : True,
        "showHeat" : True
    }

    # Store config in session
    session['config'] = config

    return redline_vis_generate(competitorDetails, io_stringHtml, io_pngList)

def redline_vis_competitor_pdf(competitorDetails, io_stringHtml, io_pngList):
    
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_competitor_pdf {competitorDetails}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
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
        "showBar" : True,
        "showViolin" : True,
        "showCutOffBar" : True,
        "showHist" : True,
        "showPie" : True,
        "showCorr" : True,
        "showHeat" : True
    }

    # Store config in session
    session['config'] = config

    return redline_vis_generate(competitorDetails, io_stringHtml, io_pngList)

# used when regenerating all generic output for all events.
def redline_vis_generic(io_stringHtml, io_pngList):

    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
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
        "showBar" : True,
        "showViolin" : True,
        "showCutOffBar" : True,
        "showHist" : True,
        "showPie" : True,
        "showCorr" : True,
        "showHeat" : True
    }

    # Store config in session
    session['config'] = config

    #local variables
    local_htmlString = " "
    local_pngList = []

    #competitor details set to False
    return redline_vis_generate(None, local_htmlString, local_pngList)


# used when generating generic pdf (if not already generated)
def redline_vis_generic_eventpdf(details, io_stringHtml, io_pngList):
 
    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic_eventpdf {details}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0, 0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
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
        "showBar" : True,
        "showViolin" : True,
        "showCutOffBar" : True,
        "showHist" : True,
        "showPie" : True,
        "showCorr" : True,
        "showHeat" : True
    }

    # Store config in session
    session['config'] = config

    #competitor details set to False
    return redline_vis_generate(details, io_stringHtml, io_pngList)

# used when generating generic event html (and generating string pdf and displaying pngs)
def redline_vis_generic_eventhtml(details, io_stringHtml, io_pngList):

    logger = rl_data.get_logger()
    logger.info(f"redline_vis_generic_eventhtml {details}")

    # Value always initialised as below but will be updated in function
    runtime = {
        "EventCutOffCount": [0,0,0,0,0,0,0,0,0,0,0,0],  #Count number of partipants who reach 7 minutes per event. Corresponds to EventList Entries
        "pngList": [],
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
        "showBar" : True,
        "showViolin" : True,
        "showCutOffBar" : True,
        "showHist" : True,
        "showPie" : True,
        "showCorr" : True,
        "showHeat" : True
    }

    # Store session config dictionary
    session['config'] = config

    #competitor details set to False
    return redline_vis_generate(details, io_stringHtml, io_pngList)