"""
Run Manager Client - Client-side functions to interact with run management API
"""
import httpx
import config
from datetime import datetime


async def create_run_metadata(run_id, use_bmge=False):
    """
    Create metadata for a new run on the server
    
    Args:
        run_id: Timestamp identifier (ddMMyyyyHHmmss)
        use_bmge: Whether BMGE will be used in this pipeline
    
    Returns:
        dict: Metadata object or None if failed
    """
    try:
        # Prepare search parameters
        search_params = {
            'term': config.search_params.get('term', ''),
            'taxonomy': config.search_params.get('taxid', ''),
            'rank': 'species',  # Default, you can store this in config if needed
            'search_type': config.current_search_type or 'protein',
        }
        
        # Prepare selection parameters
        selection_params = {
            'min_length': config.selection_params.get('min_length', '*'),
            'max_length': config.selection_params.get('max_length', '*'),
            'uniprot': config.selection_params.get('uniprot', True),
            'ncbi': config.selection_params.get('ncbi', True),
            'having_mrna': False,  # Can be added to config if needed
        }
        
        # Calculate statistics
        num_sequences = len(config.selected_data) if config.selected_data else 0
        
        # Count unique species
        species_set = set()
        if config.current_search_type == 'gene':
            for item in config.selected_data:
                taxid = item.get('taxid', '')
                if taxid:
                    species_set.add(taxid)
        else:
            for item in config.selected_data:
                taxid = item.get('organism', {}).get('taxonId') or item.get('taxid')
                if taxid:
                    species_set.add(taxid)
        
        stats = {
            'num_sequences': num_sequences,
            'num_species': len(species_set),
        }
        
        # Prepare pipeline configuration
        pipeline_config = {
            'use_bmge': use_bmge,
            'pipeline_type': 'analysis' if use_bmge else 'selection',
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/evotree_run/create",
                json={
                    'run_id': run_id,
                    'search_params': search_params,
                    'selection_params': selection_params,
                    'pipeline_config': pipeline_config,
                    'stats': stats,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('metadata')
            else:
                print(f"Failed to create run metadata: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"Error creating run metadata: {e}")
        return None


async def update_run_step(run_id, step_name, status, file_path=None):
    """
    Update the status of a pipeline step
    
    Args:
        run_id: Run identifier
        step_name: Name of the step ('fasta_creation', 'mafft', 'bmge', 'iqtree', 'nw_distance')
        status: Status ('running', 'completed', 'failed', 'skipped')
        file_path: Path to the output file (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/evotree_run/update",
                json={
                    'run_id': run_id,
                    'step_name': step_name,
                    'status': status,
                    'file_path': file_path,
                }
            )
            
            return response.status_code == 200
            
    except Exception as e:
        print(f"Error updating run step: {e}")
        return False


async def get_run_metadata(run_id):
    """
    Get detailed metadata for a specific run
    
    Args:
        run_id: Run identifier
    
    Returns:
        dict: Metadata object or None if not found
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/evotree_run/get",
                params={'run_id': run_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('metadata')
            else:
                return None
                
    except Exception as e:
        print(f"Error getting run metadata: {e}")
        return None


async def list_all_runs():
    """
    List all runs from the server
    
    Returns:
        list: List of run summaries or empty list if failed
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{config.API_BASE_URL}/evotree_run/list")
            
            if response.status_code == 200:
                data = response.json()
                return data.get('runs', [])
            else:
                return []
                
    except Exception as e:
        print(f"Error listing runs: {e}")
        return []


async def delete_run(run_id):
    """
    Delete a run and its metadata
    
    Args:
        run_id: Run identifier
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/evotree_run/delete",
                json={'run_id': run_id}
            )
            
            return response.status_code == 200
            
    except Exception as e:
        print(f"Error deleting run: {e}")
        return False
