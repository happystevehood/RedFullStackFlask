from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, abort, session, redirect, url_for,  flash, g, make_response
from markupsafe import escape
from functools import wraps
from datetime import datetime
import logging

from google.cloud import storage
import tempfile

#import base64

import pandas as pd

import os, csv, math
from dotenv import load_dotenv
from pathlib import Path
import uuid
from io import BytesIO

#for security purposes
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

#for blog purposes
from slugify import slugify 
from functools import wraps
import shutil
import json
import re

# --- Define the ANSI Escape Code Regular Expression ---
# This regex matches the patterns for ANSI color codes.
ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# local inclusion.
from rl.rl_search import find_competitor
import rl.rl_data as rl_data 
from rl.rl_dict import OUTPUT_CONFIGS
from rl.rl_config import get_config 
from rl.rl_vis import redline_vis_generate_generic, redline_vis_generate_generic_init, \
    prepare_competitor_visualization_page, redline_vis_generate_competitor_init, \
    generate_single_output_file, \
    MakeFullPdfReport, prepare_visualization_data_for_template


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
        default_limits=["100 per minute", "500 per hour", "2000 per day"],
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

    # --- Enable Jinja2 Loop Controls Extension ---
    app.jinja_env.add_extension('jinja2.ext.loopcontrols') 

    #Error handling
    if env_mode == 'deploy':
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
        app.logger.critical(f"Request failed: {str(exception)}")

@app.before_request
def make_session_permanent():
    session.permanent = True


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

    app.logger.warning(f"/ GET received {request}")

    #clear the session to keep fresh
    session.pop('search_results', None)
    session.pop("outputList", None)
    session.pop('runtime', None)
    session.pop('output_config', None)
    session.pop('async_runtime_vars_snapshot', None)

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
    app.logger.warning("Sitemap.xml route handler was called (dynamic).")
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
        app.logger.critical(f"Blog data directory not found or not a directory: {blog_data_path}")
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
                            app.logger.error(f"Skipping post in {post_folder_name} due to missing slug or updated_at in content.json")

                    except json.JSONDecodeError:
                        app.logger.critical(f"Error decoding JSON for post in {post_folder_name}/content.json")
                    except Exception as e:
                        app.logger.critical(f"Error processing post {post_folder_name}: {e}")
                else:
                    app.logger.error(f"No content.json found in blog post folder: {post_folder_path}")

    try:
        sitemap_xml_content = render_template("sitemap.xml", pages=pages)
        response = make_response(sitemap_xml_content)
        response.headers["Content-Type"] = "application/xml"
        #app.logger.info(f"Successfully rendered sitemap.xml with {len(pages)} URLs.")
        return response
    except Exception as e:
        app.logger.critical(f"Error rendering sitemap.xml: {e}", exc_info=True)
        return "Error generating sitemap", 500

@app.route('/robots.txt')
def robots_txt():
    app.logger.warning("robots.txt route handler was called.")
    # Serves 'robots.txt' from your 'static_folder' (which is 'static/')
    return send_from_directory(rl_data.ROBOTS_DIR, 'robots.txt')

