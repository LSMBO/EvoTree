
import sys, os, logging
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask import request, jsonify, send_file
from cdhit import cdhit_bp

from evotree.uniprot import create_uniprot_fasta_bp
from evotree.ncbi import create_ncbi_fasta_bp
from evotree.merge_fasta import merge_uniprot_ncbi_fasta_bp
from evotree.clear import clear_bp
from evotree.simple_pipeline import simple_pipeline_bp


from brownovo.recover import recover_bp
from brownovo.denovo import denovo_bp
from brownovo.msblast import msblast_bp
from brownovo.results_display import results_display_bp
from brownovo.search_files import search_files_bp

app = Flask(__name__)
CORS(app)
socketio = SocketIO(cors_allowed_origins="*")
socketio.init_app(app)
app.register_blueprint(cdhit_bp)

app.register_blueprint(create_uniprot_fasta_bp)
app.register_blueprint(create_ncbi_fasta_bp)
app.register_blueprint(merge_uniprot_ncbi_fasta_bp)
app.register_blueprint(clear_bp)
app.register_blueprint(simple_pipeline_bp)

app.register_blueprint(recover_bp)
app.register_blueprint(denovo_bp)
app.register_blueprint(msblast_bp)
app.register_blueprint(results_display_bp)
app.register_blueprint(search_files_bp)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

def log_prefix(route):
    """Generate log prefix with timestamp and route"""
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    return f"[{timestamp} | {route}]"

@app.route("/", methods=["POST"])
def hello():
    name = request.json.get('name', [])
    return jsonify({"message": f"Hello, {name}!"})

@app.route("/download", methods=['GET'])
def download():
    file = request.args.get("file")
    return send_file(
        file, 
        mimetype='text/plain',
        as_attachment=True, 
        download_name=os.path.basename(file)
    )

@app.route("/upload", methods=['POST'])
def upload():
    try:
        logger.info(f"{log_prefix('/upload')} Received upload request")
        if request.files and 'file' in request.files:
            file = request.files['file']
            file_path = os.path.join('uploads', file.filename)
            size = request.form.get('size', None)
            
            # Check if file exists and has the same size
            if os.path.exists(file_path) and size is not None:
                current_size = os.path.getsize(file_path)
                if current_size == int(size):
                    logger.info(f"{log_prefix('/upload')} File {file_path} already exists with same size, skipping upload")
                    return jsonify({
                        'success': True,
                        'file': file_path,
                        'message': f'File already exists with same size, skipping upload',
                        'skipped': True
                    }), 200
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            logger.info(f"{log_prefix('/upload')} File {file_path} uploaded successfully")
            return jsonify({
                'success': True,
                'file': file_path,
                'message': f'File uploaded successfully as {file.filename}',
                'skipped': False
            }), 200
        else:
            data = request.get_json()
            content = data.get('content')
            file_path = data.get('file_path')
            size = data.get('size', None)
            if not file_path:
                logger.error(f"{log_prefix('/upload')} Missing file_path in request")
                return jsonify({'error': 'Missing file_path'}), 400
            
            # Check if file exists and has the same size
            if os.path.exists(file_path) and size is not None:
                current_size = os.path.getsize(file_path)
                if current_size == size:
                    logger.info(f"{log_prefix('/upload')} File {file_path} already exists with same size, skipping upload")
                    return jsonify({
                        'success': True,
                        'file': file_path,
                        'message': f'File already exists with same size, skipping upload',
                        'skipped': True
                    }), 200
            
            # Upload only if file doesn't exist or has different size
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            logger.info(f"{log_prefix('/upload')} File {file_path} uploaded successfully")
            return jsonify({
                'success': True,
                'file': file_path,
                'message': f'File uploaded successfully as {os.path.basename(file_path)}',
                'skipped': False
            }), 200
            
    except Exception as e:
        logger.error(f"{log_prefix('/upload')} Upload failed: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8800, log_output=True)
    
    
