"""
Simple Pipeline - Exécute les 2 pipelines en une seule requête
Le serveur gère tout : exécution + génération HTML
"""
from flask import Blueprint, request, jsonify, send_file
import os
import json
import threading
from datetime import datetime
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
import subprocess
import time
import zipfile
import shutil
from .run_card_html import generate_run_card_html

simple_pipeline_bp = Blueprint('simple_pipeline', __name__)

RUNS_BASE_DIR = "evotree/runs"

def get_run_dir(run_id):
    """Get the working directory for a run"""
    return os.path.join(RUNS_BASE_DIR, run_id)

def get_state_file(run_id):
    """Get the state.json file path for a run"""
    return os.path.join(get_run_dir(run_id), "state.json")

def create_state_file(run_id, search_params, selection_params):
    """Create initial state file"""
    run_dir = get_run_dir(run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    state = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "running",
        "search_params": search_params,
        "selection_params": selection_params,
        "current_step": "Starting pipeline 1...",
        "pipeline1": {
            "status": "running",
            "fasta_file": None,
            "mafft_file": None,
            "iqtree_file": None,
            "nw_distance_file": None,
        },
        "pipeline2": {
            "status": "pending",
            "bl_fasta_file": None,
            "mafft_file": None,
            "bmge_file": None,
            "iqtree_file": None,
            "nw_distance_file": None,
        }
    }
    
    with open(get_state_file(run_id), 'w') as f:
        json.dump(state, f, indent=2)
    
    return state

def update_state(run_id, updates):
    """Update state file"""
    state_file = get_state_file(run_id)
    
    # Read current state
    state = read_state(run_id)
    if state is None:
        print(f"Warning: Could not read state file {state_file}, creating new state")
        state = {"status": "running", "run_id": run_id}
    
    state.update(updates)
    state['updated_at'] = datetime.now().isoformat()
    
    # Write updated state
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error writing state file {state_file}: {e}")
    
    return state

def read_state(run_id):
    """Read state file"""
    state_file = get_state_file(run_id)
    if not os.path.exists(state_file):
        return None
    
    try:
        with open(state_file, 'r') as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading state file {state_file}: {e}")
        return None