@app.route('/favicon.ico')
def favicon():
    # Serves the favicon from the 'static/favicons/' directory
    return send_from_directory(os.path.join(app.root_path, 'static', 'favicons'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/about')
def about():
    
    app.logger.warning(f"/about received {request}")

    #Just debug messages to test out logging
    #app.logger.debug("/about: This is a debug message")    # Typically used for detailed dev info
    #app.logger.info("/about: This is an info message")     # General application info
    #app.logger.warning("/about: This is a warning")        # Something unexpected, but not fatal
    #app.logger.error("/about: This is an error message")   # Serious problem, app still running
    #app.logger.critical("/about: This is critical") 

    #list of pngs to be displayed on about page
    pnglistAbout = [ str(rl_data.PNG_HTML_DIR / Path('redline_author.png'))]

    #clear the search results.
    session.pop('search_results', None)

    return render_template('about.html', png_files=pnglistAbout)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    app.logger.warning(f"/feedback received {request}")

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
    app.logger.warning(f"/search received {request}")
    return render_template('search.html' )


@app.route('/results', methods=["GET", "POST"])
def results():
    app.logger.warning(f"/results received {request}")

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

    app.logger.warning(f"/display GET received {request}")

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

    app.logger.info(f"/display POST received {request}")

    selected_view = None
    selected_format = None

    # get the eventname    
    eventname = request.args.get('eventname')
 
    #find index  of eventid in rl_data.EVENT_DATA_LIST[0]
    index = next((i for i, item in enumerate(rl_data.EVENT_DATA_LIST) if item[0] == eventname), None)

    selected_view = request.form.get("view_option")
    selected_format = request.form.get("output_format")

    app.logger.warning(f"/display filters: {selected_view}, {selected_format} {eventname}")

    if selected_view == "visualization" and selected_format == "html":

        details = {
                'competitor': None, 
                'race_no': None,
                'event': rl_data.EVENT_DATA_LIST[index][0]
            }

        #initialising the session - need to change name.
        redline_vis_generate_generic_init()

        #Preparte to display generic event results
        template_context = prepare_visualization_data_for_template(competitorDetails=details)
        
        if isinstance(template_context, str): # Error occurred
            return template_context 

        return render_template('visual_lazy_load.html', **template_context)

    if selected_view == "table" and selected_format == "html":

        event_name_slug = slugify(rl_data.EVENT_DATA_LIST[index][0])
        #find cvsfile.
        df_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'duration_csv_generic'), None)
        df_filename = df_conf['filename_template'].format( 
                EVENT_NAME_SLUG=event_name_slug,
                ).replace("__", "_").replace("_.", ".")
        df_dir_path_obj = Path(getattr(rl_data, df_conf['output_dir_const']))
        df_filename = df_dir_path_obj / Path(df_filename)

        title = rl_data.EVENT_DATA_LIST[index][1]

        # Load CSV file into a DataFrame
        df = pd.read_csv(df_filename, na_filter=False)

        name_column = df.pop('Name')  # Remove the Name column and store it
        df.insert(0, 'Name', name_column)  # Insert it at position 0(leftmost)

        # Convert DataFrame to list of dicts (records) for Jinja2
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()
        
        #configure for 2023 format or 2024 format
        if (rl_data.EVENT_DATA_LIST[index][2]=="2023"):
            heatmap_specific_columns = rl_data.STATIONLISTSTART23
        elif (rl_data.EVENT_DATA_LIST[index][2]=="2024"):
            heatmap_specific_columns = rl_data.STATIONLISTSTART24
        elif (rl_data.EVENT_DATA_LIST[index][2]=="2025"):
            heatmap_specific_columns = rl_data.STATIONLISTSTART25
        else:
            app.logger.error(f"ERROR: Event year not found {rl_data.EVENT_DATA_LIST[index][2]}")
            
        #add the time column to the heatmap_specific_columns listdf.dropna
        heatmap_specific_columns.append('Time Adj')
        
        return render_template('table.html', headers=headers, data=data, title=title, enable_heatmap=True, heatmap_specific_columns=heatmap_specific_columns)

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

        return render_template('table.html', headers=headers, data=data, title=title, enable_heatmap=False)

    if selected_view == "pacing_table" and selected_format == "html":

        #filepath = Path(rl_data.CSV_GENERIC_DIR) / Path("PacingTable" + rl_data.EVENT_DATA_LIST[index][0] + ".csv")
        title = rl_data.EVENT_DATA_LIST[index][1] + " Actual 'Pacing' Chart"

        event_name_slug = slugify(rl_data.EVENT_DATA_LIST[index][0])
        #find cvsfile.
        pacing_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pacing_table_csv_generic'), None)
        pace_filename = pacing_conf['filename_template'].format( 
                EVENT_NAME_SLUG=event_name_slug,
                ).replace("__", "_").replace("_.", ".")
        pace_dir_path_obj = Path(getattr(rl_data, pacing_conf['output_dir_const']))
        pace_filename = pace_dir_path_obj / Path(pace_filename)

        # Load CSV file into a DataFrame
        df = pd.read_csv(pace_filename, na_filter=False)
     
        # Convert DataFrame to list of dicts (records) for Jinja2
        # This naturally excludes the index
        data = df.to_dict(orient='records')
        headers = df.columns.tolist()

        tableHtmlString = pacing_conf['html_string_template']
        return render_template('table.html', headers=headers, data=data, title=title, htmlString=tableHtmlString, enable_heatmap=False)
                   
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

        event_name_slug = slugify(rl_data.EVENT_DATA_LIST[index][0])
        #find cvsfile.
        pdf_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_generic'), None)
        pdf_filename = pdf_conf['filename_template'].format( 
                EVENT_NAME_SLUG=event_name_slug,
                ).replace("__", "_").replace("_.", ".")
        pdf_dir_path_obj = Path(getattr(rl_data, pdf_conf['output_dir_const']))
        pace_filename = pdf_dir_path_obj / Path(pdf_filename)

        # get the file path
        filepath = pace_filename

    if selected_view == "table" and selected_format == "file":
        
        event_name_slug = slugify(rl_data.EVENT_DATA_LIST[index][0])
        #find cvsfile.
        df_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'duration_csv_generic'), None)
        df_filename = df_conf['filename_template'].format( 
                EVENT_NAME_SLUG=event_name_slug,
                ).replace("__", "_").replace("_.", ".")
        df_dir_path_obj = Path(getattr(rl_data, df_conf['output_dir_const']))
        df_filename = df_dir_path_obj / Path(df_filename)
        
        # get the file path
        filepath = df_filename

    if selected_view == "orig_table" and selected_format == "file":
        # get the file path
        filepath = Path(rl_data.CSV_INPUT_DIR) / Path(rl_data.EVENT_DATA_LIST[index][0] + ".csv")

    if selected_view == "pacing_table" and selected_format == "file":

        event_name_slug = slugify(rl_data.EVENT_DATA_LIST[index][0])
        #find cvsfile.
        pacing_conf = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pacing_table_csv_generic'), None)
        pace_filename = pacing_conf['filename_template'].format( 
                EVENT_NAME_SLUG=event_name_slug,
                ).replace("__", "_").replace("_.", ".")
        pace_dir_path_obj = Path(getattr(rl_data, pacing_conf['output_dir_const']))
        pace_filename = pace_dir_path_obj / Path(pace_filename)

        filepath = pace_filename

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

    app.logger.warning(f"/api/search POST query {search_query}")

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

