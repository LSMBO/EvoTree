import requests
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
from flask import Blueprint, request, jsonify
import re
import os
import shlex
import subprocess
import sys, logging

merge_uniprot_ncbi_fasta_bp = Blueprint('merge_uniprot_ncbi_fasta_bp', __name__)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

@merge_uniprot_ncbi_fasta_bp.route('/merge_uniprot_ncbi_fasta', methods=['POST'])
def merge_uniprot_ncbi_fasta():
    uniprot_fasta_file = request.json.get('uniprot_file')
    ncbi_fasta_file = request.json.get('ncbi_file')
    merged_file_name = request.json.get('merged_file')
    merged_file = f"evotree/tmp/{merged_file_name}"
    raw_merged_file = f"evotree/tmp/raw_{merged_file_name}"
    
    try:
        logger.info(f"Merging files: {uniprot_fasta_file} and {ncbi_fasta_file} into {merged_file}")
        with open(raw_merged_file, 'w') as outfile:
            for file in [uniprot_fasta_file, ncbi_fasta_file]:
                with open(file, 'r') as infile:
                    outfile.write(infile.read())
        
        command = f"cd-hit -i {raw_merged_file} -o {merged_file} -c 1 -G 0 -aL 1"
        logger.info(f"\nExecuting command: {command}")
        command_args = shlex.split(command)
        response = subprocess.Popen(command_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = response.communicate()
        os.remove(raw_merged_file)

        returncode = response.returncode
        if returncode != 0:
            return {'status': 'error', 'message': stderr.decode()}
        
        if not os.path.exists(merged_file):
            return {'status': 'error', 'message': 'cdhit failed to produce output file.'}
        
        rename_headers(merged_file)    
    
        return {'status': 'success', 'file': merged_file}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def rename_headers(fasta_file):
    new_records = []
    species_count = {}
    
    for record in SeqIO.parse(fasta_file, "fasta"):
        species = '_'.join(record.id.split('_')[:-1])
        if species not in species_count:
            species_count[species] = 1
        else:
            species_count[species] += 1        
        idx = species_count[species]
        new_header = f"{species}_{idx} {' '.join(record.description.split(' ')[1:])}"
        new_records.append(SeqRecord(record.seq, id=new_header, description=""))
    
    SeqIO.write(new_records, fasta_file, "fasta")
        
