import asyncio
import httpx
from nicegui import ui
from datetime import datetime
import config
from uniprot import create_uniprot_fasta
from ncbi import create_ncbi_fasta
from utils import download_file_from_server


# =============================================================================
# FASTA CREATION FUNCTIONS
# =============================================================================

async def create_fasta(download=False):
    """Create FASTA file from selected sequences"""
    min_length = config.selection_params['min_length']
    max_length = config.selection_params['max_length']
    uniprot_file_path = None
    ncbi_file_path = None
    
    if config.selection_params['uniprot']:
        try:
            base_url = "https://rest.uniprot.org/uniprotkb/stream"
            params = {
                'query': f"taxonomy_id:{config.search_params['taxid']} AND protein_name:{config.search_params['term'].replace(' ', '+')} AND length:[{min_length} TO {max_length}]",
                'format': 'fasta'
            }
            uniprot_file_path = await create_uniprot_fasta(base_url, params, config.loading_spinner)
            if uniprot_file_path == "Failed":
                print(f"Failed to create UniProt FASTA file.")
                return 'Failed'
        except Exception as e:
            print(f"Error occurred (create_uniprot_fasta): {e}")
            ui.notify(f'Error: {str(e)}', color='red')
            return 'Failed'

    if config.selection_params['ncbi']:
        try:
            ncbi_file_path = await create_ncbi_fasta(config.selected_data, config.loading_spinner)
            if ncbi_file_path == "Failed":
                print(f"Failed to create NCBI FASTA file.")
                return 'Failed'
        except Exception as e:
            print(f"Error occurred (create_ncbi_fasta): {e}")
            ui.notify(f'Error: {str(e)}', color='red')
            return 'Failed'

    # Handle results
    if uniprot_file_path and ncbi_file_path:
        try:
            print(f"Merging UniProt file: {uniprot_file_path} and NCBI file: {ncbi_file_path}...")
            merged_fasta_path = await merge_uniprot_ncbi_fasta(uniprot_file_path, ncbi_file_path, config.loading_spinner)
            if merged_fasta_path == "Failed":
                print(f"Failed to merge UniProt and NCBI FASTA files.")
                return 'Failed'
            
            if download:
                download_file_from_server(merged_fasta_path)
            return merged_fasta_path
        except Exception as e:
            ui.notify(f'Error: {str(e)}', color='red')
            return 'Failed'

    elif uniprot_file_path:
        if download:
            download_file_from_server(uniprot_file_path)
        return uniprot_file_path
    elif ncbi_file_path:
        if download:
            download_file_from_server(ncbi_file_path)
        return ncbi_file_path
    else:
        ui.notify('No sequences selected from UniProt or NCBI.', color='red')
        return 'Failed'


async def merge_uniprot_ncbi_fasta(uniprot_file_path, ncbi_file_path, loading_spinner):
    """Merge UniProt and NCBI FASTA files"""
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    merged_file_name = f"{identifier}_Merged.fasta"
    loading_spinner.set_visibility(True)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/merge_uniprot_ncbi_fasta",
                json={
                    "uniprot_file": uniprot_file_path,
                    "ncbi_file": ncbi_file_path,
                    "merged_file": merged_file_name
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error merging FASTA files: {e}")
        return 'Failed'
    finally:
        loading_spinner.set_visibility(False)
