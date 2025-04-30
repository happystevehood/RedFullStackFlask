from flask import Flask, request, jsonify, render_template, send_file, abort, session, redirect, url_for,  flash
from functools import wraps
from datetime import datetime

import pandas as pd

import os, csv, math, re
from pathlib import Path
import logging

# local inclusion.
from util.search import find_competitor
import util.data
from visualisation.redline_vis import redline_vis_competitor_html, redline_vis_competitor_pdf, redline_vis_generic, redline_vis_generic_eventpdf, redline_vis_generic_eventhtml


app = Flask(__name__)
#randon 24 character string
# python
# >>> import os
# >>> os.urandom(24)
app.secret_key = b' q/\x8ax"\xe9\xfc\x8a0v\x1a\x18\r\x8f\xc1\xb7\xf4\x14\xd0\xb8j:\xb1'

#setup consistent logging
util.data.setup_logger()

logger = logging.getLogger()

# Dummy password (store in environment variable or config in production)
ADMIN_PASSWORD = 'admin'

OutputInfo = False

# printout to confirm pkg versions.
if(OutputInfo == True): 

    import numpy as np
    import matplotlib as mpl
    import seaborn as sns
    import sys;
    print('python versions ', sys.version)
    print('pandas ', pd.__version__, 'numpy ', np.__version__,'matplotlib ', mpl.__version__,'seaborn ', sns.__version__)


@app.before_request
def ensure_log_levels_session():
    if 'log_levels' not in session:
        session['log_levels'] = {
            'global': logging.getLevelName(util.data.DEFAULT_LOG_LEVEL),
            'handlers': {
                'file': logging.getLevelName(util.data.DEFAULT_LOG_FILE_LEVEL),
                'console': logging.getLevelName(util.data.DEFAULT_LOG_CONSOLE_LEVEL)
            }
        }

@app.route('/', methods=["GET"])
def gethome():
    print('Request to / GET received', request)

    #clear the search results.
    session.pop('search_results', None)

    #list of pngs to be displayed on home page
    pnglistHome = [ str(util.data.PNG_HTML_DIR / Path('visualisation_samples.png')),  
                    str(util.data.PNG_HTML_DIR / Path('results_sample.png')),
                    str(util.data.PNG_HTML_DIR / Path('results_table.png')),
                    str(util.data.PNG_HTML_DIR / Path('searchlist.png')),
                    str(util.data.PNG_HTML_DIR / Path('individual_visualisation.png'))
                    ]
    
    strlistHome = [ "A Sample of Visualisations you can expect",  
                    "A Selction of Results avaialable",
                    "Filtered Results under your control"
                    "Search for yourself and your friends",
                    "Example of competitor visualisation"
                    ]
    
    pngListLen = len(pnglistHome)

    return render_template('home.html', png_files=pnglistHome, str_list=strlistHome, pngListLen=pngListLen)


# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            flash("You must log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash("Login successful!", "success")
            return redirect(url_for('admin'))
        else:
            flash("Incorrect password. Try again.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.route('/admin')
@login_required
def admin():
    
    #clear the search results.
    session.pop('search_results', None)

    levels = session.get('log_levels') or util.data.get_log_levels()

    print("Log levels: ",levels)   

    return render_template("admin.html", current_log_levels=levels)


@app.route('/admin', methods=["POST"])
@login_required
def postadmin():

    print('Request to / POST received', request)

    #Adming actity to clear the results on request.
    session.pop('search_results', None)

    # get which button was clicked in home.html
    # and call the appropriate function
    # for that button

    regenerate = request.form.get("regenerateBtn")
    generated_delete = request.form.get("deleteGeneratedFilesBtn")
    competitor_delete = request.form.get("deleteCompetitorFilesBtn")

    if generated_delete:
        print("Delete Generated files")
        # Delete all the Generic files include Competitor
        util.data.delete_generated_files()

    elif competitor_delete:
        print("Delete Competitor files")
        # Delete all the Competitor files include
        util.data.delete_competitor_files()

    elif regenerate:
        print("Regenerate output") 
        htmlString = " "
        pngList = []
 
        redline_vis_generic(htmlString, pngList)


    levels = util.data.get_log_levels() or session.get('log_levels')
    print("Log levels: ",levels)    
    return render_template("admin.html", current_log_levels=levels)

@app.route('/admin/feedback')
@login_required
def admin_feedback():

    page = int(request.args.get('page', 1))
    per_page = 10

    feedback_list = []
    filename = util.data.CSV_FEEDBACK_DIR / Path('feedback.csv')

    if os.path.exists(filename):
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            feedback_list = list(reader)

    total = len(feedback_list)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_feedback = feedback_list[start:end]
    total_pages = math.ceil(total / per_page)

    return render_template('admin_feedback.html',
                           feedback_list=paginated_feedback,
                           page=page,
                           total_pages=total_pages)

@app.route('/admin/feedback/export')
@login_required
def export_feedback():

    filename = util.data.CSV_FEEDBACK_DIR / Path('feedback.csv')

    return send_file(filename, as_attachment=True, download_name='feedback.csv')

@app.route('/admin/clear_feedback', methods=['POST'])
@login_required
def clear_feedback():

    filename = util.data.CSV_FEEDBACK_DIR / Path('feedback.csv')

    # Overwrite the file with headers only, if exists
    if os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            #writer.writerow(['timestamp', 'message', 'email'])

    flash("All feedback has been cleared.", "success")
    return redirect(url_for('admin_feedback'))



@app.route('/admin/logs/download')
@login_required
def download_logs():

    filename = util.data.LOG_FILE_DIR / Path('activity.log')
    return send_file(filename, as_attachment=True)

@app.route('/admin/logs/clear', methods=['POST'])
@login_required
def clear_logs():

    filename = util.data.LOG_FILE_DIR / Path('activity.log')
    with open(filename, 'w') as f:
        f.truncate()
    flash('Log file cleared.')
    return redirect(url_for('view_logs'))  # adjust route as needed

@app.route('/admin/logs')
@login_required
def view_logs():

    ANSI_ESCAPE_RE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

    try:
        filename = util.data.LOG_FILE_DIR / Path('activity.log')
        with open(filename, 'r') as f:
            raw_log = f.read()
            log_contents = ANSI_ESCAPE_RE.sub('', raw_log)  # 🔍 Strip ANSI codes
    except FileNotFoundError:
        log_contents = 'Log file not found.'

    return render_template('admin_logs.html', log_contents=log_contents)

@app.route('/admin/set-log-level', methods=['POST'])
def set_log_level():
    if not session.get('logged_in'):
        abort(403)

    global_level = request.form.get('global_log_level')
    file_level = request.form.get('file_log_level')
    console_level = request.form.get('console_log_level')

    util.data.update_log_level(
        global_level=global_level,
        handler_levels={
            'file': file_level,
            'console': console_level
        }
    )

    # Store in session for display in dropdowns
    session['log_levels'] = {
        'global': global_level,
        'handlers': {
            'file': file_level,
            'console': console_level
        }
    }

    flash("Log levels updated.", "success")
    return redirect(url_for('admin'))

@app.route('/about')
def about():
    
    logger = logging.getLogger()

    logger.debug("This is a debug message")    # Typically used for detailed dev info
    logger.info("This is an info message")     # General application info
    logger.warning("This is a warning")        # Something unexpected, but not fatal
    logger.error("This is an error message")   # Serious problem, app still running
    logger.critical("This is critical") 

    #list of pngs to be displayed on about page
    pnglistAbout = [ str(util.data.PNG_HTML_DIR / Path('redline_author.png'))]

    #clear the search results.
    session.pop('search_results', None)

    return render_template('about.html', png_files=pnglistAbout)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        comments = request.form.get('comments', '').strip()

        if not comments:
            flash('Please provide some feedback before submitting.', "warning")
            return redirect('/feedback')

        filename = util.data.CSV_FEEDBACK_DIR / Path('feedback.csv')

        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), name, email, comments])

        flash('Thanks for your feedback!', "success")
        return redirect('/feedback')

    return render_template('feedback.html')

@app.route('/search')
def index():
    print('Request to /search GET received')
    return render_template('search.html' )


