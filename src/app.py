from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, abort, session, redirect, url_for,  flash, g, make_response
from markupsafe import escape
from functools import wraps
from datetime import datetime, timedelta, tzinfo

from google.cloud import storage
import tempfile

#import base64

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

#for blog purposes
import os
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length
from flask_wtf.file import FileAllowed
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash # If you have user auth
from slugify import slugify # For URL-friendly slugs
from functools import wraps
import shutil
import json

# local inclusion.
from rl.rl_search import find_competitor
import rl.rl_data as rl_data 
from rl.rl_config import get_config 
from rl.rl_vis import redline_vis_competitor_html, redline_vis_competitor_pdf, redline_vis_generic, redline_vis_generic_eventpdf, redline_vis_generic_eventhtml



def create_app():
    """Create and configure the Flask application."""
    # Print current working directory for debugging
    # print(f"Current working directory: {os.getcwd()}")
    
    # Get configuration based on environment
    config_class = get_config()
    
    # Create Flask app
    app = Flask(__name__) #, static_url_path='/src/static') #, static_folder='src/static'

    # Apply configuration
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Initialize flask-session data
    #Session(app=app)

    # Set up the logger
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
    'img-src': [
            '\'self\'',
            'data:',  # Keep if you use data URIs for images
            'https://storage.googleapis.com'  # <-- ADD THIS
        ],
        'connect-src': "'self'",
        'frame-ancestors': "'self'"
    }

    Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src','style-src'],
        force_https=False
    )

    env_mode = os.environ.get('ENV_MODE', 'development').lower()

    #only use google cloud storage if in deploy mode
    if env_mode != 'deploy':

        #copy from local to gcs
        #rl_data.sync_local_blogs_to_gcs()
    #else:
        # Ensure blog_data directory exists
        if not os.path.exists(rl_data.BLOG_DATA_DIR):
            os.makedirs(rl_data.BLOG_DATA_DIR)


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

    OutputInfo = False

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

@app.context_processor
def inject_global_vars():
    global_config = rl_data.load_global_blog_config()
    return dict(
        get_all_posts_for_template=rl_data.get_all_posts, # For sidebar recent posts
        thumbnail_prefix=rl_data.THUMBNAIL_PREFIX,
        max_images_per_post_const=rl_data.MAX_IMAGES_PER_POST
    )

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

@app.before_request
def make_session_permanent():
    session.permanent = True

    #app.logger.debug(f"Session data at {request.path}: {dict(session)}")
    #app.logger.debug(f"Session cookie: {request.cookies.get('session')}")