# Your existing route might look something like this, or it's the one calling redline_vis_competitor_html
@app.route('/display_competitor_visuals', methods=['GET', 'POST']) # Or whatever your route is
def display_competitor_visuals_route():
    # Get competitorDetails from request.form, request.args, or session
    if request.method == 'POST':
        competitor = request.form.get('competitor')
        race_no = request.form.get('race_no')
        event = request.form.get('event_name')
    else: # GET request
        competitor = request.args.get('competitor')
        race_no = request.args.get('race_no')
        event = request.args.get('event')

    # There are valid cases where the race_no is empty as provided by the organisers....
    # below code cause those cases to fail.
    #if not all([competitor, race_no, event]):
    #    return "Missing parameters (competitor, race_no, event)", 400

    competitorDetails = {
        'competitor': competitor,
        'race_no': race_no,
        'event': event
    }
    
    app.logger.warning(f"/display_competitor_visuals {competitorDetails}")

    # --- Initialize session variables if not present ---
    redline_vis_generate_competitor_init()

    # Call your new preparation function
    # This function will return render_template(...)
    return prepare_competitor_visualization_page(competitorDetails)


@app.route('/generate_image_async', methods=['POST'])
def generate_image_async_route():
    if not request.is_json:
        return jsonify({"success": False, "error": "Invalid request, JSON expected"}), 400
    
    params = request.get_json()
    #print(f"params: {params}")
        
    result = generate_single_output_file(params) # df_override can be used for testing
    #print(f"result: {result}")
    
    if(result['success'] == True):

        outputDict = session.get("outputList",{'id': [] ,'filename': [] })
        #print(f"outputDict: {outputDict}") #debug print(outputDict)

        config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == params['output_id']), None)
        output_dir = getattr(rl_data, config_item["output_dir_const"])
        filepath =  Path(output_dir) / Path(params['target_filename'])

        # Update outputList
        outputDict['filename'].append(str(filepath))
        outputDict['id'].append(params['output_id'])
    
    return jsonify(result)

# Optional: Route for PDF generation and download
@app.route('/download_pdf', methods=['GET'])
def generate_and_download_pdf_route():
    
    output_id = request.args.get('output_id')
    event_name_actual = request.args.get('event_name_actual')
    competitor_name_actual = request.args.get('competitor_name_actual')
    competitor_race_no_actual = request.args.get('competitor_race_no_actual')

    app.logger.warning(f"/download_pdf {event_name_actual} {competitor_name_actual}")

    runtimeVars = session.get('runtime', {}) # Get from session for this example
    outputVars = session.get('output_config', {})
    outputDict = session.get("outputList",{})

    pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == output_id), None)
    if not pdf_config_item:
        app.logger.error(f"Invalid PDF type requested: {output_id}")
        return "Invalid PDF type requested", 400
    
    html_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'html_info_comp'), None)
    if not html_config_item:
        app.logger.error(f"Invalid HTML Not found: {output_id}")
        return "Invalid HTML Not found", 400   
    
    if pdf_config_item['is_competitor_specific']:
        runtimeVars['competitorName'] = competitor_name_actual
        runtimeVars['competitorRaceNo'] = competitor_race_no_actual
        
    # Check if this type of output is enabled in general_config
    if( outputVars.get(pdf_config_item['id'], False) == False ):
        app.logger.error(f"Output type not enabled: {pdf_config_item['id']}")
        return "Invalid PDF type requested", 400

    # Skip if mode doesn't match (e.g., trying to generate generic in competitor mode, or vice-versa)
    if pdf_config_item['id'] == 'pdf_report_comp' and pdf_config_item['is_competitor_specific'] == False:
        app.logger.error(f"CompetitorAnalysis mode does not match output mode: {pdf_config_item['pdf_report_comp']} {pdf_config_item['is_competitor_specific']}")
        return "Invalid PDF type requested", 400
    
    # Skip if competitor is required but not found
    if pdf_config_item['id'] == 'pdf_report_generic' and pdf_config_item['is_competitor_specific'] == True:
        app.logger.error(f"Generic PDF mode does not match output mode: {pdf_config_item['pdf_report_generic']} {pdf_config_item['is_competitor_specific']}")
        return "Invalid PDF type requested", 400

    # --- Assume PNGs are all ready and available  ---
    if outputDict['filename']: # Only if PNGs were generated
        #app.logger.debug(f"foutputList['filename']: {outputDict['filename']}")

        event_name_slug = slugify(event_name_actual)
        if outputVars['competitorAnalysis'] and outputVars['pdf_report_comp']:
            pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_comp'), None)
            competitor_name_slug = slugify(runtimeVars['competitorName']) 
            pdf_filename = pdf_config_item['filename_template'].format(
                EVENT_NAME_SLUG=event_name_slug,
                COMPETITOR_NAME_SLUG=competitor_name_slug
            )
            
            html_info_comp_filepaths = html_config_item['filename_template'].format(
                EVENT_NAME_SLUG=event_name_slug,
                COMPETITOR_NAME_SLUG=competitor_name_slug
            )
            html_output_dir = getattr(rl_data, html_config_item["output_dir_const"])            
            html_info_comp_filepaths = Path(html_output_dir) / Path(html_info_comp_filepaths)           
            
        elif outputVars['competitorAnalysis'] == False and outputVars['pdf_report_generic']:
            pdf_config_item = next((item for item in OUTPUT_CONFIGS if item['id'] == 'pdf_report_generic'), None)
            pdf_filename = pdf_config_item['filename_template'].format(
                EVENT_NAME_SLUG=event_name_slug)
            html_info_comp_filepaths = None
            
        else:
            app.logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']} and {outputVars['pdf_report_comp']}")

        #app.logger.error(f"PDF filename {pdf_filename} and pdf_config_item {pdf_config_item}")

        if pdf_config_item:

            pdf_output_dir = getattr(rl_data, pdf_config_item["output_dir_const"])
            pdf_filepath = Path(pdf_output_dir) / Path(pdf_filename)

            if(MakeFullPdfReport(filepath=pdf_filepath,  outputDict=outputDict, html_filepath=html_info_comp_filepaths, competitorAnalysis=outputVars['competitorAnalysis'])==True):
                return send_file(pdf_filepath, as_attachment=True, mimetype='application/pdf')
            
        else:
            app.logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']} and {outputVars['pdf_report_comp']}")
    else:
        app.logger.error(f"No PDF configuration found for {outputVars['pdf_report_generic']}, {outputVars['pdf_report_comp']} and {outputDict['filename']} is empty")


