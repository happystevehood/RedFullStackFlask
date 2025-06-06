import rl.rl_data as rl_data # Assuming this is where your directory constants are

OUTPUT_CONFIGS = [
    # --- CSV Outputs ---
    {
        'id': 'duration_csv_generic',
        'name': 'Download Full Event Data',
        'function_name': 'CreateDfCsv', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_FullData.csv',
        'output_dir_const': 'CSV_GENERIC_DIR',
        'output_type': 'csv_download', # For linking as a download
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': "<p><a href=\"{FILE_URL}\" download>Download Full Event Data (CSV)</a></p>",
        'is_placeholder_ready': True,
        'load_priority': 10 # LOWEST PRIORITY 
    },
    {
        'id': 'pacing_table_csv_generic',
        'name': 'Download Pacing Table Data',
        'function_name': 'CreatePacingTable', # This function already saves to CSV
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_PacingTable.csv', # Filename is constructed inside CreatePacingTable
        'output_dir_const': 'CSV_GENERIC_DIR', # Used by CreatePacingTable
        'output_type': 'csv_download',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template'   : "<h5> Disclaimer </h5> <p> The above table is based on actual athlete times and is not an exact representation of a pacing chart.  \
                                    If you consider the Top 30% row, this was calculatd based on the average station time of the athletes within the Top 25%-35% Positions. \
                                    e.g. Upon studying the table you may see there are times in the Top 40% column which are faster than 30% column counterpart.  \
                                    This counter intutitve analysis is just a quirk of the data.  </p> \
                                    <br><p> If you have any comments are suggestions, you can do so via the <a href='/feedback' target='_blank' >Feedback form</a> form tab <p>",
        'is_placeholder_ready': True, #Not needed as accessed separately
        'load_priority': 5 #  PRIORITY 
    },
    # --- HTML Outputs (Main Table for Competitor) ---
    {
        'id': 'html_info_comp',
        'name': 'Race Summary',
        'function_name': 'GenerateCompInfoTable',
        'is_competitor_specific': True,
        'filename_template': '{COMPETITOR_NAME_SLUG}_report.html', 
        'output_dir_const': 'PDF_COMP_DIR',
        'output_type': 'html_table', 
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': None, # Rendered by Jinja2
        'is_placeholder_ready': False, 
        'load_priority': 1 # LOWEST PRIORITY 
    }, 
    {
        'id': 'html_note_comp',
        'name': 'Complete Event Information',
        'function_name': 'NoFunctionHere',
        'is_competitor_specific': True,
        'filename_template': '{COMPETITOR_NAME_SLUG}_NO_FILE_PLEASE.html', 
        'output_dir_const': 'PDF_COMP_DIR',
        'output_type': 'html_string', 
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': "<p>The Full Event visualisations for the <strong>{EVENT_DESCRIPTION}</strong> can be accessed <a href='/display?eventname={EVENT_LINK}'  target='_blank'> here</a>.</p>",
        'is_placeholder_ready': True, 
        'load_priority': 1 # LOWEST PRIORITY 
    },          
    # --- PNG Chart Outputs (Generic) ---
    {
        'id': 'pie_generic',
        'name': 'Overall Station Time Breakdown',
        'function_name': 'CreatePieChartAverage', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_Pie_Generic.png',
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Pie Chart:</b> This chart shows which stations, on average, took up the largest portions of an athlete's total race time. "
                                 "Stations with bigger slices were more time-consuming for the average competitor. "
                                 "From a data science perspective, this helps identify 'time sinks' in the event. "
                                 "Focusing your training on improving efficiency and endurance for these high-percentage stations could lead to significant overall time reductions. "
                                 "Compare these general trends to your personal performance to see where your time allocation differs.</p>"),
        'is_placeholder_ready': True, 
        'load_priority': 1 # Highest PRIORITY 
    },
    {
        'id': 'bar_stacked_dist_generic', # Was showBar_generic
        'name': 'Station Time Distribution (Stacked Bar)',
        'function_name': 'CreateBarChartEvent', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_Bar_Distribution_Generic.png',
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Stacked Bar Chart:</b> Each bar represents a station, and the coloured segments show the range of times achieved by different performance percentiles on that station. "
                                 "The purple segment is the range of times for the fastest 10% of athletes, while the grey '70-90%' segment is the time for slower athletes. "
                                 "Data science insight: A large spread between the purple segments and the red/grey segments on a station indicates high variability and thus a big opportunity. "
                                 "Improving on these 'high-spread' stations can yield greater time savings and rank improvements compared to stations where everyone finishes closer together. Use this to pinpoint where focused effort can make you more competitive.</p>"),        
        'is_placeholder_ready': True,
        'load_priority': 2 #  PRIORITY
    },
    {
        'id': 'violin_generic',
        'name': 'Station Time Distribution (Violin)',
        'function_name': 'CreateViolinChartEvent',
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_Violin_Generic.png',
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Violin Plot:</b> Each 'violin' shows the density of finish times for a station – wider parts mean more athletes finished around that specific time. "
                                 "The dashed black line is the median, and the thicker black bar shows the interquartile range (middle 50% of athletes). "
                                 "From a data perspective, long, thin 'tails' suggest some athletes took much longer, indicating potential bottlenecks or areas where significant time can be lost. "
                                 "Stations with very wide violins had a broad range of performances, making them key differentiators in the race. Focus on consistency and improving your time on stations where you might be in the wider or tail sections.</p>"),
        'is_placeholder_ready': True,
        'load_priority': 3 #  PRIORITY
    },
    {
        'id': 'radar_median_generic', # Was createRadar_generic
        'name': 'Median Performance Radar',
        'function_name': 'CreateRadar', # Or ShowNew for generic radar
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_Radar_Median_Generic.png',
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Median Radar Chart:</b> This spiderweb shows the median (50th percentile) time for each station; points closer to the center represent faster median times. "
                                 "This gives a 'performance fingerprint' of the average athlete in this event. "
                                 "Data insight: Look for stations where the median point is further from the center – these were generally slower for the average competitor. "
                                 "If this shape differs significantly from your own radar plot (see competitor version), it highlights your relative strengths and weaknesses. "
                                 "Training focus could be on stations where the general field is slower, offering a chance to gain an edge, or on your personal slower-than-median stations.</p>"),
        'is_placeholder_ready': True,
        'load_priority': 4 #  PRIORITY
    },
    {
        'id': 'histogram_nettime_generic', # Was showHist
        'name': 'Overall Net Time Distribution',
        'function_name': 'CreateHistAgeCat', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_NetTimeHist_Generic.png', # Original filename had STATION_NAME_HERE, but CreateHistAgeCat is likely for Net Time
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': True, # This function specifically uses 'Category'
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Net Time Histogram:</b> This chart displays the distribution of overall finish times for all participants, often broken down by age category. "
                                 "Each bar represents a range of finish times, and its height shows how many athletes finished within that range. "
                                 "Data insight: Look at the spread and peaks for your category to understand typical finishing times and where the bulk of competitors land. "
                                 "This helps you set realistic goals and see how your target time compares to the general field. "
                                 "A wide spread indicates diverse performance levels within that category.</p>"),
        'is_placeholder_ready': False,  #as dont know at time of writing if event has mutliple age categories,
        'load_priority': 5 #  PRIORITY
    },
    {
        'id': 'catbar_avgtime_generic', # Was showCatBar
        'name': 'Average Station Time by Category',
        'function_name': 'CreateCatBarCharts', # The grouped bar chart we worked on
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_AvgStationTime_ByCategory.png', # Original filename had STATION_NAME_HERE
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': True,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Average Station Times by Category:</b> This grouped bar chart compares the average time taken for each station across different age categories. "
                                 "For each station, you'll see bars representing each category side-by-side. "
                                 "Data science insight: This helps you benchmark against your specific age group. "
                                 "Identify stations where your age category is generally faster or slower, and see how average performance shifts with age. "
                                 "This can inform if your station goals are aggressive or conservative relative to your peers.</p>"),
        'is_placeholder_ready': True,
        'load_priority': 6 #  PRIORITY 
    },
    {
        'id': 'pacing_chart_png_generic', # New ID for the PNG
        'name': 'Station Pacing Guide Chart',
        'function_name': 'CreatePacingPng', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_PacingChart.png', # Output PNG filename
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Pacing Chart:</b> Each line represents a station. "
                                "Follow a line to see how the average time for that station changes based on the overall finish percentile (e.g., ~10%, ~20%). "
                                "Each datapoint is calculated using average times per station of athletes who finished within +-5% range. "
                                " i.e. 50% values are average time (per statation) for athletes with total time within 45%-55% range. And Yes the lines criss-cross which is confusing but its reallife."
                                "A Table version of this graph is also available for easier reading of the numbers on the previous screen </p>"),
        'is_placeholder_ready': False, 
        'load_priority': 7 
    },
    {
        'id': 'correlation_bar_generic', # Was showBarCorr
        'name': 'Station Correlation with Net Time',
        'function_name': 'CreateCorrBar', # This function should be adapted to only output the bar chart part
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_CorrelationBar_Generic.png',
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Correlation Bar Chart:</b> This chart reveals how strongly each station's completion time is linked to the overall Net Time. A higher bar (correlation closer to 1.0) means that doing well on that station is more strongly associated with a better overall finish. "
                                 "Data science insight: Prioritize training for stations with high correlation values. "
                                 "Improving performance on these key stations is statistically more likely to impact your final rank positively. "
                                 "However, remember correlation isn't causation; a balanced approach is still vital, but these stations are often major differentiators.</p>"),
        'is_placeholder_ready': True,
        'load_priority': 9 #  PRIORITY
    },
    {
        'id': 'heatmap_correlation_generic', # Was showHeat
        'name': 'Inter-Station Correlation Heatmap',
        'function_name': 'CreateCorrHeat', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_CorrelationHeatmap_Generic.png', # Original filename had STATION_NAME_HERE
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Correlation Heatmap:</b> This grid uses colours to show how strongly performance on one station is related to performance on another, and to the Net Time. "
                                 "Darker shades (often specified in a legend, e.g., dark green or dark red for strong positive correlation) indicate a stronger relationship. "
                                 "Data science insight: Identify clusters of stations that are highly correlated; being good at one often means being good at others in that cluster (e.g., all erg machines). "
                                 "This can help you understand if your training for one station might have positive carry-over effects to others, or which station types are most predictive of overall success (correlation with Net Time).</p>"),
        'is_placeholder_ready': True,
        'load_priority': 11 #  PRIORITY 
    },
    {
        'id': 'cutoff_bar_generic', 
        'name': 'Participants Missing Cut-Offs',
        'function_name': 'CreateBarChartCutOffEvent', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_CutOffBar_Generic.png', # Original filename had STATION_NAME_HERE, but function usually makes one summary
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting the Cut-Off Chart:</b> This shows the percentage of participants who exceeded the 7-minute time cap for each station in the '24 events (resulting in a 7-minute penalty for that station). "
                                 "Stations with higher bars were more likely to cause athletes to hit this limit. "
                                 "For '25, while the 7-min cap is gone, an incomplete station incurs a 10-min penalty. "
                                 "This '24 data highlights historically challenging stations where ensuring completion and building a buffer should be a training priority to avoid devastating penalties in '25.</p>"),
        'is_placeholder_ready': True,
        'load_priority': 12 #  PRIORITY
    },
    
    # --- PNG Chart Outputs (Competitor Specific) ---
    {
        'id': 'pie_comp',
        'name': 'Your Station Time Breakdown',  
        'function_name': 'CreatePieChartAverage',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_Pie.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Pie Chart:</b> This chart breaks down <i>your</i> total race time, showing the percentage you spent on each station. "
                                 "Larger slices mean you spent more time there. "
                                 "Data science insight: Compare this to the generic pie chart for this event. "
                                 "Are you spending disproportionately more time on certain stations compared to the average athlete? "
                                 "This highlights areas where you might be losing time or where your strengths allow you to be quicker, guiding your training focus.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 1 #  PRIORITY
    },
    {
        'id': 'bar_stacked_dist_comp', # Was showBar_comp
        'name': 'Your Performance vs. Time Percentiles',
        'function_name': 'CreateBarChartEvent',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_Bar_Distribution.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Stacked Bar Chart:</b> This shows station time percentiles (like the generic version), but with <i>your</i> specific time highlighted by a distinct marker (e.g., cyan cross) on each station's bar. "
                                 "You can immediately see which performance band your time falls into for every station. "
                                 "Data science insight: Identify stations where your marker is in the slower colour bands (e.g., red, grey) – these are clear areas for improvement. "
                                 "Conversely, stations where your marker is in the faster bands (blue, purple) are your strengths. This provides a granular view of your competitiveness per station.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 2 #  PRIORITY
    },
    {
        'id': 'violin_comp',
        'name': 'Your Time vs. Station Distribution',
        'function_name': 'CreateViolinChartEvent',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_Violin.png', # Corrected Vionlin to Violin
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Violin Plot:</b> This displays the overall distribution of times for each station, with <i>your</i> performance marked by a distinct symbol (e.g., orange diamond). "
                                 "The width of the violin shows where most athletes' times cluster. "
                                 "Data science insight: See where your marker falls within each violin. Are you in the dense middle, or towards one of the tails? "
                                 "This helps you understand if your station times are typical, exceptionally fast, or slower than most. "
                                 "It provides context beyond just your raw time, showing your standing relative to the entire field's performance shape on that station.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 3 #  PRIORITY
    },
    {
        'id': 'radar_percentile_comp', # Was createRadar_comp
        'name': 'Your Performance Percentile Radar',
        'function_name': 'CreateRadar', # Or ShowNew for competitor radar
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_Radar_Percentile.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Radar Chart:</b> This spiderweb shows <i>your percentile rank</i> for each station (e.g., Top 42.1% means you were in the  fastest 42.1%% of competitors on that station). Points further from the center indicate a better percentile rank. "
                                 "It often includes a line for the median (50th percentile) for comparison. "
                                 "Data science insight: The 'shape' of your performance quickly reveals your strengths (points far out) and weaknesses (points closer to the center or inside the median line) across all stations. "
                                 "This holistic view is excellent for identifying patterns, like if you excel in strength but lag in cardio, to guide balanced training.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 4 #  PRIORITY
    },
    {
        'id': 'bar_sim_comp', # Was showBarSim
        'name': 'Your Station Times vs. Similar Finishers',
        'function_name': 'CreateGroupBarChart',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_BarSim.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Comparison Bar Chart:</b> This chart directly compares <i>your time</i> (e.g., blue bar) on each station against the <i>average time</i> (e.g., red bar) of athletes who had similar overall finish time to you (+/-5%). "
                                 "Data science insight: This is crucial for race strategy. "
                                 "If your bar is shorter (faster) on a station, you gained time against your peers there. If it's taller, you lost time. "
                                 "This helps identify which specific stations contributed most to your overall placing relative to those around you, highlighting where small improvements can make you leapfrog competitors.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 5 #  PRIORITY
    },
    {
        'id': 'cumul_sim_comp', # Was showCumulSim
        'name': 'Your Cumulative Time vs. Similar Finishers',
        'function_name': 'CreateCumulativeTimeComparison',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_CumulSim.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Cumulative Time Chart:</b> This line graph tracks <i>your cumulative time</i> throughout the race (e.g., blue line) against the average cumulative time of athletes who finished similarly (+/-5%) to you (e.g., red line). "
                                 "Data science insight: Watch where the lines diverge. If your line drops below the average, you're gaining time. If it goes above, you're losing time. "
                                 "The shaded areas highlight these differences. This helps identify critical phases of the race and at which stations you typically pull ahead or fall behind your direct competition, informing pacing strategies.</p>"),
        'is_placeholder_ready': False,
        'load_priority': 6 #  PRIORITY
    },
    {
        'id': 'diff_sim_comp', # Was showDiffSim
        'name': 'Your Station Time Difference vs. Similar Finishers',
        'function_name': 'CreateStationTimeDifferenceChart',
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_DiffSim.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': ("<p><b>Interpreting Your Station Difference Chart:</b> This bar chart shows the exact time difference in seconds between <i>your station time</i> and the average for similar finishers (+/-5%). "
                                 "Bars below zero (e.g., green) mean you were faster; bars above zero (e.g., red) mean you were slower. "
                                 "Data science insight: This quantifies exactly where you gain or lose time against your immediate peer group. "
                                 "Large green bars are your standout strengths. Large red bars are your most significant opportunities for improvement to better your rank among those with similar overall capabilities. Focus on turning those red bars green!</p>"),
        'is_placeholder_ready': False,
        'load_priority': 7 #  PRIORITY
    },

    # --- Scatter Plots (Needs to be called for each event, Generates 1 file) ---
   {
        'id': 'scatter_generic_collection', 
        'name': 'Generic Station vs. Net Time Scatter Plots',
        'function_name': 'ShowScatterPlot', 
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_{STATION_NAME_SLUG}_Scatter.png', 
        'output_dir_const': 'PNG_GENERIC_DIR',
        'output_type': 'png_collection', 
        'requires_category_data': False,
        'generates_multiple_files': True, 
        'num_files_generated_key': 'StationList',
        'html_string_template': ("<p><b>Interpreting Scatter Plots (Station Time vs. Overall Position):</b> Each dot is an athlete. The horizontal position is their time for this station, and the vertical position is their overall race rank (lower is better). "
                                 "A high correlation score (look at title of Chart), means that there is a strong positive relationship between the two variables. "),
        'is_placeholder_ready': True, # Each image generated individually
        'load_priority': 10 #  PRIORITY
    },
    {
        'id': 'scatter_comp_collection',
        'name': 'Your Performance on Scatter Plots',
        'function_name': 'ShowScatterPlot', # A new wrapper or modified ShowCorrInfo
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{STATION_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_Scatter.png',
        'output_dir_const': 'PNG_COMP_DIR',
        'output_type': 'png_collection',
        'requires_category_data': False,
        'generates_multiple_files': True,
        'num_files_generated_key': 'StationList',
        'html_string_template': ("<p><b>Interpreting Your Scatter Plot Position:</b> This shows where <i>your performance</i> (highlighted marker, e.g., cross) falls on the Station Time vs. Overall Rank scatter plot for each station. "
                                 "You can see your station time (horizontal) and your overall rank (vertical) relative to all other competitors. "),
        'is_placeholder_ready': False, # Each image generated individually
        'load_priority': 10 #  PRIORITY
    },
    # --- PDF Outputs --- LAST
    {
        'id': 'pdf_report_generic',
        'name': 'Generic Event PDF Report',
        'function_name': 'MakeFullPdfReport', #Non Standar parameters
        'is_competitor_specific': False,
        'filename_template': '{EVENT_NAME_SLUG}_FullReport.pdf',
        'output_dir_const': 'PDF_GENERIC_DIR',
        'output_type': 'pdf_download',
        'requires_category_data': False, # Depends on what's in PDF
        'generates_multiple_files': False, # The PDF itself is one file
        'html_string_template': "<p><a href=\"{FILE_URL}\" download>Download Full Event Report (PDF)</a> for {EVENT_NAME}.</p>",
        'is_placeholder_ready': True, 
        'load_priority': 99 # LOWEST PRIORITY - Always last
    },
    {
        'id': 'pdf_report_comp',
        'name': 'Personalized Competitor PDF Report',
        'function_name': 'MakeFullPdfReport', #Non Standar parameters
        'is_competitor_specific': True,
        'filename_template': '{EVENT_NAME_SLUG}_{COMPETITOR_NAME_SLUG}_PersonalReport.pdf',
        'output_dir_const': 'PDF_COMP_DIR', 
        'output_type': 'pdf_download',
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': "<div id=\"pdfDownloadContainer\" style=\"display: none;\"><p><a href=\"{FILE_URL}\" download>Download Your Personalized Report (PDF)</a>, {COMPETITOR_NAME}.</p></div>", 
        'is_placeholder_ready': False, #Not needed as accessed separately
        'load_priority': 99 # LOWEST PRIORITY - Always last 
    },
]