@app.template_filter('format_datetime')
def format_datetime_filter(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ""
    try:
        # If it's already a datetime object
        if isinstance(value, datetime):
            return value.strftime(format)
        # If it's an ISO string
        dt = datetime.fromisoformat(value)
        return dt.strftime(format)
    except (ValueError, TypeError):
        return value # Return original if parsing fails

#####
### app.routes
####

@app.route('/', methods=["GET"])
def gethome():

    app.logger.debug(f"/ GET received {request}")

    #clear the search results.
    session.pop('search_results', None)

    global_config = rl_data.load_global_blog_config()
    max_home_featured = global_config.get('max_featured_posts_on_home', 3)
    
    all_published_posts = rl_data.get_all_posts() # Published only
    featured_posts = [p for p in all_published_posts if p.get('is_featured', False)][:max_home_featured]
    
    # If not enough "featured", fill with most recent published (up to max_home_featured)
    if len(featured_posts) < max_home_featured:
        # Get recent posts that are not already in featured_posts
        recent_additional = [
            p for p in all_published_posts 
            if p not in featured_posts
        ][:max_home_featured - len(featured_posts)]
        featured_posts.extend(recent_additional)

    return render_template('home.html', featured_posts=featured_posts)

@app.route("/sitemap.xml")
def sitemap():
    app.logger.info("Sitemap.xml route handler was called (dynamic).")
    pages = []

    # Static pages
    # For 'loc', use url_for with _external=True or construct with BASE_URL.
    # For sitemaps, explicit BASE_URL + path is often safer.
    static_routes_info = [
        {'path': '/', 'priority': '1.0', 'changefreq': 'daily', 'template': 'home.html'}, # Assuming you have an index.html template
        {'path': '/blog', 'priority': '0.9', 'changefreq': 'weekly', 'template': 'blog_index.html'}, # Or however your main blog page is served
        {'path': '/about', 'priority': '0.9', 'changefreq': 'monthly', 'template': 'about.html'},
        {'path': '/search', 'priority': '0.7', 'changefreq': 'monthly', 'template': 'search.html'},
        {'path': '/results', 'priority': '0.7', 'changefreq': 'yearly', 'template': 'results.html'},
        {'path': '/feedback', 'priority': '0.7', 'changefreq': 'yearly', 'template': 'feedback.html'},
    ]

    for route_info in static_routes_info:
        # Ensure a template is specified for lastmod calculation
        lastmod_val = rl_data.get_static_page_lastmod(route_info['template']) if route_info.get('template') else None
        pages.append({
            'loc': f"{rl_data.BASE_URL.rstrip('/')}{route_info['path']}",
            'priority': route_info['priority'],
            'changefreq': route_info['changefreq'],
            'lastmod': lastmod_val
        })    


    # Dynamic Blog Posts from rl_data.BLOG_DATA_DIR
    # Ensure rl_data.BLOG_DATA_DIR is the correct path to the directory containing post subfolders
    # e.g., /app/my_blog_data/posts/ (if posts are in /app/my_blog_data/posts/post-slug-folder/)
    blog_data_path = rl_data.BLOG_DATA_DIR # Use the actual path from your rl_data module
    #app.logger.info(f"Scanning for blog posts in: {blog_data_path}")

    if not os.path.exists(blog_data_path) or not os.path.isdir(blog_data_path):
        app.logger.error(f"Blog data directory not found or not a directory: {blog_data_path}")
    else:
        for post_folder_name in os.listdir(blog_data_path):
            post_folder_path = os.path.join(blog_data_path, post_folder_name)
            if os.path.isdir(post_folder_path):
                content_file_path = os.path.join(post_folder_path, 'content.json')
                if os.path.exists(content_file_path):
                    try:
                        with open(content_file_path, 'r', encoding='utf-8') as f:
                            post_content = json.load(f)

                        if post_content.get('is_published', False) and 'slug' in post_content and 'updated_at' in post_content:
                            pages.append({
                                'loc': f"{rl_data.BASE_URL}/blog/{post_content['slug']}",
                                'lastmod': rl_data.format_iso_datetime_for_sitemap(post_content['updated_at']),
                                'changefreq': 'weekly', # Or 'monthly' if posts rarely update after publishing
                                'priority': '0.8'      # Individual blog posts are usually important
                            })
                        elif not post_content.get('is_published', False):
                            app.logger.debug(f"Skipping unpublished post: {post_content.get('slug', post_folder_name)}")
                        else:
                            app.logger.warning(f"Skipping post in {post_folder_name} due to missing slug or updated_at in content.json")

                    except json.JSONDecodeError:
                        app.logger.error(f"Error decoding JSON for post in {post_folder_name}/content.json")
                    except Exception as e:
                        app.logger.error(f"Error processing post {post_folder_name}: {e}")
                else:
                    app.logger.warning(f"No content.json found in blog post folder: {post_folder_path}")

    try:
        sitemap_xml_content = render_template("sitemap.xml", pages=pages)
        response = make_response(sitemap_xml_content)
        response.headers["Content-Type"] = "application/xml"
        #app.logger.info(f"Successfully rendered sitemap.xml with {len(pages)} URLs.")
        return response
    except Exception as e:
        app.logger.error(f"Error rendering sitemap.xml: {e}", exc_info=True)
        return "Error generating sitemap", 500

@app.route('/robots.txt')
def robots_txt():
    app.logger.info("robots.txt route handler was called.")
    # Serves 'robots.txt' from your 'static_folder' (which is 'static/')
    return send_from_directory(rl_data.ROBOTS_DIR, 'robots.txt')


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

        name = request.form.get('name', '-').strip()
        email = request.form.get('email', '-').strip()
        comments = request.form.get('comments', '-').strip()
        category = request.form.get('category', '-').strip()
        rating = request.form.get('rating', '-').strip()

        if not comments:
            flash('Please provide some feedback before submitting.', "warning")
            return redirect('/feedback')

        env_mode = os.environ.get('ENV_MODE', 'development').lower()

        #only use google cloud storage if in deploy mode
        if env_mode == 'deploy':

            rl_data.save_feedback_to_gcs(name, email, comments, category, rating)

        #else use local file
        else:

            filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().isoformat(), name, email, comments, category, rating])

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
        io_pngStrings=[]

        htmlString, io_pngList, io_pngStrings = redline_vis_generic_eventhtml(details, htmlString, io_pngList, io_pngStrings)
 
        return render_template('visual.html', description=rl_data.EVENT_DATA_LIST[index][1], png_files=io_pngList, png_strings=io_pngStrings)
    
    if selected_view == "table" and selected_format == "html":

        filepath = Path(rl_data.CSV_GENERIC_DIR) / Path('duration' + rl_data.EVENT_DATA_LIST[index][0] + ".csv")
        title = rl_data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath, na_filter=False)

        name_column = df.pop('Name')  # Remove the Name column and store it
        df.insert(0, 'Name', name_column)  # Insert it at position 0(leftmost)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        return render_template('table.html', headers=headers, data=data, title=title)

    if selected_view == "orig_table" and selected_format == "html":

        filepath = Path(rl_data.CSV_INPUT_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".csv")
        title = rl_data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(filepath, na_filter=False)

        name_column = df.pop('Name')  # Remove the Name column and store it
        df.insert(0, 'Name', name_column)  # Insert it at position 0 (leftmost)
       
        # Convert DataFrame to list of dicts (records) for Jinja2
        # This naturally excludes the index
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
        io_pngStrings=[]

        # get the file path
        filepath = Path(rl_data.PDF_GENERIC_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".pdf")

        # check if file exists
        if (os.path.isfile(filepath) == False):
            htmlString, io_pngList, io_pngStrings = redline_vis_generic_eventpdf(details, htmlString, io_pngList, io_pngStrings)

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

        #clear the search results.
        session.pop('search_results', None)

        competitor = request.args.get('competitor').title()
        race_no = request.args.get('race_no')
        event = request.args.get('event')

        #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
        index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == event), None)
        description=rl_data.EVENT_DATA_LIST[index][1]

        #get the link to the race results page
        link = "/display?eventname=" + event

        try:
            return render_template('display_vis.html', competitor=competitor, race_no=race_no, description=description, link=link)
        except Exception as e:
            app.logger.error(f"Template render error: {e}")
            return abort(500)


