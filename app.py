from flask import Flask, jsonify, render_template, request, send_file, Response
import subprocess
import tempfile
import os
import uuid
import re
import threading
import time
import json
import logging
import pickle

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__,
            static_folder='templates',
            static_url_path='/static')

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() in ['true', '1', 'yes', 'y']
app.debug = DEBUG_MODE
app.logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
app.logger.info(f"Application running in {'DEBUG' if DEBUG_MODE else 'PRODUCTION'} mode")

TEMP_DIR = os.environ.get('TEMP_DIR', tempfile.gettempdir())
JOB_TIMEOUT = int(os.environ.get('JOB_TIMEOUT', 300))

os.makedirs(TEMP_DIR, exist_ok=True)
app.logger.info(f"Using temporary directory: {TEMP_DIR}")
app.logger.info(f"Job cleanup timeout: {JOB_TIMEOUT}s")

JOB_DATA_FILE = os.path.join(TEMP_DIR, 'conversion_jobs.pkl')

conversion_progress = {}
completed_files = {}

COMPLETED_FILES_FILE = os.path.join(TEMP_DIR, 'completed_files.pkl')

os.makedirs(os.path.dirname(COMPLETED_FILES_FILE), exist_ok=True)

def load_saved_jobs():
    if os.path.exists(JOB_DATA_FILE):
        try:
            with open(JOB_DATA_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            app.logger.error(f"Error loading saved jobs: {str(e)}")
    return {}

def save_jobs():
    try:
        with open(JOB_DATA_FILE, 'wb') as f:
            pickle.dump(conversion_progress, f)
    except Exception as e:
        app.logger.error(f"Error saving jobs: {str(e)}")

def load_completed_files():
    if os.path.exists(COMPLETED_FILES_FILE):
        try:
            with open(COMPLETED_FILES_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            app.logger.error(f"Error loading completed files: {str(e)}")
    return {}

def save_completed_files():
    try:
        with open(COMPLETED_FILES_FILE, 'wb') as f:
            pickle.dump(completed_files, f)

        app.logger.debug(f"Saved {len(completed_files)} entries to {COMPLETED_FILES_FILE}")
    except Exception as e:
        app.logger.error(f"Error saving completed files: {str(e)}")

def job_cleaner():
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

cleaner_thread = threading.Thread(target=job_cleaner)
cleaner_thread.daemon = True
cleaner_thread.start()
app.logger.info("Started job cleaner thread")

def get_env_params(prefix, defaults):
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

def run_conversion(command, job_id, input_path, output_path):
    try:
        app.logger.info(f"Starting conversion job {job_id}")
        app.logger.debug(f"Command: {' '.join(command)}")
        app.logger.debug(f"Input path: {input_path}")
        app.logger.debug(f"Output path: {output_path}")
        
        app.logger.debug(f"Input file exists: {os.path.exists(input_path)}")
        app.logger.debug(f"Input file permissions: {oct(os.stat(input_path).st_mode)}")
        app.logger.debug(f"Input file size: {os.path.getsize(input_path)}")
        
        try:
            calibre_version = subprocess.check_output(["ebook-convert", "--version"], 
                                                   text=True, stderr=subprocess.STDOUT)
            app.logger.debug(f"Calibre version: {calibre_version}")
        except Exception as e:
            app.logger.error(f"Error checking Calibre version: {str(e)}")
        
        conversion_progress[job_id] = {
            'status': 'running', 
            'progress': 0, 
            'message': 'Starting conversion...',
            'input_path': input_path,
            'output_path': output_path,
            'detailed_logs': []
        }
        save_jobs()
        
        app.logger.debug("Starting subprocess...")
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
        
        app.logger.debug("Reading process output...")
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            app.logger.debug(f"Process output: {line}")
            full_output.append(line)
            conversion_progress[job_id]['detailed_logs'].append(line)
            
            match = progress_pattern.search(line)
            if match:
                progress = int(match.group(1))
                conversion_progress[job_id]['progress'] = progress
                conversion_progress[job_id]['message'] = line
            else:
                conversion_progress[job_id]['message'] = line
            
            save_jobs()
        
        app.logger.debug("Waiting for process to complete...")
        process.wait()
        returncode = process.returncode
        app.logger.debug(f"Process completed with return code: {returncode}")
        
        if returncode == 0:
            app.logger.info(f"Conversion job {job_id} completed successfully")
            conversion_progress[job_id]['status'] = 'completed'
            conversion_progress[job_id]['progress'] = 100
            conversion_progress[job_id]['message'] = 'Conversion completed successfully!'
            conversion_progress[job_id]['completed_time'] = time.time()
            
            if os.path.exists(output_path):
                app.logger.debug(f"Output file exists: {os.path.exists(output_path)}")
                app.logger.debug(f"Output file size: {os.path.getsize(output_path)}")
                
                completed_files[job_id] = output_path
                save_completed_files()
                app.logger.debug(f"Added job {job_id} to completed_files dictionary (now has {len(completed_files)} entries)")
            else:
                app.logger.error(f"Output file does not exist despite successful return code!")
                conversion_progress[job_id]['status'] = 'failed'
                conversion_progress[job_id]['message'] = 'Conversion failed: Output file not created!'
        else:
            app.logger.error(f"Conversion job {job_id} failed with return code {returncode}")
            conversion_progress[job_id]['status'] = 'failed'
            conversion_progress[job_id]['message'] = f'Conversion failed with code {returncode}! Check logs for details.'
            conversion_progress[job_id]['completed_time'] = time.time()

            error_details = '\n'.join(full_output[-10:]) if full_output else "No output captured"
            conversion_progress[job_id]['error_details'] = error_details
            
            app.logger.error(f"Error details: {'\n'.join(full_output)}")
        
        save_jobs()
    
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        app.logger.error(f"Exception in conversion job {job_id}: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        
        conversion_progress[job_id]['status'] = 'failed'
        conversion_progress[job_id]['message'] = error_msg
        conversion_progress[job_id]['error_details'] = error_msg
        conversion_progress[job_id]['completed_time'] = time.time()
        
        save_jobs()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        app.logger.info("POST request received")
        
        if 'epub_file' not in request.files:
            app.logger.error("No file part in the request")
            return "No file part", 400
            
        epub_file = request.files["epub_file"]
        if not epub_file or epub_file.filename == "":
            app.logger.error("No file selected")
            return "No file selected", 400
        
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

            if params["embed_all_fonts"]:
                command.append("--embed-all-fonts")
                app.logger.debug("Added --embed-all-fonts")
            if params["subset_embedded_fonts"]:
                command.append("--subset-embedded-fonts")
                app.logger.debug("Added --subset-embedded-fonts")
            if params["unsmarten_punctuation"]:
                command.append("--unsmarten-punctuation")
                app.logger.debug("Added --unsmarten-punctuation")
            if params["preserve_cover_aspect_ratio"]:
                command.append("--preserve-cover-aspect-ratio")
                app.logger.debug("Added --preserve-cover-aspect-ratio")
                
            app.logger.debug(f"Final command: {' '.join(command)}")

            app.logger.info(f"Starting conversion thread for job {job_id}")
            thread = threading.Thread(
                target=run_conversion, 
                args=(command, job_id, input_path, output_path)
            )
            thread.daemon = True
            thread.start()
            
            save_jobs()
            
            app.logger.info(f"Redirecting to progress page for job {job_id}")
            return render_template("progress.html", job_id=job_id)

    app.logger.info("Rendering index page")
    return render_template("index.html", default_params=DEFAULT_PARAMS)

@app.route("/progress/<job_id>")
def progress(job_id):
    app.logger.info(f"SSE connection established for job {job_id}")
    
    def generate():
        if job_id not in conversion_progress:
            app.logger.warning(f"Job {job_id} not found in conversion_progress")
            error_data = {
                'status': 'failed',
                'message': 'Job not found',
                'progress': 0,
                'error_details': 'Der Konvertierungsauftrag wurde nicht gefunden. Dies kann passieren, wenn:\n- Die Seite neu geladen wurde\n- Der Server neu gestartet wurde\n- Der Auftrag bereits abgeschlossen oder abgelaufen ist\n\nBitte versuche es erneut mit einer neuen Konvertierung.'
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            return
            
        while job_id in conversion_progress:
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
                
            time.sleep(0.5)
    
    return Response(generate(), mimetype="text/event-stream")

@app.route("/download/<job_id>")
def download(job_id):
    app.logger.info(f"Download requested for job {job_id}")
    
    if job_id in conversion_progress:
        if conversion_progress[job_id]['status'] == 'completed':
            output_path = conversion_progress[job_id]['output_path']
            if os.path.exists(output_path):
                app.logger.info(f"Sending file {output_path} for job {job_id} (from conversion_progress)")
                try:
                    return send_file(output_path, as_attachment=True, download_name=f"converted_{job_id[:8]}.pdf")
                except Exception as e:
                    app.logger.error(f"Error sending file: {str(e)}")
                    return f"Error sending file: {str(e)}", 500
    
    if job_id in completed_files:
        output_path = completed_files[job_id]
        if os.path.exists(output_path):
            app.logger.info(f"Sending file {output_path} for job {job_id} (from completed_files)")
            try:
                return send_file(output_path, as_attachment=True, download_name=f"converted_{job_id[:8]}.pdf")
            except Exception as e:
                app.logger.error(f"Error sending file: {str(e)}")
                return f"Error sending file: {str(e)}", 500
    
    try:
        app.logger.info("Searching for recent PDF files as fallback")
        newest_pdf = None
        newest_time = 0
        
        for file in os.listdir(TEMP_DIR):
            if file.endswith('.pdf'):
                pdf_path = os.path.join(TEMP_DIR, file)
                mtime = os.path.getmtime(pdf_path)
                
                if time.time() - mtime < 300 and mtime > newest_time:
                    newest_time = mtime
                    newest_pdf = pdf_path
        
        if newest_pdf:
            app.logger.info(f"Found recent PDF file as fallback: {newest_pdf}")
            
            completed_files[job_id] = newest_pdf
            save_completed_files()
            
            return send_file(newest_pdf, as_attachment=True, download_name=f"converted_{job_id[:8]}.pdf")
    except Exception as e:
        app.logger.error(f"Error in fallback search: {str(e)}")
    
    app.logger.error("All download attempts failed")
    return "File not found or job expired", 404

@app.route("/system-info")
def system_info():
    app.logger.info("System info requested")
    
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
def api_health():
    app.logger.info("API health check requested")
    
    try:
        calibre_version = subprocess.check_output(
            ["ebook-convert", "--version"], 
            text=True, 
            stderr=subprocess.STDOUT
        ).strip()
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

@app.route("/api/v1/device_profiles", methods=["GET"])
def api_device_profiles():
    app.logger.info("API device profiles requested")
    
    profiles = {
        "reMarkable": REMARKABLE_PARAMS,
        "boox_air_4c": BOOX_AIR_4C_PARAMS,
    }
    
    return jsonify(profiles)

@app.route("/api/v1/convert", methods=["POST"])
def api_convert():
    app.logger.info("API conversion requested")
    
    if 'epub_file' not in request.files:
        app.logger.error("API: No file part in the request")
        return jsonify({"error": "No file part"}), 400
        
    epub_file = request.files["epub_file"]
    if not epub_file or epub_file.filename == "":
        app.logger.error("API: No file selected")
        return jsonify({"error": "No file selected"}), 400
    
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
            
        app.logger.debug(f"API: Final command: {' '.join(command)}")

        app.logger.info(f"API: Starting conversion thread for job {job_id}")
        thread = threading.Thread(
            target=run_conversion, 
            args=(command, job_id, input_path, output_path)
        )
        thread.daemon = True
        thread.start()
        
        save_jobs()
        
        base_url = request.url_root.rstrip('/')
        response = {
            "job_id": job_id,
            "status_url": f"{base_url}/api/v1/jobs/{job_id}/status",
            "download_url": f"{base_url}/api/v1/jobs/{job_id}/download",
            "status": "processing"
        }
        
        return jsonify(response), 202  # 202 Accepted

@app.route("/api/v1/jobs/<job_id>/status", methods=["GET"])
def api_job_status(job_id):
    app.logger.info(f"API: Status requested for job {job_id}")
    
    if job_id in conversion_progress:
        job_data = conversion_progress[job_id].copy()
        
        if 'detailed_logs' in job_data:
            job_data['logs'] = job_data['detailed_logs'][-10:]
            del job_data['detailed_logs']
            
        if job_data['status'] == 'completed':
            base_url = request.url_root.rstrip('/')
            job_data['download_url'] = f"{base_url}/api/v1/jobs/{job_id}/download"
            
        return jsonify(job_data)
    
    elif job_id in completed_files:
        output_path = completed_files[job_id]
        if os.path.exists(output_path):
            base_url = request.url_root.rstrip('/')
            return jsonify({
                "status": "completed",
                "progress": 100,
                "message": "Conversion completed successfully",
                "download_url": f"{base_url}/api/v1/jobs/{job_id}/download"
            })

    return jsonify({
        "status": "not_found",
        "error": "Job not found or expired"
    }), 404

@app.route("/api/v1/jobs/<job_id>/download", methods=["GET"])
def api_job_download(job_id):
    app.logger.info(f"API: Download requested for job {job_id}")

    if job_id in completed_files:
        output_path = completed_files[job_id]
        if os.path.exists(output_path):
            app.logger.info(f"API: Sending file {output_path} for job {job_id} (from completed_files)")
            try:
                return send_file(output_path, as_attachment=True, 
                                download_name=f"converted_{job_id[:8]}.pdf",
                                mimetype="application/pdf")
            except Exception as e:
                app.logger.error(f"API: Error sending file: {str(e)}")
                return jsonify({"error": f"Error sending file: {str(e)}"}), 500
    
    return jsonify({"error": "File not found or job expired"}), 404

if __name__ == "__main__":
    app.logger.info("Starting application")
    app.run(debug=DEBUG_MODE)