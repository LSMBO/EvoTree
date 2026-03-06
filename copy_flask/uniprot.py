import requests
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
from flask import Blueprint, request, jsonify
import re
import sys, logging

create_uniprot_fasta_bp = Blueprint('create_uniprot_fasta_bp', __name__)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

@create_uniprot_fasta_bp.route('/create_uniprot_fasta', methods=['POST'])
def create_uniprot_fasta():
    logger.info("Received request to create Uniprot FASTA")
    base_url = request.json.get('base_url')
    params = request.json.get('params')
    fasta_file = request.json.get('fasta_file')
    if not base_url or not params:
        return jsonify({"status": "error", "message": "Missing base_url or params"}), 400
    params['format'] = 'fasta'
    write_fasta(base_url, params, fasta_file)
    rename_headers(f"evotree/tmp/{fasta_file}")
    return jsonify({"status": "success", "file": f"evotree/tmp/{fasta_file}"})

def write_fasta(url, params, fasta_file):
    try:
        # Create tmp directory if it doesn't exist
        import os
        os.makedirs('evotree/tmp', exist_ok=True)
        
        with requests.get(url, params=params, stream=True) as response:
            if response.status_code == 200:
                with open(f"evotree/tmp/{fasta_file}", "w") as otp:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            otp.write(chunk.decode('utf-8'))
            else:
                logger.info(f"Request failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.info(f"Request failed: {e}")


def rename_headers(fasta_file):
    records = []
    species_count = {}
    for record in SeqIO.parse(fasta_file, "fasta"):
        header = record.description
        # Extract species name
        m = re.search(r'OS=([\w ]+) OX=', header)
        species = m.group(1).replace(' ', '_') if m else "Unknown"
        # Increment species-specific index
        if species not in species_count:
            species_count[species] = 1
        else:
            species_count[species] += 1
        idx = species_count[species]
        # Extract protein name (after the first space)
        protein_name = header.split(' ', 1)[1].split('OS=')[0].strip() if ' ' in header else "Unknown"
        # Extract accession (can start with sp| or tr|)
        m_acc = re.search(r'(sp|tr)\|([^|]+)\|', header)
        accession = m_acc.group(2) if m_acc else "Unknown"
        # Extract Uniprot ID (can start with sp| or tr|)
        m_id = re.search(r'(sp|tr)\|[^|]+\|([^ ]+)', header)
        uniprot_id = m_id.group(2) if m_id else "Unknown"
        # Construct the new header
        new_header = f"{species}_{idx} {protein_name} {m_acc.group(1) if m_acc else 'unknown'}|{accession}|{uniprot_id}"
        records.append(SeqRecord(record.seq, id=new_header, description=""))

    # Rewrite the FASTA file with the new headers
    with open(fasta_file, "w") as out_fasta:
        SeqIO.write(records, out_fasta, "fasta")