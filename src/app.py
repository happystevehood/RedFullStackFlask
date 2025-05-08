from flask import Flask, request, jsonify, render_template, send_file, abort, session, redirect, url_for,  flash, g
from markupsafe import escape
from functools import wraps
from datetime import datetime

import base64

import pandas as pd

import os, csv, math, re
from dotenv import load_dotenv
from pathlib import Path
import uuid

import secrets

#for security purposes
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# local inclusion.
from rl.rl_search import find_competitor
import rl.rl_data as rl_data 
from rl.config import get_config 
from rl.rl_vis import redline_vis_competitor_html, redline_vis_competitor_pdf, redline_vis_generic, redline_vis_generic_eventpdf, redline_vis_generic_eventhtml

def create_app():
    """Create and configure the Flask application."""
    # Print current working directory for debugging
    # print(f"Current working directory: {os.getcwd()}")
    
    # Get configuration based on environment
    config_class, use_docker = get_config()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Apply configuration
    app.config.from_object(config_class)
    config_class.init_app(app)

    #get secret key from configutration
    app.secret_key = config_class.SECRET_KEY   

    """Initialize Flask app with improved logging"""
    # Set up the logger
    logger = rl_data.setup_logger()

    # Replace Flask's logger with our improved logger
    app.logger = logger

    #To prevent abuse (e.g., bots spamming the search box), need to review if limits are appropriate
    limiter = Limiter(app=app,
        key_func=get_remote_address,
        default_limits=["50 per minute", "500 per hour", "2000 per day"],
        storage_uri="memory://")    # Use in-memory storage for now, memcache seems like an alternative.

    #protect against Cross-Site Request Forgery:
    csrf = CSRFProtect(app)

    #Headers & Clickjacking Prevention - updated to use nonce - number once
    # For local dev, disable HTTPS enforcement
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
    #        "'unsafe-inline'",   # to remove in production
            'https://code.jquery.com',
            'https://cdn.jsdelivr.net',
            'https://cdn.datatables.net'
        ],
        'style-src': [
            "'self'",
    #        "'unsafe-inline'",   # to remove in production
            'https://cdn.jsdelivr.net',
            'https://cdn.datatables.net'
        ],
        'font-src': "'self' data:",
        'img-src': "'self' data:",
        'connect-src': "'self'",
        'frame-ancestors': "'self'"
    }

    Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src','style-src'],
        force_https=False
    )

    '''
    #Error handling
    app.config['TRAP_HTTP_EXCEPTIONS']=True

    #some local error handing
    @app.errorhandler(Exception)
    def handle_error(e):
        try:
            if e.code == 401:
                return  render_template('error.html', string1="Bad Request", string2="The page you're looking for was not found", 
                                        error_code=e.code,        
                                        name= e.name,
                                        description= e.description)
            elif e.code == 404:
                return  render_template('error.html', string1="Page Not Found", string2="The page you're looking for was not found", 
                                        error_code=e.code,        
                                        name= e.name,
                                        description= e.description)
            if e.code == 405:
                return  render_template('error.html', string1="Method Not Allowed", string2="The page you're looking for was not found", 
                                        error_code=e.code,        
                                        name= e.name,
                                        description= e.description)
            elif e.code == 500:
                return  render_template('error.html', string1="Internal Server Error", string2="The page you're looking for was not found", 
                                        error_code=e.code,        
                                        name= e.name,
                                        description= e.description)
            raise e
        except:
            return  render_template('error.html', string1="Error", string2="Something went wrong")
    '''

    OutputInfo = True

    # printout to confirm pkg versions.
    if(OutputInfo == True): 

        import numpy as np
        import matplotlib as mpl
        import seaborn as sns
        import sys;

        #set debut level to warning so output as start
        app.logger.warning(f"python versions {sys.version}")
        app.logger.warning(f"pandas {pd.__version__}, numpy {np.__version__}, matplotlib { mpl.__version__} 'seaborn {sns.__version__}")

    return app, config_class


#########################
# Create the application here so its available to use!!!
#########################
app, config_class = create_app()


#####
### pre-post processor functions
####

