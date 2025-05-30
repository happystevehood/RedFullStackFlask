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
        'is_placeholder_ready': True 
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
    },
    # --- HTML Outputs (Main Table for Competitor) ---
    {
        'id': 'html_info_comp',
        'name': 'Competitor info Table',
        'function_name': 'GenerateCompInfoTable',
        'is_competitor_specific': True,
        'filename_template': '{COMPETITOR_NAME_SLUG}_report.html', 
        'output_dir_const': 'PDF_COMP_DIR',
        'output_type': 'html_table', 
        'requires_category_data': False,
        'generates_multiple_files': False,
        'html_string_template': None, # Rendered by Jinja2
        'is_placeholder_ready': False 
    },       
    # --- PDF Outputs ---
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
        'html_string_template': "<p><a href=\"{FILE_URL}\" download>Download Your Personalized Report (PDF)</a>, {COMPETITOR_NAME}.</p>",
        'is_placeholder_ready': False, #Not needed as accessed separately
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
        'html_string_template': "<p><b>Overall Station Time Breakdown:</b> This pie chart shows the average percentage of total race time spent on each station by all participants.</p>",
        'is_placeholder_ready': True 
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
        'html_string_template': "<p><b>Station Time Distribution:</b> Stacked bars showing time percentiles for each station. The top of each colored segment represents the time achieved by that percentile of athletes (e.g., top of blue is fastest 5%).</p>",
        'is_placeholder_ready': True
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
        'html_string_template': "<p><b>Station Time Density (Violin Plot):</b> Shows how finisher times are spread out for each station. Wider parts mean more athletes finished around that time.</p>",
        'is_placeholder_ready': True
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
        'html_string_template': "<p><b>Median Performance Radar:</b> Spiderweb chart showing the median (50th percentile) time for each station. Closer to center = faster median time.</p>",
        'is_placeholder_ready': True
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
        'html_string_template': "<p><b>Station Correlation with Net Time:</b> Bar chart showing how strongly performance on each station is linked to the overall finish time. Higher bar = stronger link.</p>",
        'is_placeholder_ready': True
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
        'html_string_template': "<p><b>Cut-Off Analysis:</b> Bar chart showing the number or percentage of participants who exceeded the 7-minute time cap per station (for '24 events).</p>",
        'is_placeholder_ready': True 
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
        'html_string_template': "<p><b>Overall Net Time Distribution:</b> Histogram showing the distribution of final finish times, often broken down by age category.</p>",
        'is_placeholder_ready': False  #as dont know at time of writing if event has mutliple age categories 
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
        'html_string_template': "<p><b>Average Station Time by Category:</b> Compares the average time spent on each station across different age categories.</p>",
        'is_placeholder_ready': True 
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
        'html_string_template': "<p><b>Inter-Station Correlation Heatmap:</b> Shows how performance on different stations correlates with each other. Darker colors indicate stronger relationships.</p>",
        'is_placeholder_ready': True 
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
        'html_string_template': "<p><b>Your Station Time Breakdown:</b> Pie chart showing the percentage of your total race time spent on each station.</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Your Performance vs. Time Percentiles:</b> Stacked bars show time percentiles for each station, with your time highlighted.</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Your Time vs. Station Distribution:</b> Violin plots show how all finisher times are spread for each station, with your time marked.</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Your Performance Percentile Radar:</b> Spiderweb chart showing your percentile rank for each station compared to the field. Further from center = better rank percentile.</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Your Station Times vs. Similar Finishers:</b> Compares your time on each station (blue) against the average time of athletes who finished with a similar overall net time (red).</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Your Cumulative Time vs. Similar Finishers:</b> Line graph showing your cumulative time progression through the race compared to the average of similar finishers.</p>",
        'is_placeholder_ready': False
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
        'html_string_template': "<p><b>Station Time Difference vs. Similar Finishers:</b> Bar chart showing seconds you gained (green/below line) or lost (red/above line) on each station compared to the average of similar finishers.</p>",
        'is_placeholder_ready': False
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
        'num_files_generated_key': 'EventList', 
        'html_string_template': "<p><b>Station vs. Overall Time Scatter Plots:</b> Shows the relationship between time spent on each station and the final net time for all participants.</p>",
        'is_placeholder_ready': True # Each image generated individually
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
        'num_files_generated_key': 'EventList',
        'html_string_template': "<p><b>Your Performance on Scatter Plots:</b> Shows your position on the Station vs. Overall Time scatter plots for each station.</p>",
        'is_placeholder_ready': False # Each image generated individually
    }
]