@app.route('/display_vis', methods=['POST'])
def post_display_vis():
        
        htmlString = " "
        io_pngList = []
        io_pngStrings = []

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
            htmlString, io_pngList, io_pngStrings = redline_vis_competitor_html(details, htmlString, io_pngList, io_pngStrings)

            #get the link to the race results page
            link = "/display?eventname=" + event

            try:
                return render_template('display_vis.html', selected_format = selected_format, competitor=competitor.title(),  race_no=race_no, description=description, htmlString=htmlString, png_files=io_pngList, png_strings=io_pngStrings, link=link)
            except Exception as e:
                app.logger.error(f"Template render error: {e}")
                return abort(500)

        if selected_format == "file":

            # get the file path
            filepath = Path(rl_data.PDF_COMP_DIR) / Path(event + competitor + ".pdf")

            # check if file exists
            if (os.path.isfile(filepath) == False):
                redline_vis_competitor_pdf(details, htmlString, io_pngList, io_pngStrings)
            
            # dowload the file
            response = send_file(filepath, as_attachment=True)
            response.headers["Content-Disposition"] = f"attachment; filename={os.path.basename(filepath)}"

            app.logger.info(f"File downloaded: {response}")
            return response


# 3. User: View blog index (list of posts, searchable)
@app.route('/blog')
@app.route('/blog')
def blog_index():
    all_published_posts = rl_data.get_all_posts() # Default: published only
    # ... (rest of your existing blog_index logic for search, pagination) ...
    query = request.args.get('q', '').lower()
    if query:
        filtered_posts = [p for p in all_published_posts if query in p['headline'].lower() or query in p.get('text','').lower()]
    else:
        filtered_posts = all_published_posts
    
    page = request.args.get('page', 1, type=int); per_page = 10
    start = (page - 1) * per_page; end = start + per_page
    paginated_posts = filtered_posts[start:end]
    total_pages = (len(filtered_posts) + per_page - 1) // per_page

    return render_template('blog_index.html', posts=paginated_posts, title='Blog', query=query, current_page=page, total_pages=total_pages)


# Route to serve blog post images
@app.route('/blog/image/<slug>/<path:filename>')
def blog_post_image(slug, filename):
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    if env_mode == 'deploy':

        # Option 2: Redirect to Signed URL (more secure, handles private images)
        signed_url = rl_data.get_blog_image_url_from_gcs(slug, filename)
        if signed_url:
            return redirect(signed_url)
        else:
            app.logger.warning(f"Could not get signed URL for GCS image: {slug}/images/{filename}")
            abort(404)
    else:
        # Your existing local image serving logic
        # return send_from_directory(os.path.join(rl_data.BLOG_DATA_DIR, slug, 'images'), filename)
        # Ensure your local rl_data.BLOG_DATA_DIR is correctly constructed
        full_image_path_dir = os.path.join(rl_data.LOCAL_BLOG_DATA_DIR, slug, 'images') 
        return send_from_directory(full_image_path_dir, filename)


# User: View individual blog post@app.route('/blog/<slug>')
@app.route('/blog/<slug>')
def blog_post_detail(slug):
    env_mode = os.environ.get('ENV_MODE', 'development').lower()

    post = rl_data.get_post(slug, increment_view_count=True) # Your existing local logic

    if not post: # or not post.get('is_published', True):
        abort(404)
    
    # For image URLs, they need to point to GCS in deploy mode
    # The template will use url_for('blog_post_image', ...)
    # So, blog_post_image route needs to handle GCS.
    return render_template('blog_post_detail.html', post=post, title=post['headline'])

##############################

# Admin routes Below this line

##############################

# Decorator to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
#        session_cookie = request.cookies.get("session")
#        app.logger.debug(f"=== SESSION DEBUG ===")
#        app.logger.debug(f"Request host: {request.host}")
#        app.logger.debug(f"Request URL: {request.url}")
#        app.logger.debug(f"Session cookie: {request.cookies.get('session')}")
#        app.logger.debug(f"Session data: {dict(session)}")
#        app.logger.debug(f"===================")
        if session.get('logged_in') != True:
            flash("You must log in to access this page.", "warning")
            app.logger.warning(f"You must log in to access this page.")

            return redirect(url_for('login', _external=True, _scheme=request.scheme))
        return f(*args, **kwargs)
    return decorated_function