@app.route('/results', methods=["GET", "POST"])
def results():

    #clear the search results.
    session.pop('search_results', None)

    selected_gender = request.form.get("gender_filter")
    selected_year = request.form.get("year_filter")
    selected_cat = request.form.get("cat_filter")
    selected_location = request.form.get("location_filter")

    # Get unique years
    years = sorted({entry[2] for entry in util.data.EVENT_DATA_LIST})

    # Filter based on year selection
    if selected_year:
        filtered_data = [entry for entry in util.data.EVENT_DATA_LIST if entry[2] == selected_year]
    else:
        filtered_data = util.data.EVENT_DATA_LIST  # default to show all

    # Get unique genders
    genders = sorted({entry[3] for entry in filtered_data})

    # Filter based on gender selection
    if selected_gender:
        filtered_data = [entry for entry in filtered_data if entry[3] == selected_gender]
    else:
        filtered_data = filtered_data  # default to show all

    # Get unique categories
    cats = sorted({entry[4] for entry in filtered_data})

    # Filter based on gender selection
    if selected_cat:
        filtered_data = [entry for entry in filtered_data if entry[4] == selected_cat]
    else:
        filtered_data = filtered_data  # default to show all

    # Get unique locations
    locations = sorted({entry[5] for entry in filtered_data})

    # Filter based on location selection
    if selected_location:
        filtered_data = [entry for entry in filtered_data if entry[5] == selected_location]
    else:
        filtered_data = filtered_data  # default to show all

    return render_template("results.html", data=filtered_data, 
                           years=years, selected_year=selected_year,
                           genders=genders, selected_gender=selected_gender,
                           cats=cats, selected_cat=selected_cat, 
                           locations=locations, selected_location=selected_location)

@app.route('/display', methods=["GET"])
def getdisplayEvent():

    print('Request to /display GET received', request)

    # get the eventname    
    eventname = request.args.get('eventname')
 
    #find index  of eventid in util.data.EVENT_DATA_LIST[0]
    index = next((i for i, item in enumerate(util.data.EVENT_DATA_LIST) if item[0] == eventname), None)

    return render_template('display.html', 
                           id=util.data.EVENT_DATA_LIST[index][0], 
                           description=util.data.EVENT_DATA_LIST[index][1], 
                           year=util.data.EVENT_DATA_LIST[index][2])


@app.route('/display', methods=["POST"])
def postdisplayEvent():

    print('Request to /display POST received', request)

    selected_view = None
    selected_format = None

    # get the eventname    
    eventname = request.args.get('eventname')
 
    #find index  of eventid in util.data.EVENT_DATA_LIST[0]
    index = next((i for i, item in enumerate(util.data.EVENT_DATA_LIST) if item[0] == eventname), None)

    selected_view = request.form.get("view_option")
    selected_format = request.form.get("output_format")

    if selected_view == "visualization" and selected_format == "html":

        details = {
            'competitor': None, 
            'race_no': None,
            'event': util.data.EVENT_DATA_LIST[index][0]
        }

        htmlString = ""
        io_pngList = []

        htmlString, io_pngList = redline_vis_generic_eventhtml(details, htmlString, io_pngList)
 
        return render_template('visual.html', description=util.data.EVENT_DATA_LIST[index][1], png_files=io_pngList)
    
    if selected_view == "table" and selected_format == "html":

        filepath = Path(util.data.CSV_GENERIC_DIR) / Path('duration' + util.data.EVENT_DATA_LIST[index][0] + ".csv")
        title = util.data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        return render_template('table.html', headers=headers, data=data, title=title)

    if selected_view == "orig_table" and selected_format == "html":

        filepath = Path(util.data.CSV_INPUT_DIR) / Path(util.data.EVENT_DATA_LIST[index][0] + ".csv")
        title = util.data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        return render_template('table.html', headers=headers, data=data, title=title)
               
    if selected_view == "visualization" and selected_format == "file":

        details = {
            'competitor': None, 
            'race_no': None,
            'event': util.data.EVENT_DATA_LIST[index][0]
        }

        htmlString = ""
        io_pngList = []

        # get the file path
        filepath = Path(util.data.PDF_GENERIC_DIR) / Path(util.data.EVENT_DATA_LIST[index][0] + ".pdf")

        # check if file exists
        if (os.path.isfile(filepath) == False):
            htmlString, io_pngList = redline_vis_generic_eventpdf(details, htmlString, io_pngList)

    if selected_view == "table" and selected_format == "file":
        # get the file path
        filepath = Path(util.data.CSV_GENERIC_DIR) / Path('duration' + util.data.EVENT_DATA_LIST[index][0] + ".csv")

    if selected_view == "orig_table" and selected_format == "file":
        # get the file path
        filepath = Path(util.data.CSV_INPUT_DIR) / Path(util.data.EVENT_DATA_LIST[index][0] + ".csv")

    # dowload the file
    response = send_file(filepath, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(filepath)}"
    return response