def run_pipeline_background(run_id, fasta_content, search_params, selection_params):
    """Execute both pipelines in background"""
    try:
        run_dir = get_run_dir(run_id)
        
        # Validate fasta_content
        if not fasta_content or not fasta_content.strip():
            raise ValueError("FASTA content is empty")
        
        print(f"[{run_id}] Starting pipeline with {len(fasta_content)} chars of FASTA")
        
        # ============= PIPELINE 1 =============
        update_state(run_id, {"current_step": "Pipeline 1: Creating FASTA..."})
        
        # Create initial FASTA
        fasta_file = os.path.join(run_dir, f"{run_id}_initial.fasta")
        with open(fasta_file, 'w') as f:
            f.write(fasta_content)
        
        print(f"[{run_id}] Created FASTA file: {fasta_file}")
        
        state = update_state(run_id, {
            "pipeline1": {
                "status": "running",
                "fasta_file": fasta_file,
                "mafft_file": None,
                "iqtree_file": None,
                "nw_distance_file": None,
            }
        })
        
        # MAFFT
        update_state(run_id, {"current_step": "Pipeline 1: Running MAFFT..."})
        mafft_file = os.path.join(run_dir, f"{run_id}_p1_mafft.fasta")
        print(f"[{run_id}] Running MAFFT on {fasta_file}")
        
        # Validate input FASTA is not empty
        if os.path.getsize(fasta_file) == 0:
            raise Exception(f"Input FASTA file is empty: {fasta_file}")
        
        result = subprocess.run(['mafft', '--auto', fasta_file], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode != 0:
            raise Exception(f"MAFFT failed: {result.stderr}")
        with open(mafft_file, 'w') as out_f:
            out_f.write(result.stdout)
        
        # Validate output is not empty
        if os.path.getsize(mafft_file) == 0:
            raise Exception(f"MAFFT produced empty output file: {mafft_file}")
        
        pipeline1 = state['pipeline1']
        pipeline1['mafft_file'] = mafft_file
        update_state(run_id, {"pipeline1": pipeline1})
        
        # IQ-TREE
        update_state(run_id, {"current_step": "Pipeline 1: Building tree with IQ-TREE..."})
        iqtree_prefix = os.path.join(run_dir, f"{run_id}_p1_tree")
        print(f"[{run_id}] Running IQ-TREE on {mafft_file}")
        result = subprocess.run(['iqtree2', '-s', mafft_file, '-pre', iqtree_prefix, '-m', 'MFP', '-bb', '1000', '-nt', 'AUTO'], 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"IQ-TREE failed: {result.stderr}")
        iqtree_file = f"{iqtree_prefix}.treefile"
        
        pipeline1['iqtree_file'] = iqtree_file
        update_state(run_id, {"pipeline1": pipeline1})
        
        # NW Distance
        update_state(run_id, {"current_step": "Pipeline 1: Calculating distances..."})
        nw_distance_file = os.path.join(run_dir, f"{run_id}_p1_distances.txt")
        print(f"[{run_id}] Running nw_distance on {iqtree_file}")
        # Use -n flag to output sequence labels with distances (space-separated format)
        result = subprocess.run(['nw_distance', '-n', iqtree_file], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode != 0:
            raise Exception(f"nw_distance failed: {result.stderr}")
        with open(nw_distance_file, 'w') as out_f:
            out_f.write(result.stdout)
        
        pipeline1['nw_distance_file'] = nw_distance_file
        pipeline1['status'] = 'completed'
        update_state(run_id, {"pipeline1": pipeline1})
        
        # ============= PIPELINE 2 =============
        update_state(run_id, {"current_step": "Pipeline 2: Creating FASTA from branch lengths..."})
        
        # Debug: Check nw_distance file content
        print(f"[{run_id}] Reading branch lengths from {nw_distance_file}")
        print(f"[{run_id}] File size: {os.path.getsize(nw_distance_file)} bytes")
        
        # Read and display first few lines for debugging
        with open(nw_distance_file, 'r') as f:
            lines = f.readlines()
            print(f"[{run_id}] Total lines in nw_distance: {len(lines)}")
            print(f"[{run_id}] First 5 lines:")
            for i, line in enumerate(lines[:5]):
                print(f"  Line {i+1}: {repr(line)}")
        
        # Create FASTA with one sequence per species (lowest branch length)
        lowest_bl_species = {}
        with open(nw_distance_file, 'r') as bl_file:
            for line_num, line in enumerate(bl_file, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                # Parse space-separated format: sequence_id distance
                parts = line.split()
                
                print(f"[{run_id}] Line {line_num}: '{line}' → {len(parts)} parts: {parts}")
                
                if len(parts) >= 2:  # At least 2 parts (sequence_id and branch_length)
                    sequence_id = parts[0]
                    bl_value_str = parts[1]
                    
                    # Extract species name (everything before the last underscore+number)
                    # E.g., "Chlorocebus_sabaeus_1" → "Chlorocebus_sabaeus"
                    parts_id = sequence_id.split('_')
                    if len(parts_id) >= 2:
                        species_name = '_'.join(parts_id[:-1])
                    else:
                        species_name = sequence_id  # fallback
                    
                    try:
                        bl_value = float(bl_value_str)
                        print(f"[{run_id}]   Species: {species_name}, Sequence: {sequence_id}, BL: {bl_value}")
                        
                        if species_name not in lowest_bl_species:
                            lowest_bl_species[species_name] = {'sequence_id': sequence_id, 'branch_length': bl_value}
                            print(f"[{run_id}]   → New species, added")
                        elif bl_value < lowest_bl_species[species_name]['branch_length']:
                            print(f"[{run_id}]   → Lower BL than {lowest_bl_species[species_name]['sequence_id']} ({lowest_bl_species[species_name]['branch_length']}), replacing")
                            lowest_bl_species[species_name] = {'sequence_id': sequence_id, 'branch_length': bl_value}
                        else:
                            print(f"[{run_id}]   → Higher BL, keeping {lowest_bl_species[species_name]['sequence_id']}")
                    except ValueError as e:
                        print(f"[{run_id}]   ERROR parsing branch length '{bl_value_str}': {e}")
                        continue
                else:
                    print(f"[{run_id}]   Skipping line (not 2 parts)")
        
        print(f"[{run_id}] Found {len(lowest_bl_species)} unique species with branch lengths")
        sequence_id_to_keep = {v['sequence_id'] for v in lowest_bl_species.values()}
        print(f"[{run_id}] Sequence IDs to keep: {sequence_id_to_keep}")
        
        bl_fasta_file = os.path.join(run_dir, f"{run_id}_p2_bl.fasta")
        sequences_written = 0
        
        print(f"[{run_id}] Reading FASTA file {fasta_file}")
        with open(fasta_file, 'r') as input_fasta, open(bl_fasta_file, 'w') as output_fasta:
            for record in SeqIO.parse(input_fasta, 'fasta'):
                # record.id is the first word of the header (before space)
                print(f"[{run_id}] Checking record: id='{record.id}', description='{record.description[:80]}...'")
                if record.id in sequence_id_to_keep:
                    # Remove the numeric suffix (_1, _2, _3, etc.) from the species name
                    # Example: "Homo_sapiens_2" -> "Homo_sapiens"
                    parts = record.id.split('_')
                    if len(parts) >= 2 and parts[-1].isdigit():
                        # Remove the last part (the number)
                        new_id = '_'.join(parts[:-1])
                        # Create a new record with updated ID
                        new_record = SeqRecord(
                            record.seq,
                            id=new_id,
                            description=record.description.replace(record.id, new_id, 1)
                        )
                        SeqIO.write(new_record, output_fasta, 'fasta')
                        print(f"[{run_id}]   ✅ Kept sequence: {record.id} -> {new_id}")
                    else:
                        # Keep original if no numeric suffix
                        SeqIO.write(record, output_fasta, 'fasta')
                        print(f"[{run_id}]   ✅ Kept sequence: {record.id}")
                    sequences_written += 1
                else:
                    print(f"[{run_id}]   ❌ Skipped (not in keep list)")
        
        print(f"[{run_id}] Wrote {sequences_written} sequences to {bl_fasta_file}")
        
        # Validate BL FASTA is not empty
        if sequences_written == 0 or os.path.getsize(bl_fasta_file) == 0:
            raise Exception(f"Branch length filtering produced empty FASTA. Found {len(lowest_bl_species)} species but wrote 0 sequences. Check that FASTA headers match nw_distance output.")
        
        state = read_state(run_id)
        state['pipeline2']['status'] = 'running'
        state['pipeline2']['bl_fasta_file'] = bl_fasta_file
        update_state(run_id, state)
        
        # MAFFT
        update_state(run_id, {"current_step": "Pipeline 2: Running MAFFT..."})
        mafft_file_p2 = os.path.join(run_dir, f"{run_id}_p2_mafft.fasta")
        print(f"[{run_id}] Running MAFFT P2 on {bl_fasta_file}")
        
        # Validate input FASTA is not empty
        if os.path.getsize(bl_fasta_file) == 0:
            raise Exception(f"Input FASTA file is empty: {bl_fasta_file}")
        
        result = subprocess.run(['mafft', '--auto', bl_fasta_file], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode != 0:
            raise Exception(f"MAFFT P2 failed: {result.stderr}")
        with open(mafft_file_p2, 'w') as out_f:
            out_f.write(result.stdout)
        
        # Validate output is not empty
        if os.path.getsize(mafft_file_p2) == 0:
            raise Exception(f"MAFFT P2 produced empty output file: {mafft_file_p2}")
        
        state = read_state(run_id)
        state['pipeline2']['mafft_file'] = mafft_file_p2
        update_state(run_id, state)
        
        # BMGE
        update_state(run_id, {"current_step": "Pipeline 2: Filtering with BMGE..."})
        bmge_file = os.path.join(run_dir, f"{run_id}_p2_bmge.fasta")
        print(f"[{run_id}] Running BMGE on {mafft_file_p2}")
        
        # Validate input FASTA is not empty
        if os.path.getsize(mafft_file_p2) == 0:
            raise Exception(f"Input FASTA file is empty: {mafft_file_p2}")
        
        # Use bmge command directly (not java -jar BMGE.jar)
        result = subprocess.run(['bmge', '-i', mafft_file_p2, '-t', 'AA', '-of', bmge_file], 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"BMGE failed: {result.stderr}")
        
        # Validate output is not empty
        if not os.path.exists(bmge_file) or os.path.getsize(bmge_file) == 0:
            raise Exception(f"BMGE produced empty or no output file: {bmge_file}")
        
        state = read_state(run_id)
        state['pipeline2']['bmge_file'] = bmge_file
        update_state(run_id, state)
        
        # IQ-TREE
        update_state(run_id, {"current_step": "Pipeline 2: Building tree with IQ-TREE..."})
        iqtree_prefix_p2 = os.path.join(run_dir, f"{run_id}_p2_tree")
        print(f"[{run_id}] Running IQ-TREE P2 on {bmge_file}")
        result = subprocess.run(['iqtree2', '-s', bmge_file, '-pre', iqtree_prefix_p2, '-m', 'MFP', '-bb', '1000', '-nt', 'AUTO'], 
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise Exception(f"IQ-TREE P2 failed: {result.stderr}")
        iqtree_file_p2 = f"{iqtree_prefix_p2}.treefile"
        
        state = read_state(run_id)
        state['pipeline2']['iqtree_file'] = iqtree_file_p2
        update_state(run_id, state)
        
        # NW Distance
        update_state(run_id, {"current_step": "Pipeline 2: Calculating final distances..."})
        nw_distance_file_p2 = os.path.join(run_dir, f"{run_id}_p2_distances.txt")
        print(f"[{run_id}] Running nw_distance P2 on {iqtree_file_p2}")
        result = subprocess.run(['nw_distance', '-n', iqtree_file_p2], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode != 0:
            raise Exception(f"nw_distance P2 failed: {result.stderr}")
        with open(nw_distance_file_p2, 'w') as out_f:
            out_f.write(result.stdout)
        
        state = read_state(run_id)
        state['pipeline2']['nw_distance_file'] = nw_distance_file_p2
        state['pipeline2']['status'] = 'completed'
        state['status'] = 'completed'
        state['current_step'] = 'All pipelines completed!'
        update_state(run_id, state)
        
    except Exception as e:
        print(f"[{run_id}] ERROR: {str(e)}")
        update_state(run_id, {
            "status": "failed",
            "current_step": f"Error: {str(e)}"
        })

@simple_pipeline_bp.route('/run_full_pipeline', methods=['POST'])
def run_full_pipeline():
    """Launch both pipelines in background"""
    data = request.json
    run_id = data.get('run_id')
    fasta_content = data.get('fasta_content')
    search_params = data.get('search_params', {})
    selection_params = data.get('selection_params', {})
    
    # Create state file
    create_state_file(run_id, search_params, selection_params)
    
    # Verify state file was created
    state_file = get_state_file(run_id)
    if not os.path.exists(state_file):
        return jsonify({
            'status': 'error',
            'message': 'Failed to create state file'
        }), 500
    
    # Launch in background thread
    thread = threading.Thread(
        target=run_pipeline_background,
        args=(run_id, fasta_content, search_params, selection_params)
    )
    thread.daemon = True
    thread.start()
    
    # Give a tiny moment for the thread to start
    time.sleep(0.1)
    
    return jsonify({
        'status': 'success',
        'message': 'Pipeline launched',
        'run_id': run_id
    })

@simple_pipeline_bp.route('/get_run_status/<run_id>', methods=['GET'])
def get_run_status(run_id):
    """Return HTML with run status"""
    state = read_state(run_id)
    
    if not state:
        # Return a "starting" message instead of 404
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h2 style="color: #8B5CF6; margin-top: 0;">Run: {run_id}</h2>
            <div style="margin: 20px 0; color: #F59E0B;">
                <strong>Status:</strong> Starting...
            </div>
            <div style="margin: 20px 0;">
                Pipeline is initializing. Please wait a moment and click Refresh.
            </div>
        </div>
        """
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    # Use the reusable run card component
    html = generate_run_card_html(state)
    
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@simple_pipeline_bp.route('/list_all_runs', methods=['GET'])
def list_all_runs():
    """Return HTML with all runs"""
    if not os.path.exists(RUNS_BASE_DIR):
        return "<div style='padding: 20px;'>No runs found</div>", 200, {'Content-Type': 'text/html; charset=utf-8'}
    
    runs = []
    for run_id in os.listdir(RUNS_BASE_DIR):
        run_dir = os.path.join(RUNS_BASE_DIR, run_id)
        if os.path.isdir(run_dir):
            state = read_state(run_id)
            if state:
                runs.append(state)
    
    # Sort by creation date (most recent first)
    runs.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Generate HTML
    html = """
    <div style="font-family: Arial, sans-serif; padding: 20px;">
    """
    
    if not runs:
        html += "<div style='color: #666;'>No runs found</div>"
    else:
        for state in runs:
            # Use the reusable run card component
            html += generate_run_card_html(state)
    
    html += "</div>"
    
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

@simple_pipeline_bp.route('/list_runs_json', methods=['GET'])
def list_runs_json():
    """Return list of runs as JSON"""
    if not os.path.exists(RUNS_BASE_DIR):
        return jsonify([])
    
    runs = []
    for run_id in os.listdir(RUNS_BASE_DIR):
        run_dir = os.path.join(RUNS_BASE_DIR, run_id)
        if os.path.isdir(run_dir):
            state = read_state(run_id)
            if state:
                runs.append({
                    'run_id': state.get('run_id'),
                    'status': state.get('status'),
                    'created_at': state.get('created_at'),
                    'search_params': state.get('search_params'),
                })
    
    # Sort by creation date (most recent first)
    runs.sort(key=lambda x: x['created_at'], reverse=True)
    
    return jsonify(runs)

@simple_pipeline_bp.route('/get_run_state/<run_id>', methods=['GET'])
def get_run_state(run_id):
    """Return the full state.json for a run"""
    try:
        state = read_state(run_id)
        if not state:
            return jsonify({"error": "Run not found"}), 404
        
        return jsonify(state), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@simple_pipeline_bp.route('/download_run_zip/<run_id>', methods=['GET'])
def download_run_zip(run_id):
    """Download all results from a run as a ZIP file"""
    try:
        run_dir = get_run_dir(run_id)
        
        if not os.path.exists(run_dir):
            return jsonify({"error": "Run not found"}), 404
        
        # Create a temporary ZIP file
        zip_filename = f"{run_id}_results.zip"
        zip_path = os.path.join(RUNS_BASE_DIR, zip_filename)
        
        # Create ZIP archive of the entire run directory
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(run_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Add file to ZIP with relative path
                    arcname = os.path.relpath(file_path, run_dir)
                    zipf.write(file_path, arcname)
        
        # Send the ZIP file
        response = send_file(zip_path, as_attachment=True, download_name=zip_filename)
        
        # Clean up the ZIP file after sending (in a callback)
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
            except Exception as e:
                print(f"Error cleaning up ZIP file: {e}")
        
        return response
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@simple_pipeline_bp.route('/delete_run/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Delete a run and all its files"""
    try:
        run_dir = get_run_dir(run_id)
        
        if not os.path.exists(run_dir):
            return jsonify({"error": "Run not found"}), 404
        
        # Delete the entire run directory
        shutil.rmtree(run_dir)
        print(f"Deleted run: {run_id}")
        
        return jsonify({"status": "success", "message": f"Run {run_id} deleted"}), 200
    
    except Exception as e:
        print(f"Error deleting run {run_id}: {e}")
        return jsonify({"error": str(e)}), 500