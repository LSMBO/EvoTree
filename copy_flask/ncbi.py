import xml.etree.ElementTree as ET
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
from flask import Blueprint, request, jsonify
import os
import sys, logging

create_ncbi_fasta_bp = Blueprint('create_ncbi_fasta_bp', __name__)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

@create_ncbi_fasta_bp.route('/create_ncbi_fasta', methods=['POST'])
def create_ncbi_fasta():
    selected_data = request.json.get('selected_data')
    fasta_file = request.json.get('fasta_file')
    
    if not selected_data or not fasta_file:
        return jsonify({"status": "error", "message": "Missing selected_data or fasta_file"}), 400
        
    try:
        full_path = f"evotree/tmp/{fasta_file}"
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Create FASTA records with indexed headers
        records = create_fasta_records_with_index(selected_data)
        
        SeqIO.write(records, full_path, "fasta")
        
        if not os.path.exists(full_path):
            return jsonify({"status": "error", "message": f"FASTA file was not created: {full_path}"}), 500
        
        return jsonify({"status": "success", "file": full_path})
        
    except Exception as e:
        logger.info(f"Error in create_ncbi_fasta: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400


def create_fasta_records_with_index(selected_data):
    records = []
    species_count = {}
    
    for entry in selected_data:
        if "database" not in entry or entry["database"] != "NCBI":
            continue
        scientific_name = entry.get('scientific_name', 'Unknown').replace(' ', '_')
        entry_name = entry.get('protein_name', entry.get('gene_name', 'Unknown'))
        accession = entry.get('accession', 'Unknown')
        sequence = entry.get('sequence', '')
        
        # Count occurrences of each species to create unique indexes
        if scientific_name not in species_count:
            species_count[scientific_name] = 1
        else:
            species_count[scientific_name] += 1
        
        idx = species_count[scientific_name]
        
        # Create header: ScientificName_index ProteinName Accession
        header_id = f"{scientific_name}_{idx}"
        description = f"{entry_name} {accession}"
        
        # Create BioPython SeqRecord
        record = SeqRecord(
            Seq(sequence),
            id=header_id,
            description=description
        )
        
        records.append(record)
    
    return records
