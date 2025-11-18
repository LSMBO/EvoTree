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

async def create_fasta_from_branch_length(download, original_fasta_file, nw_distance_file):
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    bl_fasta_file = f"{identifier}_bl.fasta"
    config.loading_spinner.set_visibility(True)
    
    try:
        async with httpx.AsyncClient(timeout=360000) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/create_bl_fasta",
                json={
                    "original_fasta_file": original_fasta_file,
                    "nw_distance_file": nw_distance_file,
                    "bl_fasta_file": bl_fasta_file
                }
            )
            if response.status_code == 200:
                data = response.json()
                if download:
                    download_file_from_server(data['file'])
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error creating FASTA: {e}")
        return 'Failed'
    finally:
        config.loading_spinner.set_visibility(False)

async def create_fasta(download=False):
    min_length = config.search_params['min_length']
    max_length = config.search_params['max_length']
    uniprot_file_path = None
    ncbi_file_path = None
    
    if config.search_params['uniprot']:
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

    if config.search_params['ncbi']:
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
    
    return 'Failed'

async def merge_uniprot_ncbi_fasta(uniprot_file_path, ncbi_file_path, loading_spinner):
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    fasta_file = f"{identifier}_Merged.fasta"
    loading_spinner.set_visibility(True)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.API_BASE_URL}/merge_uniprot_ncbi_fasta",
                json={"uniprot_file": uniprot_file_path, "ncbi_file": ncbi_file_path, "merged_file": fasta_file}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"Response from Flask: {data}")
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error occurred: {e}")
        return 'Failed'
    finally:
        loading_spinner.set_visibility(False)


# =============================================================================
# PIPELINE EXECUTION FUNCTIONS  
# =============================================================================

async def run_full_pipeline(pipeline_container, run_bmge=False):
    pipeline_container.clear()
    pipeline_container.set_visibility(True)
    
    with pipeline_container:
        pipeline_steps = [
            {"name": "Creating FASTA file", "color": "#FF6B35"},
            {"name": "Running MAFFT alignment", "color": "#F7931E"}, 
        ]
        if run_bmge:
            pipeline_steps += [{"name": "Filtering with BMGE", "color": "#FFD23F"}]
        pipeline_steps += [
                {"name": "Building tree with IQTREE", "color": "#06FFA5"},
                {"name": "Calculating distances", "color": "#4ECDC4"}
        ]
        ui.label('Pipeline Progress').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        progress_label = ui.label('Starting pipeline...').classes('text-lg font-semibold mb-6 text-center')
        
        step_container = ui.row().classes('w-full justify-between mb-3')
        step_indicators = []
        for i, step in enumerate(pipeline_steps):
            with step_container:
                indicator = ui.column().classes('items-center')
                with indicator:
                    circle = ui.element('div').classes(f'w-12 h-12 rounded-full border-4 border-gray-300 flex items-center justify-center text-white font-bold text-lg transition-all duration-500 ease-in-out')
                    ui.label(step['name']).classes('text-sm text-center mt-3 max-w-24')
                step_indicators.append((circle, step['color']))
    
    try:
        # Step 1: Create FASTA
        await update_progress(progress_label, step_indicators, 0, "Creating FASTA file...")
        if run_bmge:
            config.current_fasta_file = await create_fasta_from_branch_length(download=False, original_fasta_file=config.current_fasta_file, nw_distance_file=config.current_nw_distance_file)
        else:
            config.current_fasta_file = await create_fasta(download=False)
            
        if config.current_fasta_file == 'Failed':
            raise Exception("Failed to create FASTA file")
        
        # Step 2: MAFFT
        await update_progress(progress_label, step_indicators, 1, "Running MAFFT alignment...")
        config.current_mafft_file = await run_mafft_pipeline(config.current_fasta_file)
        
        # config.current_mafft_file = "evotree/simul/29102025131303_Merged_mafft.fasta"
        
        if run_bmge:
            # Step 3: BMGE  
            await update_progress(progress_label, step_indicators, 2, "Filtering with BMGE...")
            config.current_bmge_file = await run_bmge_pipeline(config.current_mafft_file)
            
            # config.current_bmge_file = "evotree/simul/29102025131303_Merged_mafft_bmge.fasta"
        else:
            config.current_bmge_file = config.current_mafft_file
        
        # Step 4: IQTREE
        await update_progress(progress_label, step_indicators, 2 if not run_bmge else 3, "Building phylogenetic tree...")
        config.current_iqtree_file = await run_iqtree_pipeline(config.current_bmge_file)
        
        # config.current_iqtree_file = "evotree/simul/29102025131303_Merged_mafft_bmge.fasta.treefile"
        
        # Step 5: NW Distance
        await update_progress(progress_label, step_indicators, 3 if not run_bmge else 4, "Calculating branch lengths...")
        config.current_nw_distance_file = await run_nw_distance_pipeline(config.current_iqtree_file)
        
        await update_progress(progress_label, step_indicators, 5, "")

        return {
            'fasta_file': config.current_fasta_file,
            'mafft_file': config.current_mafft_file,
            'bmge_file': config.current_bmge_file,
            'iqtree_file': config.current_iqtree_file,
            'nw_distance_file': config.current_nw_distance_file
        }
    except Exception as e:
        progress_label.text = f"Pipeline failed: {str(e)}"
        ui.notify(f'Pipeline error: {str(e)}', color='red')
        return "failed"


async def update_progress(progress_label, step_indicators, current_step, message):
    progress_label.text = message
    for i, (circle, color) in enumerate(step_indicators):            
        if i < current_step:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 border-green-500 bg-green-500 flex items-center justify-center text-white font-bold text-lg transition-all duration-500 ease-in-out transform scale-110 shadow-lg')
        elif i == current_step:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 flex items-center justify-center text-white font-bold text-lg transition-all duration-300 ease-in-out transform scale-125 shadow-2xl animate-bounce')
            circle.style(f'border-color: {color}; background-color: {color}; box-shadow: 0 0 20px {color}50;')
            circle.text = str(i + 1)
        else:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 border-gray-300 bg-gray-100 flex items-center justify-center text-gray-500 font-bold text-lg transition-all duration-500 ease-in-out')
            circle.text = str(i + 1)

async def run_mafft_pipeline(fasta_file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/mafft_start", json={"fasta_file": fasta_file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/mafft_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"MAFFT error: {status_data.get('message', '')}")
        else:
            raise Exception(f"MAFFT request failed with status code: {response.status_code}")

async def run_bmge_pipeline(mafft_file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/bmge_start", json={"fasta_file": mafft_file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/bmge_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"BMGE error: {status_data.get('message', '')}")
        else:
            raise Exception(f"BMGE request failed with status code: {response.status_code}")

async def run_iqtree_pipeline(file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/iqtree_start", json={"fasta_file": file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/iqtree_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"IQTREE error: {status_data.get('message', '')}")
        else:
            raise Exception(f"IQTREE request failed with status code: {response.status_code}")

async def run_nw_distance_pipeline(treefile):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/nw_distance_start", json={"treefile": treefile}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/nw_distance_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"NW Distance error: {status_data.get('message', '')}")
        else:
            raise Exception(f"NW Distance request failed with status code: {response.status_code}")
        