# Updated login route with improved session handling
@app.route('/login', methods=['GET', 'POST'])
def login():
    app.logger.debug(f"/login received {request}")
    
    # Debug session before login attempt
    #app.logger.debug(f"Pre-login session: {dict(session)}")
    
    if request.method == 'POST':
        password = request.form.get('password')
        #app.logger.debug(f"Login attempt with password: {'*' * len(password)}")
        
        if password == config_class.ADMIN_PASSWORD:
            # Clear any existing session data first
            session.clear()
            
            # Set session variables
            session['logged_in'] = True
            session.modified = True  # Ensure the session is saved
            
            #app.logger.debug(f"Post-login session: {dict(session)}")
            flash("Login successful!", "success")
            app.logger.warning(f"Login successful!")
            
            # Use the same scheme and host as the request
            return redirect(url_for('admin', _external=True, _scheme=request.scheme))
        else:
            flash("Incorrect password. Try again.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():

    #app.logger.debug(f"/logout received {request}")
    session.pop('logged_in', None)

    flash("You have been logged out.", "info")
    app.logger.warning(f"You have been logged out!")  
    
    return redirect(url_for('login', _external=True, _scheme=request.scheme))


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

    app.logger.debug(f"regenerate: {regenerate}")
    app.logger.debug(f"generated_delete: {generated_delete}")
    app.logger.debug(f"competitor_delete: {competitor_delete}")

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
 
        redline_vis_generic()

    level1 = rl_data.get_log_levels()
    level2 = session.get('log_levels')

    levels = rl_data.get_log_levels() or session.get('log_levels')
    #app.logger.info(f"Log Levels: {levels} {level1} {level2}") 

    return render_template("admin.html", current_log_levels=levels)

@app.route('/admin/feedback')
@login_required
def admin_feedback():

    app.logger.debug(f"/admin/feedback received {request}")

    page = int(request.args.get('page', 1))
    per_page = 10

    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    
    #only use google cloud storage if in deploy mode
    if env_mode == 'deploy':

        paginated_feedback, total_pages = rl_data.get_paginated_feedback(page, per_page)

    else:

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

    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    
    #only use google cloud storage if in deploy mode
    if env_mode == 'deploy':

        # Set up Google Cloud Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(rl_data.BLOG_BUCKET_NAME)
        
        # Define the GCS object path
        blob = bucket.blob(str(rl_data.FEEDBACK_BLOB_FILEPATH))
        
        if blob.exists():
            # Option 1: For smaller files - use a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                blob.download_to_filename(temp_file.name)
                temp_file_path = temp_file.name
            
            # Send the temporary file and then clean up
            response = send_file(temp_file_path, 
                                as_attachment=True, 
                                download_name='feedback.csv')
                             
            # Setup callback to remove the temp file after the response is sent
            @response.call_on_close
            def cleanup():
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
            return response

    else:

        filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

        return send_file(filename, as_attachment=True, download_name='feedback.csv')



@app.route('/admin/clear_feedback', methods=['POST'])
@login_required
def clear_feedback():

    app.logger.debug(f"/admin/clear_feedback POST received {request}")

    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    
    #only use google cloud storage if in deploy mode
    if env_mode == 'deploy':
        
        # Set up Google Cloud Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(rl_data.BLOG_BUCKET_NAME)
        
        # Define the GCS object path
        blob = bucket.blob(rl_data.FEEDBACK_BLOB_FILEPATH)
        
        if blob.exists():
            # Option 1: Delete the file completely
            blob.delete()
            
            # Option 2: Or replace with an empty file if you prefer
            # blob.upload_from_string('', content_type='text/csv')
    else:  
        filename = rl_data.CSV_FEEDBACK_DIR / Path('feedback.csv')

        # Overwrite the file with headers only, if exists
        if os.path.exists(filename):
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)

    flash("All feedback has been cleared.", "success")
    app.logger.info(f"All feedback has been cleared.")   
    return redirect(url_for('admin_feedback', _external=True, _scheme=request.scheme))

# Admin routes for log management
@app.route('/admin/logs/download')
@login_required
def download_logs():
    app.logger.debug(f"/admin/logs/download received {request}")

    return send_file(rl_data.LOG_FILE, as_attachment=True, download_name='activity.log')

@app.route('/admin/logs/clear', methods=['POST'])
@login_required
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
            app.logger.info(f"Warning: Lock failed during log clear: {e}")
            with open(rl_data.LOG_FILE, 'w') as f:
                   f.truncate()
            
    app.logger.info(f"All logs have been cleared.")
    return app.redirect(app.url_for('view_logs', _external=True, _scheme=request.scheme))

@app.route('/admin/logs')
@login_required
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
@login_required
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
    
    #app.logger.info(f"Log levels updated, global: {global_level}, file: {file_level}, console: {console_level}")
    return app.redirect(app.url_for('admin', _external=True, _scheme=request.scheme))

#
# Create new blog post (GET form, POST submit)
#
# ... (imports: datetime, json, os, slugify, shutil, etc.) ...