#@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)


# Register before/after request handlers
@app.before_request
def setup_request_logging():
    # Generate a unique ID for this request
    request_id = str(uuid.uuid4())[:8]
    g.request_id = request_id
    
    # Store in thread local for the logger
    rl_data.thread_local.request_id = request_id
    
    # Log the request
    app.logger.debug(f"Request started: {request.method} {request.path}")

#@app.before_request
#def check_cookie():
#    print("Session cookie:", request.cookies.get("session"))

@app.after_request
def log_after_request(response):
    app.logger.debug(f"Request completed: {response.status_code}")
    return response

@app.teardown_request
def teardown_request_logging(exception=None):
    # Clean up thread local
    if hasattr(rl_data.thread_local, 'request_id'):
        delattr(rl_data.thread_local, 'request_id')
    
    if exception:
        app.logger.error(f"Request failed: {str(exception)}")

#####
### app.routes
####

@app.route('/', methods=["GET"])
def gethome():

    app.logger.debug(f"/ GET received {request}")

    #clear the search results.
    session.pop('search_results', None)

    #list of pngs to be displayed on home page
    pnglistHome = [ str(rl_data.PNG_HTML_DIR / Path('visualisation_samples.png')),  
                    str(rl_data.PNG_HTML_DIR / Path('results_sample.png')),
                    str(rl_data.PNG_HTML_DIR / Path('results_table.png')),
                    str(rl_data.PNG_HTML_DIR / Path('searchlist.png')),
                    str(rl_data.PNG_HTML_DIR / Path('individual_visualisation.png'))
                    ]
    
    strlistHome = [ "A Sample of Visualisations you can expect",  
                    "A Selction of Results avaialable",
                    "Filtered Results under your control",
                    "Search for yourself and your friends",
                    "Example of competitor visualisation"
                    ]
    
    pngListLen = len(pnglistHome)

    return render_template('home.html', png_files=pnglistHome, str_list=strlistHome, pngListLen=pngListLen)



@app.route('/about')
def about():
    
    app.logger.debug(f"/about received {request}")

    #Just debug messages to test out logging
    app.logger.debug("/about: This is a debug message")    # Typically used for detailed dev info
    app.logger.info("/about: This is an info message")     # General application info
    app.logger.warning("/about: This is a warning")        # Something unexpected, but not fatal
    app.logger.error("/about: This is an error message")   # Serious problem, app still running
    app.logger.critical("/about: This is critical") 

    #list of pngs to be displayed on about page
    pnglistAbout = [ str(rl_data.PNG_HTML_DIR / Path('redline_author.png'))]

    #clear the search results.
    session.pop('search_results', None)

    return render_template('about.html', png_files=pnglistAbout)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    app.logger.debug(f"/feedback received {request}")

    if request.method == 'POST':

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        comments = request.form.get('comments', '').strip()

        if not comments:
            flash('Please provide some feedback before submitting.', "warning")
            return redirect('/feedback')

        filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().isoformat(), name, email, comments])

        flash('Thanks for your feedback!', "success")
        return redirect('/feedback')

    return render_template('feedback.html')

@app.route('/search')
def index():
    app.logger.debug(f"/search received {request}")
    return render_template('search.html' )


@app.route('/results', methods=["GET", "POST"])
def results():
    app.logger.debug(f"/results received {request}")

    #clear the search results.
    session.pop('search_results', None)

    selected_gender = request.form.get("gender_filter")
    selected_year = request.form.get("year_filter")
    selected_cat = request.form.get("cat_filter")
    selected_location = request.form.get("location_filter")

    app.logger.info(f"/results filters: {selected_gender}, {selected_year}, {selected_cat}, {selected_location}")

    # Get unique years
    years = sorted({entry[2] for entry in rl_data.EVENT_DATA_LIST})

    # Filter based on year selection
    if selected_year:
        filtered_data = [entry for entry in rl_data.EVENT_DATA_LIST if entry[2] == selected_year]
    else:
        filtered_data = rl_data.EVENT_DATA_LIST  # default to show all

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

    app.logger.debug(f"/display GET received {request}")

    # get the eventname    
    eventname = request.args.get('eventname')
 
    #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
    index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == eventname), None)

    return render_template('display.html', 
                           id=rl_data.EVENT_DATA_LIST[index][0], 
                           description=rl_data.EVENT_DATA_LIST[index][1], 
                           year=rl_data.EVENT_DATA_LIST[index][2])