@app.route('/api/search', methods=['GET'])
def get_search_results():
    print('Request to /api/search GET received')

    search_results = session.get('search_results', [])

    if not search_results:
        print('No matches found')
        return jsonify("No matches found")
    print('Returning search results')
    return jsonify(search_results)


@app.route('/api/search', methods=['POST'])
def new_search():
    
    # call the find_competitor function, and store result in matches
    print('Request to /api/search POST received')

    #clear the search results.
    session.pop('search_results', None)

    search_query = request.form['competitor'].upper()

    if not search_query:
        print('No search query found /api/search POST received')
        return jsonify("No matches found")

    # We'll define a local variable to store the matches
    matches = []

    # Populate the matches list using the callback
    find_competitor(search_query, lambda competitor, returned_matches: matches.extend(list(returned_matches)))

    if not matches:
        print('No matches found /api/search POST received')
        return jsonify("No matches found")

    # Store in session
    session['search_results'] = matches
    print('Search results stored in session.')

    return jsonify({'status': 'ok', 'data': matches})


@app.route('/api/search/', methods=['DELETE'])
def clear_search():
    
    print('Request to /api/search/ DELETE received', request.form)
    session.pop('search_results', None)

    return jsonify({'status': 'cleared'})


@app.route('/display_vis', methods=['GET'])
def get_display_vis():
        print('Request to /display_vis GET received')
        competitor = request.args.get('competitor').title()
        race_no = request.args.get('race_no')
        event = request.args.get('event')

        #find index  of eventid in util.data.EVENT_DATA_LIST[0]
        index = next((i for i, item in enumerate(util.data.EVENT_DATA_LIST) if item[0] == event), None)
        description=util.data.EVENT_DATA_LIST[index][1]

        try:
            return render_template('display_vis.html', competitor=competitor, race_no=race_no, description=description)
        except Exception as e:
            print("❌ Template render error:", e)
            return abort(500)


@app.route('/display_vis', methods=['POST'])
def post_display_vis():
        
        htmlString = " "
        io_pngList = []

        selected_format = request.form.get('output_format')

        print('Request to /display_vis POST received',selected_format)
        competitor = request.args.get('competitor')
        race_no = request.args.get('race_no')
        event = request.args.get('event')

        #find index  of eventid in util.data.EVENT_DATA_LIST[0]
        index = next((i for i, item in enumerate(util.data.EVENT_DATA_LIST) if item[0] == event), None)

        description=util.data.EVENT_DATA_LIST[index][1]

        details = {
            'competitor': competitor, 
            'race_no': race_no,
            'event': event
        }

        if selected_format == "html":
            htmlString, io_pngList = redline_vis_competitor_html(details, htmlString, io_pngList)

            try:
                return render_template('display_vis.html', selected_format = selected_format, competitor=competitor.title(),  race_no=race_no, description=description, htmlString=htmlString, png_files=io_pngList)
            except Exception as e:
                print("❌ Template render error:", e)
                return abort(500)

        if selected_format == "file":

            # get the file path
            filepath = Path(util.data.PDF_COMP_DIR) / Path(event + competitor + ".pdf")

            # check if file exists
            if (os.path.isfile(filepath) == False):
                redline_vis_competitor_pdf(details, htmlString, io_pngList)
            
            # dowload the file
            response = send_file(filepath, as_attachment=True)
            response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(filepath)}"

            print(response)
            return response
        

##############################


#app.config["TEMPLATES_AUTO_RELOAD"] = True
#app.config["EXPLAIN_TEMPLATE_LOADING"] = True

#Run the app on localhost port 5000
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)