# 3. User: View blog index (list of posts, searchable)
@app.route('/blog')
def blog_index():
    
    app.logger.warning(f"/blog")
    
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
            app.logger.error(f"Could not get signed URL for GCS image: {slug}/images/{filename}")
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
    app.logger.warning(f"/blog/{slug}")

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
            #app.logger.warning(f"You must log in to access this page.")

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
            #app.logger.warning(f"Login successful!")
            
            # Use the same scheme and host as the request
            return redirect(url_for('admin', _external=True, _scheme=request.scheme))
        else:
            app.logger.warning(f"Login unsuccessful!")
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
    
    for key in list(session.keys()):
        if not key.startswith('_'):
            app.logger.debug(f"Session Keys: {key}: {session[key]}")
 
    #clear the search results.
    session.pop('search_results', None)

    if 'search_results' in session:  
        app.logger.warning(f"Warning: After Pop: 'search_results': {session['search_results']}")

    return render_template("admin.html")


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
        redline_vis_generate_generic()

    return render_template("admin.html")

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
        blob = bucket.blob(str(rl_data.FEEDBACK_BLOB_FILEPATH))
        
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
    app.logger.debug(f"/admin/logs/download received")
    env_mode = os.environ.get('ENV_MODE', 'development')

    if env_mode == 'deploy':
        # --- GCS File Download ---
        if not rl_data.storage or not rl_data.BLOG_BUCKET_NAME:
            flash("GCS is not configured, cannot download log.", "danger")
            return redirect(url_for('view_logs'))
        try:
            log_date = datetime.utcnow().strftime('%Y-%m-%d')
            gcs_log_filename = f"logs/deploy/app_{log_date}.log"
            storage_client = rl_data.storage.Client()
            bucket = storage_client.bucket(rl_data.BLOG_BUCKET_NAME)
            blob = bucket.blob(gcs_log_filename)
            if not blob.exists():
                flash(f"GCS log file '{gcs_log_filename}' not found.", "warning")
                return redirect(url_for('view_logs'))
            log_stream = BytesIO(blob.download_as_bytes())
            return send_file(
                log_stream, as_attachment=True,
                download_name=f'activity_{log_date}.log',
                mimetype='text/plain'
            )
        except Exception as e:
            app.logger.error(f"Error downloading log from GCS: {e}", exc_info=True)
            flash(f"Error downloading log from GCS: {e}", "danger")
            return redirect(url_for('view_logs'))
    else:
        # --- Local File Download ---
        if os.path.exists(rl_data.LOG_FILE):
            return send_file(rl_data.LOG_FILE, as_attachment=True, download_name='activity_local.log')
        else:
            flash("Local log file not found.", "warning")
            return redirect(url_for('view_logs'))

@app.route('/admin/logs/clear', methods=['POST'])
@login_required
def clear_logs_route(): # Unified clear/rotate route
    app.logger.info(f"/admin/logs/clear POST received")
    message, category = rl_data.clear_or_rotate_logs() # Call the unified function
    flash(message, category)
    return redirect(url_for('view_logs'))

@app.route('/admin/logs/delete/<path:filename>', methods=['POST'])
@login_required
def delete_single_log(filename):
    """
    Handles the request to delete a single log file.
    The <path:filename> converter allows the filename to contain slashes,
    which is necessary for GCS blob paths.
    """
    #app.logger.warning(f"Received request to delete log file: {filename}")
    
    # The CSRF token is automatically validated by Flask-WTF for POST requests.
    
    success, message = rl_data.delete_log_file(filename)
    
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for('view_logs'))