@app.route('/display', methods=["POST"])
def postdisplayEvent():

    app.logger.debug(f"/display POST received {request}")

    selected_view = None
    selected_format = None

    # get the eventname    
    eventname = request.args.get('eventname')
 
    #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
    index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == eventname), None)

    selected_view = request.form.get("view_option")
    selected_format = request.form.get("output_format")

    app.logger.info(f"/display filters: {selected_view}, {selected_format}")

    if selected_view == "visualization" and selected_format == "html":

        details = {
            'competitor': None, 
            'race_no': None,
            'event': rl_data.EVENT_DATA_LIST[index][0]
        }

        htmlString = ""
        io_pngList = []

        htmlString, io_pngList = redline_vis_generic_eventhtml(details, htmlString, io_pngList)
 
        return render_template('visual.html', description=rl_data.EVENT_DATA_LIST[index][1], png_files=io_pngList)
    
    if selected_view == "table" and selected_format == "html":

        filepath = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + rl_data.EVENT_DATA_LIST[index][0] + ".csv")
        title = rl_data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        return render_template('table.html', headers=headers, data=data, title=title)

    if selected_view == "orig_table" and selected_format == "html":

        filepath = Path(rl_data.CSV_INPUT_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".csv")
        title = rl_data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath)

        name_column = df.pop('Name')  # Remove the Name column and store it
        df.insert(0, 'Name', name_column)  # Insert it at position 0 (leftmost)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        return render_template('table.html', headers=headers, data=data, title=title)
               
    if selected_view == "visualization" and selected_format == "file":

        details = {
            'competitor': None, 
            'race_no': None,
            'event': rl_data.EVENT_DATA_LIST[index][0]
        }

        htmlString = ""
        io_pngList = []

        # get the file path
        filepath = Path(rl_data.PDF_GENERIC_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".pdf")

        # check if file exists
        if (os.path.isfile(filepath) == False):
            htmlString, io_pngList = redline_vis_generic_eventpdf(details, htmlString, io_pngList)

    if selected_view == "table" and selected_format == "file":
        # get the file path
        filepath = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + rl_data.EVENT_DATA_LIST[index][0] + ".csv")

    if selected_view == "orig_table" and selected_format == "file":
        # get the file path
        filepath = Path(rl_data.CSV_INPUT_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".csv")

    # dowload the file
    response = send_file(filepath, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(filepath)}"
    return response

@app.route('/api/search', methods=['GET'])
def get_search_results():
        
    app.logger.debug(f"/api/search GET received {request}")

    search_results = session.get('search_results', [])

    if not search_results:
        app.logger.debug(f"/api/search GET No matches found")
        return jsonify("No matches found")
    app.logger.debug(f"/api/search return results {search_results}")
    return jsonify(search_results)


@app.route('/api/search', methods=['POST'])
def new_search():
    
    app.logger.debug(f"/api/search POST received {request}")

    # call the find_competitor function, and store result in matches

    #clear the search results.
    session.pop('search_results', None)

    search_query = request.form['competitor'].upper()

    #sanitise this search query
    search_query = search_query.strip()  # Remove leading/trailing whitespace
    search_query = escape(search_query)  # Prevent injection if rendered back to user

    # Optionally, apply further filtering:
    if len(search_query) > 100:
        app.logger.debug(f"/api/search POST Search term too long: {search_query}")
        flash("Search term too long.", "danger")
        return jsonify("No matches found")

    if not search_query:
        app.logger.debug(f"/api/search POST No search query found")
        return jsonify("No matches found")

    # We'll define a local variable to store the matches
    matches = []

    # Populate the matches list using the callback
    find_competitor(search_query, lambda competitor, returned_matches: matches.extend(list(returned_matches)))

    if not matches:
        app.logger.debug(f"/api/search POST No matches query found")
        return jsonify("No matches found")

    # Store in session
    session['search_results'] = matches

    return jsonify({'status': 'ok', 'data': matches})


