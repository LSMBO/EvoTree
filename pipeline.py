import asyncio
import httpx
from nicegui import ui
from datetime import datetime
import config
from uniprot import create_uniprot_fasta
from ncbi import create_ncbi_fasta
from utils import download_file_from_server
from run_manager_client import create_run_metadata, update_run_step, get_run_metadata
from run_card import create_run_card_from_metadata


# =============================================================================
# FASTA CREATION FUNCTIONS
# =============================================================================

async def upload_custom_fasta_to_server(fasta_content, filename):
    from datetime import datetime
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    server_filename = f"{identifier}_{filename}"
    
    config.loading_spinner.set_visibility(True)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/upload",
                json={
                    "content": fasta_content,
                    "file_path": f"evotree/tmp/{server_filename}"
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data['file']
            else:
                print(f"Upload failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error uploading custom FASTA: {e}")
        return 'Failed'
    finally:
        config.loading_spinner.set_visibility(False)

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

async def run_full_pipeline(pipeline_container, run_bmge=False, run_id=None, resume_from_step=None):
    """
    Run the full phylogenetic pipeline
    
    Args:
        pipeline_container: UI container for progress display
        run_bmge: Whether to run BMGE filtering step
        run_id: Optional run ID (for resuming), otherwise creates new one
        resume_from_step: Optional step to resume from
    """
    pipeline_container.clear()
    pipeline_container.set_visibility(True)
    
    # Create or reuse run_id
    if run_id is None:
        run_id = datetime.now().strftime("%d%m%Y%H%M%S")
    
    # Store run_id in config for later use
    config.current_run_id = run_id
    
    # Container for the run card that will be updated
    card_container = None
    
    async def update_run_card():
        """Update the run card display"""
        if card_container:
            card_container.clear()
            with card_container:
                metadata = await get_run_metadata(run_id)
                if metadata:
                    # Simple display without actions during execution
                    create_run_card_from_metadata(metadata, show_actions=False)
                else:
                    ui.label('Loading run information...').classes('text-gray-500')
    
    with pipeline_container:
        ui.label('Pipeline Execution').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-4')
        
        # Create container for the card
        card_container = ui.column().classes('w-full')
        
        # Initial card display
        await update_run_card()
        
        # Create a timer to refresh the card every 2 seconds
        timer = ui.timer(5.0, update_run_card, active=True)
    
    use_custom_fasta = config.select_sequence_active_tab == 'custom_fasta'
    
    try:
        # Create run metadata at the start (only if not resuming)
        if resume_from_step is None:
            await create_run_metadata(run_id, use_bmge=run_bmge)
        
        # Step 1: Custom FASTA upload OR Create FASTA from search
        if use_custom_fasta:
            # Upload custom FASTA to server
            config.current_fasta_file = await upload_custom_fasta_to_server(
                config.custom_fasta_content, 
                config.custom_fasta_filename
            )
            if config.current_fasta_file == 'Failed':
                await update_run_step(run_id, 'fasta_creation', 'failed')
                raise Exception("Failed to upload custom FASTA file")
            await update_run_step(run_id, 'fasta_creation', 'completed', config.current_fasta_file)
        else:
            # Create FASTA from selected_data
            await update_run_step(run_id, 'fasta_creation', 'running')
            
            if run_bmge:
                # Pipeline 2: Create FASTA from branch lengths
                # Verify that required files from pipeline 1 exist
                if not config.current_fasta_file or config.current_fasta_file == 'Failed':
                    await update_run_step(run_id, 'fasta_creation', 'failed')
                    raise Exception("Pipeline 2 requires a valid FASTA file from Pipeline 1. Please run Pipeline 1 first.")
                
                if not config.current_nw_distance_file or config.current_nw_distance_file == 'Failed':
                    await update_run_step(run_id, 'fasta_creation', 'failed')
                    raise Exception("Pipeline 2 requires distance file from Pipeline 1. Please run Pipeline 1 first.")
                
                print(f"Creating FASTA from branch lengths...")
                print(f"  Original FASTA: {config.current_fasta_file}")
                print(f"  Distance file: {config.current_nw_distance_file}")
                
                config.current_fasta_file = await create_fasta_from_branch_length(
                    download=False, 
                    original_fasta_file=config.current_fasta_file, 
                    nw_distance_file=config.current_nw_distance_file
                )
                
                print(f"  Created FASTA: {config.current_fasta_file}")
            else:
                # Pipeline 1: Create FASTA from selected data
                config.current_fasta_file = await create_fasta(download=False)
                
            if config.current_fasta_file == 'Failed':
                await update_run_step(run_id, 'fasta_creation', 'failed')
                raise Exception("Failed to create FASTA file")
            
            await update_run_step(run_id, 'fasta_creation', 'completed', config.current_fasta_file)
        
        # Step 2: MAFFT
        await update_run_step(run_id, 'mafft', 'running')
        print(f"Running MAFFT on: {config.current_fasta_file}")
        config.current_mafft_file = await run_mafft_pipeline(config.current_fasta_file)
        print(f"MAFFT result: {config.current_mafft_file}")
        await update_run_step(run_id, 'mafft', 'completed', config.current_mafft_file)
        
        if run_bmge:
            # Step 3: BMGE  
            await update_run_step(run_id, 'bmge', 'running')
            config.current_bmge_file = await run_bmge_pipeline(config.current_mafft_file)
            await update_run_step(run_id, 'bmge', 'completed', config.current_bmge_file)
        else:
            config.current_bmge_file = config.current_mafft_file
            await update_run_step(run_id, 'bmge', 'skipped')
        
        # Step 4: IQTREE
        await update_run_step(run_id, 'iqtree', 'running')
        config.current_iqtree_file = await run_iqtree_pipeline(config.current_bmge_file)
        await update_run_step(run_id, 'iqtree', 'completed', config.current_iqtree_file)
        
        # Step 5: NW Distance
        await update_run_step(run_id, 'nw_distance', 'running')
        config.current_nw_distance_file = await run_nw_distance_pipeline(config.current_iqtree_file)
        await update_run_step(run_id, 'nw_distance', 'completed', config.current_nw_distance_file)
        
        # Stop the timer when pipeline completes
        timer.active = False
        
        # Final refresh to show completed state
        await update_run_card()

        return {
            'fasta_file': config.current_fasta_file,
            'mafft_file': config.current_mafft_file,
            'bmge_file': config.current_bmge_file,
            'iqtree_file': config.current_iqtree_file,
            'nw_distance_file': config.current_nw_distance_file
        }
    except Exception as e:
        # Stop the timer on error
        timer.active = False
        ui.notify(f'Pipeline error: {str(e)}', color='red')
        return "failed"

async def run_pipeline_job(tool_name, start_endpoint, status_endpoint, params, max_wait_seconds=3600):
    """
    Generic function to run a pipeline job with timeout
    
    Args:
        tool_name: Name of the tool (for error messages)
        start_endpoint: API endpoint to start the job
        status_endpoint: API endpoint to check job status
        params: Parameters for the start request
        max_wait_seconds: Maximum seconds to wait for completion (default 1 hour)
    """
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            # Start the job
            response = await client.post(f"{config.API_BASE_URL}{start_endpoint}", json=params)
            if response.status_code != 200:
                raise Exception(f"{tool_name} request failed with status code: {response.status_code}")
            
            job_id = response.json()['job_id']
            elapsed_time = 0
            unknown_count = 0  # Count consecutive 'unknown' responses
            last_known_status = 'running'
            
            # Poll for completion
            while elapsed_time < max_wait_seconds:
                await asyncio.sleep(2)
                elapsed_time += 2
                
                try:
                    status_resp = await client.get(f"{config.API_BASE_URL}{status_endpoint}?id={job_id}")
                    status_data = status_resp.json()
                    current_status = status_data.get('status', 'unknown')
                    
                    if current_status == 'finished':
                        return status_data['file']
                    elif current_status == 'error':
                        raise Exception(f"{tool_name} error: {status_data.get('message', 'Unknown error')}")
                    elif current_status == 'unknown':
                        unknown_count += 1
                        # Give more tolerance for 'unknown' status (job might be completing)
                        # Wait up to 60 seconds before giving up
                        if unknown_count >= 30:  # 30 checks * 2 seconds = 60 seconds
                            raise Exception(f"{tool_name} job not found after {unknown_count * 2} seconds (job_id: {job_id})")
                    elif current_status == 'running':
                        last_known_status = 'running'
                        unknown_count = 0  # Reset count if we get a valid status
                        
                except httpx.ReadTimeout:
                    # Continue polling if status check times out
                    continue
                    
            # Timeout reached
            raise Exception(f"{tool_name} timeout after {max_wait_seconds} seconds (last status: {last_known_status})")
            
        except httpx.RequestError as e:
            raise Exception(f"{tool_name} connection error: {str(e)}")

async def run_mafft_pipeline(fasta_file_path):
    return await run_pipeline_job(
        "MAFFT",
        "/mafft_start",
        "/mafft_status",
        {"fasta_file": fasta_file_path},
        max_wait_seconds=1800  # 30 minutes
    )

async def run_bmge_pipeline(mafft_file_path):
    return await run_pipeline_job(
        "BMGE",
        "/bmge_start",
        "/bmge_status",
        {"fasta_file": mafft_file_path},
        max_wait_seconds=600  # 10 minutes
    )

async def run_iqtree_pipeline(file_path):
    return await run_pipeline_job(
        "IQTREE",
        "/iqtree_start",
        "/iqtree_status",
        {"fasta_file": file_path},
        max_wait_seconds=7200  # 2 hours
    )

async def run_nw_distance_pipeline(treefile):
    return await run_pipeline_job(
        "NW Distance",
        "/nw_distance_start",
        "/nw_distance_status",
        {"treefile": treefile},
        max_wait_seconds=300  # 5 minutes
    )
        