@app.route('/admin/logs')
@login_required
def view_logs():
    app.logger.debug(f"/admin/logs received. Checking for logs...")
    
    import re
    ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    log_files_content = {}
    env_mode = os.environ.get('ENV_MODE', 'development')

    try:
        if env_mode == 'deploy':
            # --- (Your GCS logic remains unchanged) ---
            if not rl_data.storage or not rl_data.BLOG_BUCKET_NAME:
                log_files_content['error'] = "GCS is not configured on the server."
                app.logger.warning("GCS logging not configured, cannot view logs.")
            else:
                app.logger.info(f"Attempting to read logs from GCS bucket: {rl_data.BLOG_BUCKET_NAME}")
                storage_client = rl_data.storage.Client()
                bucket = storage_client.bucket(rl_data.BLOG_BUCKET_NAME)
                
                prefix_to_view = f"logs/deploy/app_"
                
                blobs = list(reversed(list((bucket.list_blobs(prefix=prefix_to_view)))))
                app.logger.info(f"Found {len(blobs)} log blob(s) in GCS with prefix '{prefix_to_view}'.")

                if not blobs:
                    log_files_content['info'] = f"No log files found with prefix '{prefix_to_view}' in GCS bucket '{rl_data.BLOG_BUCKET_NAME}'."
                else:
                    for blob in blobs:
                        app.logger.debug(f"Attempting to download blob: {blob.name}")
                        content = blob.download_as_text() 
                        clean_content = ANSI_ESCAPE_RE.sub('', content)
                        log_files_content[blob.name] = clean_content
                        
                        app.logger.info(f"Successfully read {len(content)} bytes from {blob.name}.")

        else:
            # --- MODIFIED: Read from Local File ---
            local_log_file_path = Path(rl_data.LOG_FILE)
            
            # Ensure the directory exists first
            local_log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If the main log file was deleted, touch it to recreate it as empty
            if not local_log_file_path.exists():
                local_log_file_path.touch()
                app.logger.info(f"Main log file '{local_log_file_path}' was missing. Recreated empty file.")

            # Now, read all .log and .log.* files in the directory
            log_directory = Path(rl_data.LOG_FILE_DIR)
            
            # Get all log files, sort them to show the main one first, then backups
            all_log_files = sorted(
                [f for f in log_directory.iterdir() if f.is_file() and str(f.name).startswith('activity.log')],
                key=lambda x: str(x.name)
            )

            if all_log_files:
                for log_file in all_log_files:
                    app.logger.info(f"Reading local log file: {log_file}")
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_contents = f.read()
                    log_files_content[log_file.name] = ANSI_ESCAPE_RE.sub('', log_contents)
            else:
                 log_files_content['info'] = "No log files found in the log directory."


    except Exception as e:
        # This will catch permissions errors and other issues
        app.logger.error(f"An error occurred while viewing logs: {e}", exc_info=True)
        log_files_content['error'] = f"An error occurred while trying to read logs: {e}"

    
    current_levels = rl_data.get_log_levels()
    
    return render_template('admin_logs.html', 
                           log_files_content=log_files_content, 
                           current_levels=current_levels,
                           env_mode=env_mode)