@app.route('/admin/blog/new', methods=['GET', 'POST'])
@login_required
def new_blog_post():
    env_mode = os.environ.get('ENV_MODE', 'development').lower()

    if request.method == 'POST':
        headline = request.form.get('headline', '').strip()
        text_content = request.form.get('content', '').strip()
        is_featured = 'is_featured' in request.form
        is_published_now = 'is_published' in request.form

        if not headline:
            flash('Headline is required.', 'danger')
            return render_template('admin_post_blog.html', legend='New Blog Post', form_data=request.form) # Ensure template path

        # --- Slug Generation and Uniqueness Check ---
        original_post_slug = slugify(headline)
        post_slug = original_post_slug
        counter = 1
        slug_exists = True

        while slug_exists:
            if env_mode == 'deploy':
                # Use your GCS helper: from .rl_data_gcs import check_if_post_slug_exists_in_gcs
                slug_exists = rl_data.check_if_post_slug_exists_in_gcs(post_slug)
            else:
                # Use your local config: from .rl_data import LOCAL_BLOG_DATA_DIR
                # This assumes LOCAL_BLOG_DATA_DIR is correctly configured, e.g., app.config['LOCAL_BLOG_DATA_DIR']
                local_blog_dir_for_check = rl_data.LOCAL_BLOG_DATA_DIR
                slug_exists = os.path.exists(os.path.join(local_blog_dir_for_check, post_slug))
            
            if slug_exists:
                app.logger.info(f"Slug '{post_slug}' already exists (mode: {env_mode}). Trying next.")
                post_slug = f"{original_post_slug}-{counter}"
                counter += 1
            else:
                #app.logger.info(f"Generated unique slug '{post_slug}' (mode: {env_mode}).")
                break # Exit while loop, slug is unique
        # --- End Slug Generation ---

        post_dir_local_path = None # Only relevant for local mode
        if env_mode != 'deploy':
            local_blog_dir = rl_data.LOCAL_BLOG_DATA_DIR
            post_dir_local_path = os.path.join(local_blog_dir, post_slug)
            try:
                os.makedirs(post_dir_local_path, exist_ok=True)
                #app.logger.info(f"Created local directory: {post_dir_local_path}")
            except OSError as e:
                flash(f"Could not create local directory for post: {e}", "danger")
                app.logger.error(f"OSError creating local directory {post_dir_local_path}: {e}")
                return render_template('admin/admin_post_blog.html', legend='New Blog Post', form_data=request.form)

        # --- Image Uploading ---
        uploaded_image_basenames = [] # Store just basenames like "img_timestamp_0.png"
        uploaded_image_captions = []
        image_files_from_form = [] # Collect FileStorage objects first

        # Collect all image FileStorage objects
        for i in range(rl_data.MAX_IMAGES_PER_POST):
            image_file = request.files.get(f'image_{i}')
            if image_file and image_file.filename:
                image_files_from_form.append(image_file)
        
        if not image_files_from_form:
            flash('At least one image is required.', 'danger')
            if env_mode != 'deploy' and post_dir_local_path and os.path.exists(post_dir_local_path):
                shutil.rmtree(post_dir_local_path) # Cleanup local dir if created
            return render_template('admin_post_blog.html', legend='New Blog Post', form_data=request.form)

        image_save_failed = False
        for idx, image_file_to_save in enumerate(image_files_from_form):
            caption_text = request.form.get(f'caption_{idx}', '').strip() # Assuming captions are indexed same as image_ fields
            
            # from .rl_data import allowed_file
            if not rl_data.allowed_file(image_file_to_save.filename):
                flash(f'Image {idx+1} ("{image_file_to_save.filename}") has an invalid file type. Not saved.', 'warning')
                continue # Skip this file

            unique_base_name_no_ext = f"img_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{idx}"
            saved_basename_ext = None

            image_file_to_save.seek(0) # Crucial: Reset stream before each save attempt

            if env_mode == 'deploy':
                # from .rl_data_gcs import save_uploaded_image_and_thumbnail_to_gcs
                saved_basename_ext = rl_data.save_uploaded_image_and_thumbnail_to_gcs(
                    post_slug, image_file_to_save, unique_base_name_no_ext
                )
            else:
                # from .rl_data import save_uploaded_image_and_thumbnail as save_image_local
                 saved_basename_ext = rl_data.save_uploaded_image_and_thumbnail(
                    post_slug, image_file_to_save, unique_base_name_no_ext
                )
            
            if saved_basename_ext:
                uploaded_image_basenames.append(saved_basename_ext)
                uploaded_image_captions.append(caption_text)
            else:
                flash(f'Error saving Image {idx+1} ("{image_file_to_save.filename}"). Post creation aborted.', 'danger')
                image_save_failed = True
                break # Stop processing further images

        if image_save_failed or not uploaded_image_basenames:
            if not uploaded_image_basenames and not image_save_failed: # No valid images uploaded
                 flash('At least one valid image is required and must be successfully uploaded.', 'danger')
            
            app.logger.warning(f"Image upload failed or no valid images for new post '{post_slug}'. Cleaning up.")
            # Cleanup logic
            if env_mode == 'deploy':
                # from .rl_data_gcs import delete_blog_post_from_gcs # This deletes content.json AND images
                # Since content.json hasn't been uploaded yet, we only need to delete images if any were uploaded.
                # A simpler GCS cleanup here might be to delete objects under post_slug/images/
                # For now, let's assume if save_post_to_gcs fails, or if we get here, we might call a full delete.
                # This needs a careful GCS cleanup function for partially created posts.
                app.logger.info(f"Attempting GCS cleanup for partially created post '{post_slug}' (if any images were uploaded).")
                for fname in uploaded_image_basenames: # uploaded_image_basenames contains what SUCCEEDED
                    # from .rl_data_gcs import delete_blog_image_and_thumbnail_from_gcs
                    rl_data.delete_blog_image_and_thumbnail_from_gcs(post_slug, fname)
            else: # Local cleanup
                if post_dir_local_path and os.path.exists(post_dir_local_path):
                    shutil.rmtree(post_dir_local_path)
            return render_template('admin_post_blog.html', legend='New Blog Post', form_data=request.form)
        # --- End Image Uploading ---

        # --- Prepare Post Data ---
        now_iso = datetime.now().isoformat()
        published_at_iso = now_iso if is_published_now else None
        post_data = {
            'headline': headline,
            'text': text_content,
            'image_filenames': uploaded_image_basenames, # Use the successfully saved basenames
            'image_captions': uploaded_image_captions,
            'created_at': now_iso,
            'updated_at': now_iso,
            'published_at': published_at_iso,
            'is_featured': is_featured,
            'is_published': is_published_now,
            'view_count': 0,
            'slug': post_slug # The unique slug
        }
        # --- End Prepare Post Data ---

        # --- Save Config File (content.json) ---
        save_config_successful = False
        if env_mode == 'deploy':
            # from .rl_data_gcs import save_post_config_to_gcs
            if rl_data.save_post_config_to_gcs(post_slug, post_data):
                save_config_successful = True
                flash('Blog post created successfully in GCS!', 'success')
            else:
                flash('Error saving blog post config to GCS. Images might have been uploaded. Check GCS.', 'danger')
                # Major error: images uploaded but config failed. May need manual GCS cleanup or retry.
                # For simplicity, we don't automatically delete uploaded images here if config save fails,
                # as it might be a transient GCS issue.
        else: # Local mode
            try:
                with open(os.path.join(post_dir_local_path, 'content.json'), 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, indent=4)
                save_config_successful = True
                flash('Blog post created successfully locally!', 'success')
            except IOError as e:
                flash(f'Error saving local content.json: {e}', 'danger')
                app.logger.error(f"IOError saving local content.json for {post_slug}: {e}")
                # Cleanup images and dir
                if post_dir_local_path and os.path.exists(post_dir_local_path): shutil.rmtree(post_dir_local_path)

        if save_config_successful:
            return redirect(url_for('manage_blog_posts')) 
        else:
            # If config save failed, images might still be there.
            # This path leads back to the form.
            # Cleanup was attempted earlier if image save failed. If config save failed after images,
            # GCS images might still be there. Local images would be in the created dir which might also still be there.
            # This is a complex state to fully roll back automatically.
            if env_mode != 'deploy' and post_dir_local_path and os.path.exists(post_dir_local_path):
                 shutil.rmtree(post_dir_local_path) # Attempt local cleanup if config save failed

            return render_template('admin_post_blog.html', legend='New Blog Post', form_data=request.form)
            
    # GET request
    return render_template('admin_post_blog.html', legend='New Blog Post')


