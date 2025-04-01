from flask import Flask, jsonify, render_template, request, send_file, Response
from flask_caching import Cache
import subprocess
import tempfile
import os
import uuid
import re
import threading
import time
import json
import logging
import hashlib
from functools import lru_cache

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static')

cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() in ['true', '1', 'yes', 'y']
app.debug = DEBUG_MODE
app.logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
app.logger.info(f"Application running in {'DEBUG' if DEBUG_MODE else 'PRODUCTION'} mode")

TEMP_DIR = os.environ.get('TEMP_DIR', tempfile.gettempdir())
JOB_TIMEOUT = int(os.environ.get('JOB_TIMEOUT', 300))

os.makedirs(TEMP_DIR, exist_ok=True)
app.logger.info(f"Using temporary directory: {TEMP_DIR}")
app.logger.info(f"Job cleanup timeout: {JOB_TIMEOUT}s")

JOB_DATA_FILE = os.path.join(TEMP_DIR, 'conversion_jobs.json')

conversion_progress = {}
completed_files = {}

COMPLETED_FILES_FILE = os.path.join(TEMP_DIR, 'completed_files.json')

os.makedirs(os.path.dirname(COMPLETED_FILES_FILE), exist_ok=True)

def load_saved_jobs():
    """
    Load previously saved conversion jobs from disk.
    
    Returns:
        dict: Dictionary of saved jobs or empty dict if none found
    """
    if os.path.exists(JOB_DATA_FILE):
        try:
            with open(JOB_DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            app.logger.error(f"Error loading saved jobs: {str(e)}")
    return {}

_last_jobs_hash = None

def get_job_cache_key():
    """
    Generate a cache key based on the current job state to prevent excessive writes.
    
    Returns:
        str: MD5 hash of the jobs state
    """
    return hashlib.md5(json.dumps(conversion_progress, sort_keys=True).encode()).hexdigest()

def save_jobs():
    """
    Save current conversion jobs to disk if state has changed.
    Only writes to disk when necessary to reduce I/O.
    Force save when _last_jobs_hash is None (first time or after modifications).
    """
    global _last_jobs_hash
    
    current_hash = get_job_cache_key()

    if _last_jobs_hash is None:
        app.logger.debug("First save or important state change, forcing save")
    elif _last_jobs_hash == current_hash:
        app.logger.debug("No change in job state, skipping save")
        return
        
    try:
        app.logger.debug(f"Saving {len(conversion_progress)} jobs to {JOB_DATA_FILE}")
        with open(JOB_DATA_FILE, 'w') as f:
            json.dump(conversion_progress, f)
        _last_jobs_hash = current_hash
        app.logger.debug("Jobs saved successfully")
    except Exception as e:
        app.logger.error(f"Error saving jobs: {str(e)}")

def load_completed_files():
    """
    Load previously saved completed files from disk.
    
    Returns:
        dict: Dictionary of completed files or empty dict if none found
    """
    if os.path.exists(COMPLETED_FILES_FILE):
        try:
            with open(COMPLETED_FILES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            app.logger.error(f"Error loading completed files: {str(e)}")
    return {}
    

def get_epub_metadata(input_path):
    """
    Extract author and title from epub file for better naming.
    
    Args:
        input_path (str): Path to the EPUB file
        
    Returns:
        tuple: (author, title) strings formatted for filename use
    """
    try:
        metadata = subprocess.check_output(
            ["ebook-meta", input_path],
            text=True, stderr=subprocess.STDOUT
        ).strip()
        
        author = "unknown"
        title = "ebook"
        
        for line in metadata.split('\n'):
            if line.startswith('Title'):
                title = line.split(':', 1)[1].strip()
            elif line.startswith('Author(s)'):
                author = line.split(':', 1)[1].strip()
                if ',' in author:
                    author = author.split(',')[0].strip()
                if '(' in author:
                    author = author.split('(')[0].strip()
                    
        author = re.sub(r'[^\w\s-]', '', author).strip().replace(' ', '_').lower()
        title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_').lower()
        
        return author, title
    except Exception as e:
        app.logger.error(f"Error extracting metadata: {str(e)}")
        return "unknown", "ebook"

def build_conversion_command(input_path, output_path, params):
    """
    Build the command for ebook conversion with the given parameters.
    
    Args:
        input_path (str): Path to input EPUB file
        output_path (str): Path for output PDF file
        params (dict): Conversion parameters
        
    Returns:
        list: Command list for subprocess execution
    """
    command = [
        "ebook-convert",
        input_path,
        output_path,
        "--verbose",
        "--debug",
        f"--input-profile={params['input_profile']}",
        f"--output-profile={params['output_profile']}",
        f"--base-font-size={params['base_font_size']}",
        f"--pdf-default-font-size={params['default_font_size']}",
        f"--pdf-mono-font-size={params['mono_font_size']}",
        f"--custom-size={params['custom_size']}",
        f"--unit={params['unit']}",
        f"--pdf-sans-family={params['pdf_sans_family']}",
        f"--pdf-serif-family={params['pdf_serif_family']}",
        f"--pdf-mono-family={params['pdf_mono_family']}",
        f"--pdf-standard-font={params['pdf_standard_font']}",
        f"--pdf-page-margin-left={params['pdf_page_margin_left']}",
        f"--pdf-page-margin-right={params['pdf_page_margin_right']}",
        f"--pdf-page-margin-top={params['pdf_page_margin_top']}",
        f"--pdf-page-margin-bottom={params['pdf_page_margin_bottom']}",
        f"--change-justification={params['change_justification']}"
    ]

    if params.get("embed_all_fonts", False):
        command.append("--embed-all-fonts")
    if params.get("subset_embedded_fonts", False):
        command.append("--subset-embedded-fonts")
    if params.get("unsmarten_punctuation", False):
        command.append("--unsmarten-punctuation")
    if params.get("preserve_cover_aspect_ratio", False):
        command.append("--preserve-cover-aspect-ratio")
        
    return command

_last_completed_files_hash = None

def get_completed_files_cache_key():
    """
    Generate a cache key based on the completed files state to prevent excessive writes.
    
    Returns:
        str: MD5 hash of the completed files state
    """
    return hashlib.md5(json.dumps(completed_files, sort_keys=True).encode()).hexdigest()

def save_completed_files():
    """
    Save current completed files to disk if state has changed.
    Only writes to disk when necessary to reduce I/O.
    """
    global _last_completed_files_hash
    
    current_hash = get_completed_files_cache_key()
    if _last_completed_files_hash == current_hash:
        app.logger.debug("No change in completed files state, skipping save")
        return
        
    try:
        app.logger.debug(f"Saving {len(completed_files)} entries to {COMPLETED_FILES_FILE}")
        with open(COMPLETED_FILES_FILE, 'w') as f:
            json.dump(completed_files, f)
        _last_completed_files_hash = current_hash
        app.logger.debug(f"Saved {len(completed_files)} entries to {COMPLETED_FILES_FILE}")
    except Exception as e:
        app.logger.error(f"Error saving completed files: {str(e)}")

def job_cleaner():
    """
    Background thread function that cleans up completed/failed jobs after timeout.
    Removes temporary files and job records to free up disk space.
    """
    while True:
        try:
            current_time = time.time()
            jobs_to_cleanup = []
            
            for job_id, job_data in list(conversion_progress.items()):
                if 'completed_time' in job_data and job_data['status'] in ['completed', 'failed']:
                    if current_time - job_data['completed_time'] >= JOB_TIMEOUT:
                        jobs_to_cleanup.append(job_id)
            
            for job_id in jobs_to_cleanup:
                app.logger.debug(f"Cleaning up job {job_id} after timeout")
                try:
                    input_path = conversion_progress[job_id].get('input_path')
                    output_path = conversion_progress[job_id].get('output_path')
                    
                    if input_path and os.path.exists(input_path):
                        os.remove(input_path)
                        app.logger.debug(f"Deleted temporary input file: {input_path}")
                    
                    if output_path and os.path.exists(output_path):
                        os.remove(output_path)
                        app.logger.debug(f"Deleted temporary output file: {output_path}")

                except Exception as e:
                    app.logger.error(f"Error while cleaning up files for job {job_id}: {str(e)}")
                
                del conversion_progress[job_id]
                save_jobs()
                del completed_files[job_id]
                save_completed_files()
                
        except Exception as e:
            app.logger.error(f"Error in job_cleaner: {str(e)}")

        time.sleep(30)

conversion_progress = load_saved_jobs()
completed_files = load_completed_files()

_last_jobs_hash = get_job_cache_key() if conversion_progress else None
_last_completed_files_hash = get_completed_files_cache_key() if completed_files else None
app.logger.debug(f"Initialized with {len(conversion_progress)} jobs and {len(completed_files)} completed files")

cleaner_thread = threading.Thread(target=job_cleaner)
cleaner_thread.daemon = True
cleaner_thread.start()
app.logger.info("Started job cleaner thread")

def get_env_params(prefix, defaults):
    """
    Load parameters from environment variables with fallback to defaults.
    
    Args:
        prefix (str): Environment variable prefix
        defaults (dict): Default values for parameters
        
    Returns:
        dict: Parameters with values from environment or defaults
    """
    params = {}
    for key, default_value in defaults.items():
        env_key = f"{prefix}_{key.upper()}"
        
        if isinstance(default_value, bool):
            params[key] = os.environ.get(env_key, str(default_value)).lower() in ['true', '1', 'yes', 'y']
        else:
            params[key] = os.environ.get(env_key, default_value)
    
    return params

DEFAULT_PARAMS = {
    "input_profile": "default",
    "output_profile": "generic_eink_hd",
    "base_font_size": "12",
    "default_font_size": "18",
    "mono_font_size": "16",
    "embed_all_fonts": True,
    "subset_embedded_fonts": True,
    "unsmarten_punctuation": True,
    "custom_size": "1620x2160",
    "unit": "devicepixel",
    "pdf_sans_family": "IBM Plex Sans",
    "pdf_serif_family": "IBM Plex Serif",
    "pdf_mono_family": "IBM Plex Mono",
    "pdf_standard_font": "serif",
    "pdf_page_margin_left": "72",
    "pdf_page_margin_right": "20",
    "pdf_page_margin_top": "20",
    "pdf_page_margin_bottom": "20",
    "preserve_cover_aspect_ratio": True,
    "change_justification": "justify"
}

REMARKABLE_PARAMS = get_env_params("REMARKABLE", DEFAULT_PARAMS.copy())

BOOX_AIR_4C_DEFAULT = {
    "input_profile": "default",
    "output_profile": "generic_eink_hd",
    "base_font_size": "12",
    "default_font_size": "16", 
    "mono_font_size": "14",
    "embed_all_fonts": True,
    "subset_embedded_fonts": True,
    "unsmarten_punctuation": True,
    "custom_size": "1860x2480",
    "unit": "devicepixel",
    "pdf_sans_family": "IBM Plex Sans",
    "pdf_serif_family": "IBM Plex Serif",
    "pdf_mono_family": "IBM Plex Mono",
    "pdf_standard_font": "serif",
    "pdf_page_margin_left": "72",
    "pdf_page_margin_right": "20",
    "pdf_page_margin_top": "20",
    "pdf_page_margin_bottom": "20",
    "preserve_cover_aspect_ratio": True,
    "change_justification": "justify"
}

BOOX_AIR_4C_PARAMS = get_env_params("BOOX_AIR_4C", BOOX_AIR_4C_DEFAULT)

@cache.memoize(timeout=60)
def get_calibre_version():
    """
    Get and cache Calibre version to avoid repeated calls.
    
    Returns:
        str: Calibre version string or "Unknown" on error
    """
    try:
        return subprocess.check_output(["ebook-convert", "--version"], 
                                    text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e:
        app.logger.error(f"Error checking Calibre version: {str(e)}")
        return "Unknown"

def update_job_status(job_id, status=None, progress=None, message=None, error_details=None, completed_time=None):
    """
    Update job status with the given parameters.
    Only updates fields that are provided and only saves on significant status changes.
    
    Args:
        job_id (str): ID of the job to update
        status (str, optional): New job status
        progress (int, optional): Progress percentage (0-100)
        message (str, optional): Status message
        error_details (str, optional): Error information
        completed_time (float, optional): Timestamp of job completion
    """
    if job_id not in conversion_progress:
        return
        
    if status is not None:
        conversion_progress[job_id]['status'] = status
    if progress is not None:
        conversion_progress[job_id]['progress'] = progress
    if message is not None:
        conversion_progress[job_id]['message'] = message
    if error_details is not None:
        conversion_progress[job_id]['error_details'] = error_details
    if completed_time is not None:
        conversion_progress[job_id]['completed_time'] = completed_time
    
    if status in ['completed', 'failed', 'running'] or progress == 100:
        save_jobs()

def run_conversion(command, job_id, input_path, output_path):
    """
    Run the conversion process for an EPUB file.
    Executes the conversion command, tracks progress, and updates job status.
    
    Args:
        command (list): Command to execute
        job_id (str): Job identifier
        input_path (str): Path to input EPUB file
        output_path (str): Path for output PDF file
    """
    try:
        app.logger.info(f"Starting conversion job {job_id}")
        app.logger.debug(f"Command: {' '.join(command)}")
        app.logger.debug(f"Input path: {input_path}")
        app.logger.debug(f"Output path: {output_path}")
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file {input_path} does not exist")
        
        file_size = os.path.getsize(input_path)
        app.logger.debug(f"Input file size: {file_size}")
        if file_size == 0:
            raise ValueError("Input file is empty")
            
        calibre_version = get_calibre_version()
        app.logger.debug(f"Calibre version: {calibre_version}")
        
        author, title = get_epub_metadata(input_path)
        
        conversion_progress[job_id] = {
            'status': 'running', 
            'progress': 1, 
            'message': 'Running conversion...',
            'input_path': input_path,
            'output_path': output_path,
            'detailed_logs': [],
            'author': author,
            'title': title
        }
        save_jobs()
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        progress_pattern = re.compile(r'(\d+)%')
        full_output = []
        last_save_time = time.time()
        batch_size = 10
        lines_since_save = 0
        save_interval = 2.0
        
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            app.logger.debug(f"Process output: {line}")
            full_output.append(line)
            conversion_progress[job_id]['detailed_logs'].append(line)
            lines_since_save += 1
            
            match = progress_pattern.search(line)
            if match:
                progress = int(match.group(1))
                update_job_status(job_id, progress=progress, message=line)
            else:
                conversion_progress[job_id]['message'] = line
            
            current_time = time.time()
            if lines_since_save >= batch_size and current_time - last_save_time >= save_interval:
                save_jobs()
                last_save_time = current_time
                lines_since_save = 0
        
        app.logger.debug("Waiting for process to complete...")
        process.wait()
        returncode = process.returncode
        app.logger.debug(f"Process completed with return code: {returncode}")
        
        if returncode == 0:
            app.logger.info(f"Conversion job {job_id} completed successfully")
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                app.logger.debug(f"Output file exists: {os.path.exists(output_path)}")
                app.logger.debug(f"Output file size: {os.path.getsize(output_path)}")
                
                if 'author' in conversion_progress[job_id] and 'title' in conversion_progress[job_id]:
                    author = conversion_progress[job_id]['author']
                    title = conversion_progress[job_id]['title']
                    completed_files[job_id] = {
                        'path': output_path,
                        'author': author,
                        'title': title
                    }
                else:
                    completed_files[job_id] = {'path': output_path}
                save_completed_files()
                
                update_job_status(
                    job_id, 
                    status='completed',
                    progress=100,
                    message='Conversion completed successfully!',
                    completed_time=time.time()
                )
            else:
                app.logger.error(f"Output file does not exist despite successful return code!")
                update_job_status(
                    job_id,
                    status='failed',
                    message='Conversion failed: Output file not created!',
                    completed_time=time.time()
                )
        else:
            app.logger.error(f"Conversion job {job_id} failed with return code {returncode}")
            error_details = '\n'.join(full_output[-10:]) if full_output else "No output captured"
            app.logger.error(f"Error details: {'\n'.join(full_output)}")
            
            update_job_status(
                job_id,
                status='failed',
                message=f'Conversion failed with code {returncode}! Check logs for details.',
                error_details=error_details,
                completed_time=time.time()
            )
        
        save_jobs()
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        app.logger.error(f"Exception in conversion job {job_id}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        
        update_job_status(
            job_id,
            status='failed',
            message=error_msg,
            error_details=error_msg,
            completed_time=time.time()
        )
        
        save_jobs()

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main route for the web interface.
    Handles both GET (display form) and POST (process upload) requests.
    
    Returns:
        Response: Rendered template or redirect
    """
    if request.method == "POST":
        app.logger.info("POST request received")
        
        if 'epub_file' not in request.files:
            app.logger.error("No file part in the request")
            return "No file part", 400
            
        epub_file = request.files["epub_file"]
        if not epub_file or epub_file.filename == "":
            app.logger.error("No file selected")
            return "No file selected", 400
            
        if not epub_file.filename.lower().endswith('.epub'):
            app.logger.error(f"Invalid file extension: {epub_file.filename}")
            return "Only EPUB files are supported", 400
            
        if request.content_length > 100 * 1024 * 1024:
            app.logger.error(f"File too large: {request.content_length / (1024*1024):.2f}MB")
            return "File size exceeds the 100MB limit", 400
        
        app.logger.info(f"File uploaded: {epub_file.filename}")
        
        job_id = str(uuid.uuid4())
        app.logger.info(f"Created job ID: {job_id}")
        
        with tempfile.NamedTemporaryFile(suffix=".epub", dir=TEMP_DIR, delete=False) as input_tmp_file, \
             tempfile.NamedTemporaryFile(suffix=".pdf", dir=TEMP_DIR, delete=False) as output_tmp_file:

            input_path = input_tmp_file.name
            output_path = output_tmp_file.name
            
            app.logger.debug(f"Created temporary files: input={input_path}, output={output_path}")

            epub_file.save(input_path)
            app.logger.debug(f"Saved uploaded file to {input_path}")

            device_profile = request.form.get("device_profile")
            app.logger.info(f"Selected device profile: {device_profile}")
            
            if device_profile == "reMarkable":
                params = REMARKABLE_PARAMS
            elif device_profile == "boox_air_4c":
                params = BOOX_AIR_4C_PARAMS
            else:
                app.logger.info("Using user-defined parameters")
                params = {
                    "input_profile": request.form.get("input_profile", DEFAULT_PARAMS["input_profile"]),
                    "output_profile": request.form.get("output_profile", DEFAULT_PARAMS["output_profile"]),
                    "base_font_size": request.form.get("base_font_size", DEFAULT_PARAMS["base_font_size"]),
                    "default_font_size": request.form.get("default_font_size", DEFAULT_PARAMS["default_font_size"]),
                    "mono_font_size": request.form.get("mono_font_size", DEFAULT_PARAMS["mono_font_size"]),
                    "embed_all_fonts": "embed_all_fonts" in request.form,
                    "subset_embedded_fonts": "subset_embedded_fonts" in request.form,
                    "unsmarten_punctuation": "unsmarten_punctuation" in request.form,
                    "custom_size": request.form.get("custom_size", DEFAULT_PARAMS["custom_size"]),
                    "unit": request.form.get("unit", DEFAULT_PARAMS["unit"]),
                    "pdf_sans_family": request.form.get("pdf_sans_family", DEFAULT_PARAMS["pdf_sans_family"]),
                    "pdf_serif_family": request.form.get("pdf_serif_family", DEFAULT_PARAMS["pdf_serif_family"]),
                    "pdf_mono_family": request.form.get("pdf_mono_family", DEFAULT_PARAMS["pdf_mono_family"]),
                    "pdf_standard_font": request.form.get("pdf_standard_font", DEFAULT_PARAMS["pdf_standard_font"]),
                    "pdf_page_margin_left": request.form.get("pdf_page_margin_left", DEFAULT_PARAMS["pdf_page_margin_left"]),
                    "pdf_page_margin_right": request.form.get("pdf_page_margin_right", DEFAULT_PARAMS["pdf_page_margin_right"]),
                    "pdf_page_margin_top": request.form.get("pdf_page_margin_top", DEFAULT_PARAMS["pdf_page_margin_top"]),
                    "pdf_page_margin_bottom": request.form.get("pdf_page_margin_bottom", DEFAULT_PARAMS["pdf_page_margin_bottom"]),
                    "preserve_cover_aspect_ratio": "preserve_cover_aspect_ratio" in request.form,
                    "change_justification": request.form.get("change_justification", DEFAULT_PARAMS["change_justification"])
                }
                
                app.logger.debug(f"Parameters: {params}")

            command = build_conversion_command(input_path, output_path, params)
                
            app.logger.debug(f"Final command: {' '.join(command)}")

            app.logger.info(f"Starting conversion thread for job {job_id}")

            author, title = get_epub_metadata(input_path)
            
            conversion_progress[job_id] = {
                'status': 'starting', 
                'progress': 0, 
                'message': 'Starting conversion...',
                'input_path': input_path,
                'output_path': output_path,
                'detailed_logs': [],
                'author': author,
                'title': title
            }
            save_jobs()

            thread = threading.Thread(
                target=run_conversion, 
                args=(command, job_id, input_path, output_path)
            )
            thread.daemon = True
            thread.start()
            
            time.sleep(0.2)  
            
            app.logger.info(f"Redirecting to progress page for job {job_id}")
            return render_template("progress.html", job_id=job_id)

    app.logger.info("Rendering index page")
    return render_template("index.html", default_params=DEFAULT_PARAMS)

@app.route("/progress/<job_id>")
def progress(job_id):
    """
    Server-sent events endpoint for progress updates.
    Streams job status updates to the client.
    
    Args:
        job_id (str): Job identifier
        
    Returns:
        Response: Server-sent events stream
    """
    app.logger.info(f"SSE connection established for job {job_id}")

    def generate():
        global conversion_progress
        if job_id not in conversion_progress:
            app.logger.debug(f"Job {job_id} not in memory, trying to load from disk")
            disk_jobs = load_saved_jobs()
            if job_id in disk_jobs:
                app.logger.info(f"Found job {job_id} in saved jobs file, reloading")
                conversion_progress.update(disk_jobs)
        
        if job_id not in conversion_progress and job_id not in completed_files:
            app.logger.warning(f"Job {job_id} not found in active or completed jobs")
            error_data = {
                'status': 'failed',
                'message': 'Job not found',
                'progress': 0,
                'error_details': 'Der Konvertierungsauftrag wurde nicht gefunden. Dies kann passieren, wenn:\n- Die Seite neu geladen wurde\n- Der Server neu gestartet wurde\n- Der Auftrag bereits abgeschlossen oder abgelaufen ist\n\nBitte versuche es erneut mit einer neuen Konvertierung.'
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            return
        
        if job_id in completed_files and job_id not in conversion_progress:
            file_info = completed_files[job_id]
            output_path = file_info['path'] if isinstance(file_info, dict) else file_info
            
            if os.path.exists(output_path):
                app.logger.info(f"Found completed job {job_id} in completed_files")
                
                completed_data = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Conversion completed successfully!',
                }
                
                if isinstance(file_info, dict):
                    if 'author' in file_info and 'title' in file_info:
                        completed_data['author'] = file_info['author']
                        completed_data['title'] = file_info['title']
                
                yield f"data: {json.dumps(completed_data)}\n\n"
                return
            
        connection_lost = False
        retry_count = 0
        max_retries = 30
        
        while True:
            if job_id in conversion_progress:
                connection_lost = False
                retry_count = 0
                data = conversion_progress[job_id]
                app.logger.debug(f"Sending progress update for job {job_id}: {data['status']}, {data['progress']}%")
                
                if 'detailed_logs' in data and len(data['detailed_logs']) > 100:
                    trimmed_data = data.copy()
                    trimmed_data['detailed_logs'] = data['detailed_logs'][-100:]
                    yield f"data: {json.dumps(trimmed_data)}\n\n"
                else:
                    yield f"data: {json.dumps(data)}\n\n"
                
                if data['status'] in ['completed', 'failed']:
                    app.logger.info(f"Job {job_id} {data['status']}")
                    break
            elif job_id in completed_files:
                file_info = completed_files[job_id]
                output_path = file_info['path'] if isinstance(file_info, dict) else file_info
                
                if os.path.exists(output_path):
                    app.logger.info(f"Job {job_id} completed and found in completed_files")
                    
                    completed_data = {
                        'status': 'completed',
                        'progress': 100,
                        'message': 'Conversion completed successfully!',
                    }
                    
                    if isinstance(file_info, dict):
                        if 'author' in file_info and 'title' in file_info:
                            completed_data['author'] = file_info['author']
                            completed_data['title'] = file_info['title']
                    
                    yield f"data: {json.dumps(completed_data)}\n\n"
                    break
            else:
                if not connection_lost:
                    app.logger.warning(f"Connection to job {job_id} lost, attempting to reconnect")
                    connection_lost = True
                
                retry_count += 1
                if retry_count > max_retries:
                    app.logger.warning(f"Maximum reconnection attempts reached for job {job_id}")
                    error_data = {
                        'status': 'failed',
                        'message': 'Connection lost',
                        'progress': 0,
                        'error_details': 'Die Verbindung zum Server wurde unterbrochen. Falls die Konvertierung abgeschlossen wurde, sollte die PDF automatisch erscheinen.'
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    break
            
            time.sleep(0.5)
    
    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/download/<job_id>")
def download(job_id):
    """
    File download endpoint for completed conversions.
    
    Args:
        job_id (str): Job identifier
        
    Returns:
        Response: File download or error message
    """
    app.logger.info(f"Download requested for job {job_id}")
    global conversion_progress, completed_files
    
    app.logger.debug(f"Job ID {job_id} in conversion_progress: {job_id in conversion_progress}")
    app.logger.debug(f"Job ID {job_id} in completed_files: {job_id in completed_files}")
    if job_id not in conversion_progress and job_id not in completed_files:
        app.logger.debug(f"Job {job_id} not in memory, trying to load from disk")
        disk_jobs = load_saved_jobs()
        disk_completed = load_completed_files()
        
        if job_id in disk_jobs:
            app.logger.info(f"Found job {job_id} in saved jobs file, reloading")
            conversion_progress.update(disk_jobs)
        
        if job_id in disk_completed:
            app.logger.info(f"Found job {job_id} in completed files, reloading")
            completed_files.update(disk_completed)
    
    if job_id in conversion_progress:
        job_data = conversion_progress[job_id]
        app.logger.debug(f"Job data in conversion_progress: {job_data}")
        
        if 'status' in job_data:
            app.logger.debug(f"Job status: {job_data['status']}")
        
        if 'output_path' in job_data:
            output_path = job_data['output_path']
            app.logger.debug(f"Output path from conversion_progress: {output_path}")
            app.logger.debug(f"File exists: {os.path.exists(output_path)}")
            
            if job_data.get('status') == 'completed' and os.path.exists(output_path):
                app.logger.info(f"Sending file {output_path} for job {job_id} (from conversion_progress)")
                try:
                    if 'author' in job_data and 'title' in job_data:
                        author = job_data['author']
                        title = job_data['title']
                        filename = f"{author}-{title}.pdf"
                    else:
                        filename = f"converted_{job_id[:8]}.pdf"
                    
                    completed_files[job_id] = {
                        'path': output_path,
                        'author': job_data.get('author', 'unknown'),
                        'title': job_data.get('title', 'ebook')
                    }
                    save_completed_files()
                        
                    response = send_file(output_path, as_attachment=True, download_name=filename)
                    response.headers['Cache-Control'] = 'public, max-age=86400'
                    response.headers['ETag'] = hashlib.md5(str(os.path.getmtime(output_path)).encode()).hexdigest()
                    return response
                except Exception as e:
                    app.logger.error(f"Error sending file from conversion_progress: {str(e)}")
    
    if job_id in completed_files:
        file_info = completed_files[job_id]
        app.logger.debug(f"File info in completed_files: {file_info}")
        
        output_path = file_info['path'] if isinstance(file_info, dict) else file_info
        app.logger.debug(f"Output path from completed_files: {output_path}")
        app.logger.debug(f"File exists: {os.path.exists(output_path)}")
        
        if os.path.exists(output_path):
            app.logger.info(f"Sending file {output_path} for job {job_id} (from completed_files)")
            try:
                if isinstance(file_info, dict) and 'author' in file_info and 'title' in file_info:
                    author = file_info['author']
                    title = file_info['title']
                    filename = f"{author}-{title}.pdf"
                else:
                    filename = f"converted_{job_id[:8]}.pdf"
                    
                response = send_file(output_path, as_attachment=True, download_name=filename)
                response.headers['Cache-Control'] = 'public, max-age=86400'
                response.headers['ETag'] = hashlib.md5(str(os.path.getmtime(output_path)).encode()).hexdigest()
                return response
            except Exception as e:
                app.logger.error(f"Error sending file from completed_files: {str(e)}")
    
    app.logger.error("All download attempts failed")
    return "File not found or job expired", 404

@app.route("/system-info")
@cache.cached(timeout=60)
def system_info():
    """
    System information endpoint for debugging.
    Only available in debug mode.
    
    Returns:
        Response: Rendered template with system information or 404
    """
    app.logger.info("System info requested")
    if not app.debug:
        return "Not Found", 404
    
    info = {
        "calibre_version": "Unknown",
        "fonts": [],
        "temp_directory": TEMP_DIR,
        "temp_directory_writable": os.access(TEMP_DIR, os.W_OK),
        "python_version": os.popen("python --version").read().strip(),
        "environment": dict(os.environ),
        "disk_space": os.popen("df -h").read(),
        "active_jobs": len(conversion_progress),
        "completed_files": len(completed_files),
        "job_timeout": JOB_TIMEOUT,
    }
    
    try:
        info["calibre_version"] = subprocess.check_output(
            ["ebook-convert", "--version"], 
            text=True, 
            stderr=subprocess.STDOUT
        ).strip()
    except Exception as e:
        info["calibre_error"] = str(e)
    
    try:
        fonts_output = subprocess.check_output(
            ["fc-list"], 
            text=True
        ).strip()
        info["fonts"] = [line.split(":")[0] for line in fonts_output.split("\n")]
    except Exception as e:
        info["fonts_error"] = str(e)
    
    return render_template(
        "system_info.html", 
        info=info,
        ibm_plex_installed=any("IBMPlex" in font for font in info["fonts"])
    )

@app.route("/api/v1/health", methods=["GET"])
@cache.cached(timeout=60)
def api_health():
    """
    API health check endpoint.
    
    Returns:
        Response: JSON with service status information
    """
    app.logger.info("API health check requested")
    
    try:
        calibre_version = get_calibre_version()
        calibre_status = "available"
    except Exception as e:
        app.logger.error(f"Calibre not available: {str(e)}")
        calibre_version = "Not available"
        calibre_status = "unavailable"
    
    return jsonify({
        "status": "operational",
        "api_version": "1.0.0",
        "calibre": {
            "status": calibre_status,
            "version": calibre_version
        }
    })

@app.route("/disclaimer")
def disclaimer():
    """
    Route for the legal disclaimer page.
    
    Returns:
        Response: Rendered disclaimer template with timeout information
    """
    app.logger.info("Disclaimer page requested")

    timeout_minutes = (JOB_TIMEOUT + 59) // 60
    return render_template("disclaimer.html", timeout_minutes=timeout_minutes)

@app.route("/api/v1/device_profiles", methods=["GET"])
@cache.cached(timeout=300)
def api_device_profiles():
    """
    API endpoint for device profiles.
    
    Returns:
        Response: JSON with device profile information
    """
    app.logger.info("API device profiles requested")
    
    profiles = {
        "reMarkable": REMARKABLE_PARAMS,
        "boox_air_4c": BOOX_AIR_4C_PARAMS,
    }
    
    return jsonify(profiles)

@app.route("/api/v1/convert", methods=["POST"])
def api_convert():
    """
    API endpoint for EPUB conversion.
    
    Returns:
        Response: JSON with job information or error
    """
    app.logger.info("API conversion requested")
    
    if 'epub_file' not in request.files:
        app.logger.error("API: No file part in the request")
        return jsonify({"error": "No file part"}), 400
        
    epub_file = request.files["epub_file"]
    if not epub_file or epub_file.filename == "":
        app.logger.error("API: No file selected")
        return jsonify({"error": "No file selected"}), 400
        
    if not epub_file.filename.lower().endswith('.epub'):
        app.logger.error(f"API: Invalid file extension: {epub_file.filename}")
        return jsonify({"error": "Only EPUB files are supported"}), 400
        
    if request.content_length > 100 * 1024 * 1024:
        app.logger.error(f"API: File too large: {request.content_length / (1024*1024):.2f}MB")
        return jsonify({"error": "File size exceeds the 100MB limit"}), 400
    
    app.logger.info(f"API: File uploaded: {epub_file.filename}")
    
    job_id = str(uuid.uuid4())
    app.logger.info(f"API: Created job ID: {job_id}")
    
    with tempfile.NamedTemporaryFile(suffix=".epub", dir=TEMP_DIR, delete=False) as input_tmp_file, \
         tempfile.NamedTemporaryFile(suffix=".pdf", dir=TEMP_DIR, delete=False) as output_tmp_file:

        input_path = input_tmp_file.name
        output_path = output_tmp_file.name
        
        app.logger.debug(f"API: Created temporary files: input={input_path}, output={output_path}")

        epub_file.save(input_path)
        app.logger.debug(f"API: Saved uploaded file to {input_path}")

        device_profile = request.form.get("device_profile", "reMarkable")
        app.logger.info(f"API: Selected device profile: {device_profile}")

        if device_profile == "reMarkable":
            params = REMARKABLE_PARAMS
        elif device_profile == "boox_air_4c":
            params = BOOX_AIR_4C_PARAMS
        else:
            params = {}
            for key in DEFAULT_PARAMS.keys():
                if key in request.form:
                    if key in ["embed_all_fonts", "subset_embedded_fonts", "unsmarten_punctuation", "preserve_cover_aspect_ratio"]:
                        params[key] = key in request.form and request.form.get(key) in ["true", "True", "1", "on"]
                    else:
                        params[key] = request.form.get(key)
                else:
                    params[key] = DEFAULT_PARAMS[key]
        
        app.logger.debug(f"API: Parameters: {params}")

        command = build_conversion_command(input_path, output_path, params)
            
        app.logger.debug(f"API: Final command: {' '.join(command)}")

        app.logger.info(f"API: Starting conversion thread for job {job_id}")

        author, title = get_epub_metadata(input_path)
        
        conversion_progress[job_id] = {
            'status': 'starting', 
            'progress': 0, 
            'message': 'Starting conversion...',
            'input_path': input_path,
            'output_path': output_path,
            'detailed_logs': [],
            'author': author,
            'title': title
        }
        save_jobs()

        thread = threading.Thread(
            target=run_conversion, 
            args=(command, job_id, input_path, output_path)
        )
        thread.daemon = True
        thread.start()

        time.sleep(0.2)

        base_url = request.url_root.rstrip('/')
        response = {
            "job_id": job_id,
            "status_url": f"{base_url}/api/v1/jobs/{job_id}/status",
            "download_url": f"{base_url}/api/v1/jobs/{job_id}/download",
            "status": "processing"
        }
        
        return jsonify(response), 202

@app.route("/api/v1/jobs/<job_id>/status", methods=["GET"])
def api_job_status(job_id):
    """
    API endpoint for job status.
    
    Args:
        job_id (str): Job identifier
        
    Returns:
        Response: JSON with job status information
    """
    app.logger.info(f"API: Status requested for job {job_id}")
    
    global conversion_progress
    if job_id not in conversion_progress:
        app.logger.debug(f"API: Job {job_id} not in memory, trying to load from disk")
        disk_jobs = load_saved_jobs()
        if job_id in disk_jobs:
            app.logger.info(f"API: Found job {job_id} in saved jobs file, reloading")
            conversion_progress.update(disk_jobs)
    
    if job_id in conversion_progress:
        job_data = conversion_progress[job_id].copy()
        
        if 'detailed_logs' in job_data:
            job_data['logs'] = job_data['detailed_logs'][-10:]
            del job_data['detailed_logs']
            
        if job_data['status'] == 'completed':
            base_url = request.url_root.rstrip('/')
            job_data['download_url'] = f"{base_url}/api/v1/jobs/{job_id}/download"
            
            if 'author' in job_data and 'title' in job_data:
                job_data['filename'] = f"{job_data['author']}-{job_data['title']}.pdf"
            
        return jsonify(job_data)
    
    elif job_id in completed_files:
        file_info = completed_files[job_id]
        output_path = file_info['path'] if isinstance(file_info, dict) else file_info
        
        if os.path.exists(output_path):
            base_url = request.url_root.rstrip('/')
            response_data = {
                "status": "completed",
                "progress": 100,
                "message": "Conversion completed successfully",
                "download_url": f"{base_url}/api/v1/jobs/{job_id}/download"
            }
            
            if isinstance(file_info, dict) and 'author' in file_info and 'title' in file_info:
                author = file_info['author']
                title = file_info['title']
                response_data["filename"] = f"{author}-{title}.pdf"
                response_data["author"] = author
                response_data["title"] = title
                
            return jsonify(response_data)

    return jsonify({
        "status": "not_found",
        "error": "Job not found or expired"
    }), 404

@app.route("/api/v1/jobs/<job_id>/download", methods=["GET"])
def api_job_download(job_id):
    """
    API endpoint for file download.
    
    Args:
        job_id (str): Job identifier
        
    Returns:
        Response: File download or error JSON
    """
    app.logger.info(f"API: Download requested for job {job_id}")
    global conversion_progress, completed_files
    
    app.logger.debug(f"API: Job ID {job_id} in conversion_progress: {job_id in conversion_progress}")
    app.logger.debug(f"API: Job ID {job_id} in completed_files: {job_id in completed_files}")
    if job_id not in conversion_progress and job_id not in completed_files:
        app.logger.debug(f"API: Job {job_id} not in memory, trying to load from disk")
        disk_jobs = load_saved_jobs()
        disk_completed = load_completed_files()
        
        if job_id in disk_jobs:
            app.logger.info(f"API: Found job {job_id} in saved jobs file, reloading")
            conversion_progress.update(disk_jobs)
        
        if job_id in disk_completed:
            app.logger.info(f"API: Found job {job_id} in completed files, reloading")
            completed_files.update(disk_completed)
    
    if job_id in conversion_progress:
        job_data = conversion_progress[job_id]
        app.logger.debug(f"API: Job data in conversion_progress: {job_data}")
        
        if 'status' in job_data:
            app.logger.debug(f"API: Job status: {job_data['status']}")
        
        if 'output_path' in job_data:
            output_path = job_data['output_path']
            app.logger.debug(f"API: Output path from conversion_progress: {output_path}")
            app.logger.debug(f"API: File exists: {os.path.exists(output_path)}")
            
            if job_data.get('status') == 'completed' and os.path.exists(output_path):
                app.logger.info(f"API: Sending file {output_path} for job {job_id} (from conversion_progress)")
                try:
                    if 'author' in job_data and 'title' in job_data:
                        author = job_data['author']
                        title = job_data['title']
                        filename = f"{author}-{title}.pdf"
                    else:
                        filename = f"converted_{job_id[:8]}.pdf"
                    
                    completed_files[job_id] = {
                        'path': output_path,
                        'author': job_data.get('author', 'unknown'),
                        'title': job_data.get('title', 'ebook')
                    }
                    save_completed_files()
                                        
                    response = send_file(output_path, as_attachment=True, 
                                    download_name=filename,
                                    mimetype="application/pdf")
                    response.headers['Cache-Control'] = 'public, max-age=86400'
                    response.headers['ETag'] = hashlib.md5(str(os.path.getmtime(output_path)).encode()).hexdigest()
                    return response
                except Exception as e:
                    app.logger.error(f"API: Error sending file from conversion_progress: {str(e)}")
    
    if job_id in completed_files:
        file_info = completed_files[job_id]
        app.logger.debug(f"API: File info in completed_files: {file_info}")
        
        output_path = file_info['path'] if isinstance(file_info, dict) else file_info
        app.logger.debug(f"API: Output path from completed_files: {output_path}")
        app.logger.debug(f"API: File exists: {os.path.exists(output_path)}")
        
        if os.path.exists(output_path):
            app.logger.info(f"API: Sending file {output_path} for job {job_id} (from completed_files)")
            try:
                if isinstance(file_info, dict) and 'author' in file_info and 'title' in file_info:
                    author = file_info['author']
                    title = file_info['title']
                    filename = f"{author}-{title}.pdf"
                else:
                    filename = f"converted_{job_id[:8]}.pdf"
                
                response = send_file(output_path, as_attachment=True, 
                                download_name=filename,
                                mimetype="application/pdf")
                response.headers['Cache-Control'] = 'public, max-age=86400'
                response.headers['ETag'] = hashlib.md5(str(os.path.getmtime(output_path)).encode()).hexdigest()
                return response
            except Exception as e:
                app.logger.error(f"API: Error sending file from completed_files: {str(e)}")
        else:
            app.logger.warning(f"API: File {output_path} from completed_files doesn't exist for job {job_id}")

    return jsonify({"error": "File not found or job expired"}), 404

if __name__ == "__main__":
    app.logger.info("Starting application")
    app.run(debug=DEBUG_MODE)