@app.route('/admin/logs/download/<path:gcs_blob_name>')
@login_required
def download_gcs_log(gcs_blob_name):
    # This route is specifically for downloading a GCS log file
    # You would generate links to this route in your admin_logs.html template
    app.logger.debug(f"Request to download GCS log: {gcs_blob_name}")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(rl_data.BLOG_BUCKET_NAME)
        blob = bucket.blob(gcs_blob_name)
        if not blob.exists():
            flash(f"Log file '{gcs_blob_name}' not found.", "danger")
            return redirect(url_for('view_logs'))
        
        log_stream = BytesIO(blob.download_as_bytes())
        return send_file(log_stream, as_attachment=True,
                         download_name=os.path.basename(gcs_blob_name),
                         mimetype='text/plain')
    except Exception as e:
        flash(f"Error downloading GCS log: {e}", "danger")
        return redirect(url_for('view_logs'))
    
    
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
            return render_template('admin/admin_post_blog.html', legend='New Blog Post', form_data=request.form) # Corrected template path likely

        # --- Slug Generation and Uniqueness Check ---
        original_post_slug = slugify(headline)
        post_slug = original_post_slug
        counter = 1
        slug_exists = True

        while slug_exists:
            if env_mode == 'deploy':
                slug_exists = rl_data.check_if_post_slug_exists_in_gcs(post_slug)
            else:
                local_blog_dir_for_check = rl_data.LOCAL_BLOG_DATA_DIR
                slug_exists = os.path.exists(os.path.join(local_blog_dir_for_check, post_slug))
            
            if slug_exists:
                app.logger.info(f"Slug '{post_slug}' already exists (mode: {env_mode}). Trying next.")
                post_slug = f"{original_post_slug}-{counter}"
                counter += 1
            else:
                break
        # --- End Slug Generation ---

        post_dir_local_path = None
        if env_mode != 'deploy':
            local_blog_dir = rl_data.LOCAL_BLOG_DATA_DIR
            post_dir_local_path = os.path.join(local_blog_dir, post_slug)
            try:
                os.makedirs(post_dir_local_path, exist_ok=True)
            except OSError as e:
                flash(f"Could not create local directory for post: {e}", "danger")
                app.logger.critical(f"OSError creating local directory {post_dir_local_path}: {e}")
                return render_template('admin/admin_post_blog.html', legend='New Blog Post', form_data=request.form)

        # --- Image Uploading ---
        # MODIFIED: Store image data as a list of dicts
        uploaded_images_data = [] 
        image_files_from_form = []

        for i in range(rl_data.MAX_IMAGES_PER_POST):
            image_file = request.files.get(f'image_{i}')
            if image_file and image_file.filename:
                image_files_from_form.append(image_file)
        
        if not image_files_from_form:
            flash('At least one image is required.', 'danger')
            if env_mode != 'deploy' and post_dir_local_path and os.path.exists(post_dir_local_path):
                shutil.rmtree(post_dir_local_path)
            return render_template('admin/admin_post_blog.html', legend='New Blog Post', form_data=request.form)

        image_save_failed = False
        for idx, image_file_to_save in enumerate(image_files_from_form):
            caption_text = request.form.get(f'caption_{idx}', '').strip()
            
            # NEW: Get 'show_in_gallery' status. Defaulting to True for now.
            # When your HTML form has <input type="checkbox" name="show_in_gallery_{idx}">,
            # you would change the line below to:
            show_in_gallery = f'show_in_gallery_{idx}' in request.form
            #show_in_gallery = True # <<< Placeholder: Default to True

            if not rl_data.allowed_file(image_file_to_save.filename):
                flash(f'Image {idx+1} ("{image_file_to_save.filename}") has an invalid file type. Not saved.', 'warning')
                continue

            #unique_base_name_no_ext = f"img_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{idx}"
            unique_base_name_no_ext, ext = os.path.splitext(image_file_to_save.filename)
            
            saved_basename_ext = None

            image_file_to_save.seek(0)

            if env_mode == 'deploy':
                saved_basename_ext = rl_data.save_uploaded_image_and_thumbnail_to_gcs(
                    post_slug, image_file_to_save, unique_base_name_no_ext
                )
            else:
                 saved_basename_ext = rl_data.save_uploaded_image_and_thumbnail(
                    post_slug, image_file_to_save, unique_base_name_no_ext
                )
            
            if saved_basename_ext:
                # MODIFIED: Append a dictionary to uploaded_images_data
                uploaded_images_data.append({
                    'filename': saved_basename_ext,
                    "caption": caption_text,
                    "show_in_gallery": show_in_gallery 
                })
            else:
                flash(f'Error saving Image {idx+1} ("{image_file_to_save.filename}"). Post creation aborted.', 'danger')
                image_save_failed = True
                break

        # MODIFIED: Check uploaded_images_data instead of uploaded_image_basenames
        if image_save_failed or not uploaded_images_data:
            if not uploaded_images_data and not image_save_failed:
                 flash('At least one valid image is required and must be successfully uploaded.', 'danger')
            
            app.logger.error(f"Image upload failed or no valid images for new post '{post_slug}'. Cleaning up.")
            if env_mode == 'deploy':
                app.logger.info(f"Attempting GCS cleanup for partially created post '{post_slug}' (if any images were uploaded).")
                # MODIFIED: Iterate through uploaded_images_data to get filenames for cleanup
                for img_data in uploaded_images_data: 
                    rl_data.delete_blog_image_and_thumbnail_from_gcs(post_slug, img_data['filename'])
            else:
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
            # MODIFIED: Use the new 'images' key with the list of dictionaries
            'images': uploaded_images_data, 
            'created_at': now_iso,
            'updated_at': now_iso,
            'published_at': published_at_iso,
            'is_featured': is_featured,
            'is_published': is_published_now,
            'view_count': 0,
            'slug': post_slug
        }
        # --- End Prepare Post Data ---

        # --- Save Config File (content.json) ---
        save_config_successful = False
        if env_mode == 'deploy':
            if rl_data.save_post_config_to_gcs(post_slug, post_data):
                save_config_successful = True
                flash('Blog post created successfully in GCS!', 'success')
            else:
                flash('Error saving blog post config to GCS. Images might have been uploaded. Check GCS.', 'danger')
        else: # Local mode
            try:
                with open(os.path.join(post_dir_local_path, 'content.json'), 'w', encoding='utf-8') as f:
                    json.dump(post_data, f, indent=4)
                save_config_successful = True
                flash('Blog post created successfully locally!', 'success')
            except IOError as e:
                flash(f'Error saving local content.json: {e}', 'danger')
                app.logger.critical(f"IOError saving local content.json for {post_slug}: {e}")
                if post_dir_local_path and os.path.exists(post_dir_local_path): shutil.rmtree(post_dir_local_path)

        if save_config_successful:
            return redirect(url_for('manage_blog_posts')) # Assuming blueprint or direct route name
        else:
            if env_mode != 'deploy' and post_dir_local_path and os.path.exists(post_dir_local_path):
                 shutil.rmtree(post_dir_local_path)
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
    
    post_data_from_storage = rl_data.get_post(slug) # Assumes this handles GCS/local

    if not post_data_from_storage:
        app.logger.error(f"Edit attempt for non-existent post '{slug}' in mode '{env_mode}'.")
        abort(404)

    # Work with a copy for modifications
    post_for_processing = dict(post_data_from_storage)

    # --- Normalize image data to the new 'images' list of dicts format ---
    if 'images' not in post_for_processing and 'image_filenames' in post_for_processing:
        app.logger.info(f"Post '{slug}' uses old image format. Converting to new 'images' structure for editing.")
        images_list = []
        filenames = post_for_processing.get('image_filenames', [])
        captions = post_for_processing.get('image_captions', [])
        for i, filename_item in enumerate(filenames):
            images_list.append({
                'filename': filename_item,
                "caption": captions[i] if i < len(captions) else "",
                "show_in_gallery": True # Default for old data
            })
        post_for_processing['images'] = images_list
        post_for_processing.pop('image_filenames', None) # Remove old keys
        post_for_processing.pop('image_captions', None)
    elif 'images' not in post_for_processing: # If no image keys at all (e.g. 'images' is not there, nor image_filenames)
        post_for_processing['images'] = []

    # Ensure all image dicts in 'images' have all keys (filename, caption, show_in_gallery)
    # This handles cases where 'images' might exist but be missing some sub-keys.
    normalized_images_temp = []
    for img_data in post_for_processing.get('images', []): # Iterate over the potentially modified list
        normalized_images_temp.append({
            'filename': img_data.get('filename'), # Should always exist if img_data itself exists
            "caption": img_data.get("caption", ""),
            "show_in_gallery": img_data.get("show_in_gallery", True) # Default to True if missing
        })
    post_for_processing['images'] = normalized_images_temp
    # --- End Image Data Normalization ---

    if request.method == 'POST':
        was_published_before_edit = post_for_processing.get('is_published', False)

        post_for_processing['headline'] = request.form.get('headline', post_for_processing['headline'])
        post_for_processing['text'] = request.form.get('content', post_for_processing['text'])
        post_for_processing['is_featured'] = 'is_featured' in request.form
        is_published_now = 'is_published' in request.form
        post_for_processing['is_published'] = is_published_now

        # --- Image Processing ---
        # original_images_from_storage now comes from the normalized post_for_processing['images'] at the start of the request
        # but before any POST modifications. We use what was loaded and normalized.
        # The `post_for_processing['images']` at this point is what we'll iterate over for existing images.
        
        final_images_data = [] # This will hold the new list of image dicts

        # 1. Process Existing Images: Keep or Delete, and Update Captions/ShowInGallery
        # Iterate based on the number of images present when the form was rendered.
        # This count should match the number of 'delete_image_{idx}', 'current_caption_{idx}' fields submitted.
        # We use the state of `post_for_processing['images']` as it was *before* this POST processing block.
        # However, since `post_data_from_storage` is the pristine version, let's use that to determine original images.
        # This is safer if `post_for_processing` was somehow mutated before this POST block but after normalization.
        
        # Re-normalize `post_data_from_storage` just for this section to get the initial list of images
        # This avoids using `post_for_processing` which might be partially updated by form fields above.
        initial_images_for_processing = []
        if 'images' not in post_data_from_storage and 'image_filenames' in post_data_from_storage:
            filenames_orig = post_data_from_storage.get('image_filenames', [])
            captions_orig = post_data_from_storage.get('image_captions', [])
            for i, fn_orig in enumerate(filenames_orig):
                initial_images_for_processing.append({
                    'filename': fn_orig,
                    "caption": captions_orig[i] if i < len(captions_orig) else "",
                    "show_in_gallery": True
                })
        elif 'images' in post_data_from_storage:
            for img_d in post_data_from_storage.get('images', []):
                 initial_images_for_processing.append({
                    'filename': img_d.get('filename'),
                    "caption": img_d.get("caption", ""),
                    "show_in_gallery": img_d.get("show_in_gallery", True)
                })


        for i, existing_image_data in enumerate(initial_images_for_processing):
            existing_filename = existing_image_data['filename']
            if not existing_filename: continue # Should not happen if data is clean

            if request.form.get(f'delete_image_{i}'):
                # Image marked for deletion
                if env_mode == 'deploy':
                    rl_data.delete_blog_image_and_thumbnail_from_gcs(slug, existing_filename)
                else:
                    rl_data.delete_blog_image_and_thumbnail(slug, existing_filename) # Local deletion
                app.logger.info(f"Deleted image '{existing_filename}' for post '{slug}' (mode: {env_mode}).")
            else:
                # Image is kept, update its details
                updated_caption = request.form.get(f'current_caption_{i}', existing_image_data['caption']).strip()
                # For checkbox: if 'current_show_in_gallery_{i}' is in form, it's checked (True), else False.
                updated_show_in_gallery = f'current_show_in_gallery_{i}' in request.form
                
                final_images_data.append({
                    'filename': existing_filename,
                    "caption": updated_caption,
                    "show_in_gallery": updated_show_in_gallery
                })

        # 2. Handle New Image Uploads
        for i in range(rl_data.MAX_IMAGES_PER_POST): # MAX_IMAGES_PER_POST should be defined in rl_data
            if len(final_images_data) >= rl_data.MAX_IMAGES_PER_POST:
                if request.files.get(f'new_image_{i}') and request.files.get(f'new_image_{i}').filename:
                    flash(f'Maximum of {rl_data.MAX_IMAGES_PER_POST} images reached. Additional uploads ignored.', 'warning')
                break

            image_file = request.files.get(f'new_image_{i}')
            new_caption_text = request.form.get(f'new_caption_{i}', '').strip()
            # For new images, 'show_in_gallery' is True if checked, False otherwise.
            new_show_in_gallery = f'new_show_in_gallery_{i}' in request.form

            if image_file and image_file.filename:
                if not rl_data.allowed_file(image_file.filename):
                    flash(f'New Image (slot {i+1}) "{image_file.filename}" has an invalid file type. Not saved.', 'warning')
                    continue

                #want to stick with the original filename
                #unique_base_name = f"img_edit_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{i}"
                unique_base_name, ext = os.path.splitext(image_file.filename)
                saved_image_basename = None
                image_file.seek(0) # Reset stream just in case

                app.logger.debug(f"new image {image_file.filename} -> image_basename: {unique_base_name} ext: {ext}")

                if env_mode == 'deploy':
                    saved_image_basename = rl_data.save_uploaded_image_and_thumbnail_to_gcs(
                        slug, image_file, unique_base_name
                    )
                else:
                    saved_image_basename = rl_data.save_uploaded_image_and_thumbnail( # Local save
                        slug, image_file, unique_base_name
                    )

                if saved_image_basename:
                    final_images_data.append({
                        'filename': saved_image_basename,
                        "caption": new_caption_text,
                        "show_in_gallery": new_show_in_gallery
                    })
                    app.logger.info(f"Saved new image '{saved_image_basename}' for post '{slug}' (mode: {env_mode}).")
                else:
                    flash(f'Error saving new Image (slot {i+1}) "{image_file.filename}". Check logs.', 'warning')
        # --- End Image Processing ---

        post_for_processing['images'] = final_images_data # Update with the new list of dicts
        # Remove old keys if they somehow persisted (should be removed by normalization if they existed)
        post_for_processing.pop('image_filenames', None)
        post_for_processing.pop('image_captions', None)

        if not post_for_processing['images']: # Check if the list is empty
            flash('A post must have at least one image. Please add an image.', 'danger')
            # Repopulate form with current (failed) submission state
            return render_template('admin_post_blog.html', 
                                   legend=f'Edit Post: "{post_data_from_storage["headline"]}"', # Use original headline for legend
                                   post=post_for_processing, # Pass the current state of post_for_processing
                                   form_data=request.form) # Pass raw form data for general field repopulation

        # --- Timestamps and Published_at Logic ---
        now_iso = datetime.now().isoformat()
        post_for_processing['updated_at'] = now_iso

        if is_published_now and not was_published_before_edit:
            post_for_processing['published_at'] = now_iso
        elif is_published_now and was_published_before_edit:
            if not post_for_processing.get('published_at'):
                post_for_processing['published_at'] = post_for_processing.get('created_at', now_iso)
        # --- End Timestamps ---

        # Save the updated post_for_processing data
        save_successful = False
        if env_mode == 'deploy':
            # save_post_to_gcs should now expect post_for_processing['images']
            save_successful = rl_data.save_post_config_to_gcs(slug, post_for_processing) # Assuming save_post_config_to_gcs
        else:
            local_post_dir_path = os.path.join(rl_data.LOCAL_BLOG_DATA_DIR, slug)
            if not os.path.exists(local_post_dir_path): os.makedirs(local_post_dir_path, exist_ok=True)
            try:
                with open(os.path.join(local_post_dir_path, 'content.json'), 'w', encoding='utf-8') as f:
                    json.dump(post_for_processing, f, indent=4)
                save_successful = True
            except IOError as e:
                app.logger.critical(f"Error writing local content.json for {slug}: {e}")
                flash(f'Error saving post data locally: {e}', 'danger')

        if save_successful:
            flash('Blog post updated successfully!', 'success')
            return redirect(url_for('manage_blog_posts')) # Adjust if not using blueprint
        else:
            flash('Error saving post data. Check logs.', 'danger')
            # Fall through to render form again with submitted data (post_for_processing should have it)

    # --- GET request or if POST had issues and fell through ---
    # `post_for_processing` at this point (for GET) has been normalized.
    # For POST fall-through, it contains the data from the failed POST attempt.
    form_data_for_template = { # Primarily for non-image fields if not directly using post_for_processing in template
        'headline': post_for_processing['headline'],
        'content': post_for_processing['text'],
        'is_featured': post_for_processing.get('is_featured', False),
        'is_published': post_for_processing.get('is_published', True)
    }
    return render_template('admin_post_blog.html',
                           legend=f'Edit Post: "{post_for_processing["headline"]}"',
                           post=post_for_processing, # This contains post_for_processing['images']
                           form_data=form_data_for_template) # Or just use request.form if POST failed


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
                shutil.rmtree(post_dir, onexc=rl_data.handle_rm_error) # This deletes content.json and all images/thumbnails
                flash(f'Post "{slug}" and all its images deleted successfully.', 'success')
            except OSError as e:
                flash(f'Error deleting post (Content deleted, but dir remains) "{slug}": {e}', 'danger')
                app.logger.critical(f"Error deleting directory {post_dir}: {e}")
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
                logger.error(f"Sync function reported partial success or issues.")
            else:
                flash('Blog post sync to GCS failed to initiate or encountered errors. Check logs.', 'danger')
                logger.critical(f"Sync function reported failure.")
                
        except Exception as e:
            flash(f'An unexpected error occurred during the sync process: {e}', 'danger')
            logger.critical(f"Exception during sync call: {e}", exc_info=True)
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

   