# 1b & 2. Admin: Manage (list, edit, delete links)
@app.route('/admin/blog/manage', methods=['GET', 'POST'])
@login_required
def manage_blog_posts():
    global_config = rl_data.load_global_blog_config()
    if request.method == 'POST':
        try:
            max_featured = int(request.form.get('max_featured_posts_on_home'))
            if max_featured >= 0:
                global_config['max_featured_posts_on_home'] = max_featured
                if rl_data.save_global_blog_config(global_config):
                    flash('Settings updated successfully.', 'success')
                else:
                    flash('Error saving settings.', 'danger')
            else:
                flash('Max featured posts must be a non-negative number.', 'warning')
        except ValueError:
            flash('Invalid number for max featured posts.', 'danger')
        return redirect(url_for('manage_blog_posts')) # Redirect to refresh with GET

    # GET request
    posts = rl_data.get_all_posts(published_only=False) # Show all for admin management
    return render_template('admin_manage_posts.html', 
                           posts=posts, 
                           title='Manage Blog Posts',
                           current_max_featured=global_config.get('max_featured_posts_on_home', 3))

# 2a. Admin: Edit existing post
# ... (all other imports and functions remain the same) ...
# ... (imports) ...


@app.route('/admin/blog/edit/<slug>', methods=['GET', 'POST'])
@login_required
def edit_blog_post(slug):
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    post_data_from_storage = None

    post_data_from_storage = rl_data.get_post(slug) # Assumes this loads from local LOCAL_BLOG_DATA_DIR

    if not post_data_from_storage:
        app.logger.warning(f"Edit attempt for non-existent post '{slug}' in mode '{env_mode}'.")
        abort(404)

    # Work with a copy for modifications
    post_for_processing = dict(post_data_from_storage)

    # --- Caption Alignment (same as before, good for consistency) ---
    filenames_count = len(post_for_processing.get('image_filenames', []))
    captions = post_for_processing.get('image_captions', [])
    if len(captions) < filenames_count:
        captions.extend([""] * (filenames_count - len(captions)))
    elif len(captions) > filenames_count:
        captions = captions[:filenames_count]
    post_for_processing['image_captions'] = captions
    # --- End Caption Alignment ---

    if request.method == 'POST':
        was_published_before_edit = post_for_processing.get('is_published', False)

        post_for_processing['headline'] = request.form.get('headline', post_for_processing['headline'])
        post_for_processing['text'] = request.form.get('content', post_for_processing['text'])
        post_for_processing['is_featured'] = 'is_featured' in request.form
        is_published_now = 'is_published' in request.form
        post_for_processing['is_published'] = is_published_now

        # --- Image Processing ---
        # Start with copies of what was loaded (before any POST modifications to post_for_processing lists)
        original_filenames_from_storage = list(post_data_from_storage.get('image_filenames', []))
        original_captions_from_storage = list(post_data_from_storage.get('image_captions', []))
        # Sync original_captions length with original_filenames before processing deletions
        if len(original_captions_from_storage) < len(original_filenames_from_storage):
            original_captions_from_storage.extend([""] * (len(original_filenames_from_storage) - len(original_captions_from_storage)))
        elif len(original_captions_from_storage) > len(original_filenames_from_storage):
            original_captions_from_storage = original_captions_from_storage[:len(original_filenames_from_storage)]

        final_filenames = []
        final_captions = []

        # 1. Process Existing Images: Keep or Delete, and Update Captions
        for i, existing_filename in enumerate(original_filenames_from_storage):
            if request.form.get(f'delete_image_{i}'):
                # Image marked for deletion
                if env_mode == 'deploy':
                    rl_data.delete_blog_image_and_thumbnail_from_gcs(slug, existing_filename)
                else:
                    rl_data.delete_blog_image_and_thumbnail(slug, existing_filename)
                app.logger.info(f"Deleted image '{existing_filename}' for post '{slug}' (mode: {env_mode}).")
            else:
                # Image is kept
                final_filenames.append(existing_filename)
                # Update its caption from the form
                updated_caption = request.form.get(f'current_caption_{i}', '').strip()
                final_captions.append(updated_caption)

        # 2. Handle New Image Uploads
        # Assuming rl_data.MAX_IMAGES_PER_POST is defined
        for i in range(rl_data.MAX_IMAGES_PER_POST):
            if len(final_filenames) >= rl_data.MAX_IMAGES_PER_POST:
                if request.files.get(f'new_image_{i}') and request.files.get(f'new_image_{i}').filename: # Check if user tried to upload more
                    flash(f'Maximum of {rl_data.MAX_IMAGES_PER_POST} images reached. Additional uploads ignored.', 'warning')
                break # Stop processing new uploads if max is reached

            image_file = request.files.get(f'new_image_{i}') # This is a FileStorage object
            new_caption_text = request.form.get(f'new_caption_{i}', '').strip()

            if image_file and image_file.filename:
                if not rl_data.allowed_file(image_file.filename): # Common utility function
                    flash(f'New Image (slot {i+1}) has an invalid file type. Not saved.', 'warning')
                    continue

                # Generate a unique base name for the image to avoid collisions
                unique_base_name = f"img_edit_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{i}"
                saved_image_basename = None

                if env_mode == 'deploy':
                    # This function needs to handle FileStorage, create full & thumb, upload both to GCS,
                    # and return the base filename (e.g., "img_edit_timestamp_i.png")
                    saved_image_basename = rl_data.save_uploaded_image_and_thumbnail_to_gcs(
                        slug, image_file, unique_base_name
                    )
                else:
                    saved_image_basename = rl_data.save_uploaded_image_and_thumbnail(
                        slug, image_file, unique_base_name
                    )

                if saved_image_basename:
                    final_filenames.append(saved_image_basename)
                    final_captions.append(new_caption_text)
                    app.logger.info(f"Saved new image '{saved_image_basename}' for post '{slug}' (mode: {env_mode}).")
                else:
                    flash(f'Error saving new Image (slot {i+1}). Check logs.', 'warning')
        # --- End Image Processing ---

        post_for_processing['image_filenames'] = final_filenames
        post_for_processing['image_captions'] = final_captions

        if not post_for_processing['image_filenames']:
            flash('A post must have at least one image. Please add an image.', 'danger')
            # To prevent saving without images, return to form. Repopulating is key.
            # This part is tricky to make perfect without a proper form library.
            return render_template('admin_post_blog.html', # Assuming this is your template
                                   legend=f'Edit Post: "{post_data_from_storage["headline"]}"',
                                   post=post_for_processing, # Pass the current state
                                   form_data=request.form, # Pass raw form data for repopulation
                                   current_images_for_form=post_for_processing.get('image_filenames', []),
                                   current_captions_for_form=post_for_processing.get('image_captions', []))


        # --- Timestamps and Published_at Logic (same as before) ---
        now_iso = datetime.now().isoformat()
        post_for_processing['updated_at'] = now_iso

        if is_published_now and not was_published_before_edit:
            post_for_processing['published_at'] = now_iso
        elif is_published_now and was_published_before_edit:
            if not post_for_processing.get('published_at'): # For older posts missing this field
                post_for_processing['published_at'] = post_for_processing.get('created_at', now_iso)
        # If not is_published_now, published_at is preserved (or remains None)
        # --- End Timestamps ---

        # Save the updated post_for_processing data
        save_successful = False
        if env_mode == 'deploy':
            save_successful = rl_data.save_post_to_gcs(slug, post_for_processing)
        else:
            local_post_dir_path = os.path.join(rl_data.LOCAL_BLOG_DATA_DIR, slug) # Define LOCAL_BLOG_DATA_DIR
            # Ensure local directory exists (it should for an edit)
            if not os.path.exists(local_post_dir_path): os.makedirs(local_post_dir_path, exist_ok=True)
            try:
                with open(os.path.join(local_post_dir_path, 'content.json'), 'w') as f:
                    json.dump(post_for_processing, f, indent=4)
                save_successful = True
            except IOError as e:
                app.logger.error(f"Error writing local content.json for {slug}: {e}")
                flash(f'Error saving post data locally: {e}', 'danger')

        if save_successful:
            flash('Blog post updated successfully!', 'success')
            return redirect(url_for('manage_blog_posts')) # Make sure this route exists
        else:
            flash('Error saving post data. Check logs.', 'danger')
            # Fall through to render form again, ideally with submitted data
            # This is where a form library (like WTForms) would greatly simplify repopulation.


    # --- GET request or if POST had issues and fell through ---
    # For GET, `post_for_processing` (which is a copy of `post_data_from_storage`
    # with aligned captions) is used to populate the form.
    form_data_for_template = {
        'headline': post_for_processing['headline'],
        'content': post_for_processing['text'],
        'is_featured': post_for_processing.get('is_featured', False),
        'is_published': post_for_processing.get('is_published', True) # Default to true if not set
    }
    return render_template('admin_post_blog.html', # Use consistent template name
                           legend=f'Edit Post: "{post_for_processing["headline"]}"',
                           post=post_for_processing,
                           form_data=form_data_for_template,
                           current_images_for_form=post_for_processing.get('image_filenames', []),
                           current_captions_for_form=post_for_processing.get('image_captions', []))