@app.route('/display_vis', methods=['GET'])
def get_display_vis():
        app.logger.debug(f"/display_vis GET received {request}")

        competitor = request.args.get('competitor').title()
        race_no = request.args.get('race_no')
        event = request.args.get('event')

        #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
        index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == event), None)
        description=rl_data.EVENT_DATA_LIST[index][1]

        try:
            return render_template('display_vis.html', competitor=competitor, race_no=race_no, description=description)
        except Exception as e:
            app.logger.error(f"Template render error: {e}")
            return abort(500)


@app.route('/display_vis', methods=['POST'])
def post_display_vis():
        
        htmlString = " "
        io_pngList = []

        app.logger.debug(f"/display_vis POST received {request}")

        selected_format = request.form.get('output_format')
        competitor = request.args.get('competitor')
        race_no = request.args.get('race_no')
        event = request.args.get('event')

        app.logger.info(f"selected_format: {selected_format}, competitor: {competitor}, race_no: {race_no}, event: {event}")

        #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
        index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == event), None)

        description=rl_data.EVENT_DATA_LIST[index][1]

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
                app.logger.error(f"Template render error: {e}")
                return abort(500)

        if selected_format == "file":

            # get the file path
            filepath = Path(rl_data.PDF_COMP_DIR) / Path(event + competitor + ".pdf")

            # check if file exists
            if (os.path.isfile(filepath) == False):
                redline_vis_competitor_pdf(details, htmlString, io_pngList)
            
            # dowload the file
            response = send_file(filepath, as_attachment=True)
            response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(filepath)}"

            app.logger.info(f"File downloaded: {response}")
            return response
        
##############################

# Admin routes Below this line