def handle_rm_error(function, path, excinfo):
    import stat
    # Is the error an access error?
    if not os.access(path, os.W_OK):
        os.chmod(path, stat.S_IWUSR)
        function(path)
    else:
        raise excinfo

# ... (rest of your app.py) ...
# 2b. Admin: Delete post
@app.route('/admin/blog/delete/<slug>', methods=['POST']) # Use POST for destructive actions
@login_required
def delete_blog_post(slug):
    
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    if env_mode == 'deploy':
        rl_data.delete_blog_post_from_gcs(slug)
    else:
        post_dir = os.path.join(rl_data.BLOG_DATA_DIR, slug)
        if os.path.exists(post_dir) and os.path.isdir(post_dir):
            try:
                shutil.rmtree(post_dir, onexc=handle_rm_error) # This deletes content.json and all images/thumbnails
                flash(f'Post "{slug}" and all its images deleted successfully.', 'success')
            except OSError as e:
                flash(f'Error deleting post (Content deleted, but dir remains) "{slug}": {e}', 'danger')
                app.logger.error(f"Error deleting directory {post_dir}: {e}")
        else:
            flash(f'Post "{slug}" not found for deletion.', 'warning')
    return redirect(url_for('manage_blog_posts'))


@app.route('/admin/sync-blogs-to-gcs', methods=['POST'])
@login_required # Ensure only admins can access
def sync_blogs_to_gcs_route():
    logger = app.logger # Use Flask's app logger

    app.logger.info(f"Sync to GCS requested by admin.")

    # It's good practice to check the ENV_MODE here too,
    # as this operation might behave differently or only make sense in certain modes.
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    
    if env_mode == 'deploy':
        logger.info(f"Running in DEPLOY mode. Sync will attempt to copy from Docker image's local data to GCS.")

        try:
            # Call your actual sync function.
            success = rl_data.sync_local_blogs_to_gcs() 

            if success is True or isinstance(success, dict) and success.get("status") == "success": # Adjust if your sync returns more detail
                flash('Blog post sync to GCS Succeeded.', 'success')
                logger.info(f"Sync function reported success.")
            elif success is False or isinstance(success, dict) and success.get("status") == "partial_success":
                flash('Blog post sync to GCS initiated with some issues. Check logs for details.', 'warning')
                logger.warning(f"Sync function reported partial success or issues.")
            else:
                flash('Blog post sync to GCS failed to initiate or encountered errors. Check logs.', 'danger')
                logger.error(f"Sync function reported failure.")
                
        except Exception as e:
            flash(f'An unexpected error occurred during the sync process: {e}', 'danger')
            logger.error(f"Exception during sync call: {e}", exc_info=True)
    else:
       logger.info(f"Running in {env_mode} mode. Sync will not attempt be attempted") 


    return redirect(url_for('admin')) # Or whatever your main admin page route is named

##############################

# Admin routes Above this line

##############################


#One line of code cut our Flask page load times by 60%
#https://medium.com/building-socratic/the-one-weird-trick-that-cut-our-flask-page-load-time-by-70-87145335f679
#https://www.reddit.com/r/programming/comments/2er5nj/one_line_of_code_cut_our_flask_page_load_times_by/
app.jinja_env.cache = {}

# Run the app if executed directly
if __name__ == "__main__":
    # Only run the app directly if not using Docker
    if config_class.USE_DOCKER == 'False':
        port = int(config_class.PORT)
        debug_mode = config_class.DEBUG
        
        print(f"Starting Flask app on port {port} with debug={debug_mode}")
        app.run('0.0.0.0', port, debug=debug_mode)
    else:
        print(f"Not starting Flask server directly as USE_DOCKER={config_class.USE_DOCKER}")