##############################

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != True:
            flash("You must log in to access this page.", "warning")
            app.logger.warning(f"You must log in to access this page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug(f"/login received {request}")

    if request.method == 'POST':
        password = request.form.get('password')
        print(f"password: {config_class.ADMIN_PASSWORD} {password}")
        if password == config_class.ADMIN_PASSWORD:
            session['logged_in'] = True
            flash("Login successful!", "success")
            app.logger.warning(f"Login successful!")            
            return redirect(url_for('admin'))
        else:
            flash("Incorrect password. Try again.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():

    app.logger.debug(f"/logout received {request}")
    session.pop('logged_in', None)

    flash("You have been logged out.", "info")
    app.logger.warning(f"You have been logged out!")  
    
    return redirect(url_for('login'))


@app.route('/admin', methods=["GET"])
@login_required
def admin():

    app.logger.debug(f"/admin received {request}")
    
    #clear the search results.
    session.pop('search_results', None)

    # Get current log levels for display
    log_levels = rl_data.get_log_levels()
    
    # Store in g for template access (not in session)
    g.log_levels = log_levels

    return render_template("admin.html", current_log_levels=log_levels)


@app.route('/admin', methods=["POST"])
@login_required
def postadmin():

    app.logger.debug(f"/admin POST received {request}")

    #Adming actity to clear the results on request.
    session.pop('search_results', None)

    # get which button was clicked in home.html
    # and call the appropriate function
    # for that button

    regenerate = request.form.get("regenerateBtn")
    generated_delete = request.form.get("deleteGeneratedFilesBtn")
    competitor_delete = request.form.get("deleteCompetitorFilesBtn")

    if generated_delete:
        app.logger.debug(f"Delete the generated files")
        # Delete all the Generic files include Competitor
        rl_data.delete_generated_files()

    elif competitor_delete:
        app.logger.debug(f"Delete Competitor files")
        # Delete all the Competitor files include
        rl_data.delete_competitor_files()

    elif regenerate:
        app.logger.debug(f"Regenerate output")
        htmlString = " "
        pngList = []
 
        redline_vis_generic(htmlString, pngList)

    level1 = rl_data.get_log_levels()
    level2 = session.get('log_levels')

    levels = rl_data.get_log_levels() or session.get('log_levels')
    app.logger.info(f"Log Levels: {levels} {level1} {level2}") 

    return render_template("admin.html", current_log_levels=levels)

@app.route('/admin/feedback')
@login_required
def admin_feedback():

    app.logger.debug(f"/admin/feedback received {request}")

    page = int(request.args.get('page', 1))
    per_page = 10

    feedback_list = []
    filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

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

    app.logger.debug(f"/admin/feedback/export received {request}")

    filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

    return send_file(filename, as_attachment=True, download_name='feedback.csv')

@app.route('/admin/clear_feedback', methods=['POST'])
@login_required
def clear_feedback():

    app.logger.debug(f"/admin/clear_feedback POST received {request}")

    filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

    # Overwrite the file with headers only, if exists
    if os.path.exists(filename):
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

    flash("All feedback has been cleared.", "success")
    app.logger.info(f"All feedback has been cleared.")   
    return redirect(url_for('admin_feedback'))

# Admin routes for log management
@app.route('/admin/logs/download')
def download_logs():
    app.logger.debug(f"/admin/logs/download received {request}")

    return send_file(rl_data.LOG_FILE, as_attachment=True, download_name='activity.log')

@app.route('/admin/logs/clear', methods=['POST'])
def clear_logs():
    app.logger.debug(f"/admin/logs/clear POST received {request}")
    
    filename = f"{str(rl_data.LOG_FILE)}.lock"

    try:
        import portalocker
        # Use portalocker with a file path, not a file object
        with portalocker.Lock(filename,  timeout=10):
            with open(rl_data.LOG_FILE, 'w') as f:
                f.truncate()
    except (portalocker.LockException, IOError, OSError) as e:
            # If locking fails, try without locking
            print(f"Warning: Lock failed during log clear: {e}")
            with open(rl_data.LOG_FILE, 'w') as f:
                   f.truncate()
            
    app.logger.info(f"All logs have been cleared.")
    return app.redirect(app.url_for('view_logs'))

@app.route('/admin/logs')
def view_logs():
    app.logger.debug(f"/admin/logs received {request}")
    
    import re
    ANSI_ESCAPE_RE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    
    try:
        with open(rl_data.LOG_FILE, 'r') as f:
            raw_log = f.read()
            log_contents = ANSI_ESCAPE_RE.sub('', raw_log)  # Strip ANSI codes
    except FileNotFoundError:
        app.logger.info(f"Log file not found")
        log_contents = 'Log file not found.'
    
    return render_template('admin_logs.html', log_contents=log_contents)

@app.route('/admin/set-log-level', methods=['POST'])
def set_log_level():
    app.logger.debug(f"/admin/set-log-level POST received {request}")
    
    global_level = request.form.get('global_log_level')
    file_level = request.form.get('file_log_level')
    console_level = request.form.get('console_log_level')
    
    rl_data.update_log_level(
        global_level=global_level,
        handler_levels={
            'file': file_level,
            'console': console_level
        }
    )
    
    app.logger.info(f"Log levels updated, global: {global_level}, file: {file_level}, console: {console_level}")
    return app.redirect(app.url_for('admin'))

##############################

# Admin routes Above this line

##############################


#One line of code cut our Flask page load times by 60%
#https://medium.com/building-socratic/the-one-weird-trick-that-cut-our-flask-page-load-time-by-70-87145335f679
#https://www.reddit.com/r/programming/comments/2er5nj/one_line_of_code_cut_our_flask_page_load_times_by/
#app.jinja_env.cache = {}

# Run the app if executed directly
if __name__ == "__main__":
    # Only run the app directly if not using Docker
    if os.environ.get('USE_DOCKER', 'False').lower() not in ('true', '1', 'yes'):
        debug_mode = app.config.get('DEBUG', False)
        port = app.config.get('PORT', 5000)
        
        print(f"Starting Flask app on port {port} with debug={debug_mode}")
        app.run('0.0.0.0', port, debug=debug_mode)
    else:
        print("Not starting Flask server directly as USE_DOCKER=True")