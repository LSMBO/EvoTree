"""
Simple Pipeline Client - Architecture simplifiée
Le serveur fait tout, le client affiche juste le HTML
"""
from nicegui import ui
import httpx
import config
from datetime import datetime
import asyncio


async def launch_full_pipeline():
    """Launch both pipelines with a single request"""
    # Generate run_id
    run_id = datetime.now().strftime("%d%m%Y%H%M%S")
    config.current_run_id = run_id
    
    # Prepare FASTA content from selected_data
    fasta_content = ""
    species_count = {}  # Track sequences per species
    
    if config.current_search_type == 'protein':
        for item in config.selected_data:
            # Extract accession
            accession = item.get('primaryAccession', item.get('accession', 'Unknown'))
            
            # Extract and validate sequence
            sequence_data = item.get('sequence', '')
            if isinstance(sequence_data, dict):
                sequence = sequence_data.get('value', '')
            else:
                sequence = sequence_data
            
            # Skip empty sequences
            if not sequence or not sequence.strip():
                print(f"Warning: Skipping entry {accession} - empty sequence")
                continue
            
            # Extract organism name
            organism_data = item.get('organism', item.get('scientific_name', 'Unknown'))
            if isinstance(organism_data, dict):
                organism = organism_data.get('scientificName', 'Unknown')
            else:
                organism = organism_data
            
            # Replace spaces with underscores in organism name
            organism_formatted = organism.replace(' ', '_')
            
            # Count sequences per species
            if organism_formatted not in species_count:
                species_count[organism_formatted] = 1
            else:
                species_count[organism_formatted] += 1
            species_index = species_count[organism_formatted]
            
            # Extract protein name - try multiple possible locations
            protein_desc = item.get('proteinDescription', {})
            if isinstance(protein_desc, dict):
                recommended = protein_desc.get('recommendedName', {})
                if isinstance(recommended, dict):
                    full_name = recommended.get('fullName', {})
                    if isinstance(full_name, dict):
                        protein_name = full_name.get('value', '')
                    else:
                        protein_name = ''
                else:
                    protein_name = ''
            else:
                protein_name = ''
            
            # Fallback to other fields
            if not protein_name:
                protein_name = item.get('protein_name', '')
            if not protein_name:
                protein_name = config.search_params.get('term', 'Unknown protein')
            
            # Extract database and uniprot ID
            database = item.get('database', 'UniProt')
            uniprot_id = item.get('uniProtkbId', accession)
            
            # Determine database prefix (tr or sp for UniProt, or just accession for NCBI)
            if database == 'NCBI':
                db_prefix = ''
                full_id = accession
            else:
                # UniProt: check if reviewed (sp) or unreviewed (tr)
                entry_type = item.get('entryType', 'UniProtKB/TrEMBL')
                db_prefix = 'sp' if 'Swiss-Prot' in entry_type else 'tr'
                full_id = f"{db_prefix}|{accession}|{uniprot_id}"
            
            # Format header: >Organism_1 Protein name db|accession|id
            header = f">{organism_formatted}_{species_index} {protein_name} {full_id}"
            fasta_content += f"{header}\n{sequence}\n"
            
    else:  # gene
        for item in config.selected_data:
            gene_id = item.get('gene_id', item.get('accession', 'Unknown'))
            sequence = item.get('sequence', '')
            
            # Skip empty sequences
            if not sequence or not sequence.strip():
                print(f"Warning: Skipping entry {gene_id} - empty sequence")
                continue
            
            organism = item.get('organism', item.get('scientific_name', 'Unknown'))
            organism_formatted = organism.replace(' ', '_')
            
            # Count sequences per species
            if organism_formatted not in species_count:
                species_count[organism_formatted] = 1
            else:
                species_count[organism_formatted] += 1
            species_index = species_count[organism_formatted]
            
            gene_name = item.get('gene_name', config.search_params.get('term', 'Unknown gene'))
            
            header = f">{organism_formatted}_{species_index} {gene_name} {gene_id}"
            fasta_content += f"{header}\n{sequence}\n"
    
    # Prepare search params
    search_params = {
        'term': config.search_params.get('term', ''),
        'taxonomy': config.search_params.get('taxid', ''),
        'rank': 'species',
        'search_type': config.current_search_type or 'protein',
    }
    
    # Prepare selection params
    selection_params = {
        'min_length': config.selection_params.get('min_length', '*'),
        'max_length': config.selection_params.get('max_length', '*'),
        'uniprot': config.selection_params.get('uniprot', True),
        'ncbi': config.selection_params.get('ncbi', True),
        'having_mrna': False,
    }
    
    # Launch pipeline
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{config.API_BASE_URL}/run_full_pipeline",
                json={
                    'run_id': run_id,
                    'fasta_content': fasta_content,
                    'search_params': search_params,
                    'selection_params': selection_params,
                }
            )
            
            if response.status_code == 200:
                ui.notify('Pipeline launched! Click Refresh to see progress.', color='positive')
                return run_id
            else:
                ui.notify(f'Failed to launch pipeline: {response.status_code}', color='negative')
                return None
                
    except Exception as e:
        ui.notify(f'Error launching pipeline: {str(e)}', color='negative')
        return None


async def get_run_status_html(run_id):
    """Get HTML status from server"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/get_run_status/{run_id}"
            )
            
            if response.status_code == 200:
                return response.text
            else:
                return f"<div style='color: red;'>Error: {response.status_code}</div>"
                
    except Exception as e:
        return f"<div style='color: red;'>Error: {str(e)}</div>"


async def get_all_runs_html():
    """Get HTML of all runs from server"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{config.API_BASE_URL}/list_all_runs"
            )
            
            if response.status_code == 200:
                return response.text
            else:
                return f"<div style='color: red;'>Error: {response.status_code}</div>"
                
    except Exception as e:
        return f"<div style='color: red;'>Error: {str(e)}</div>"


async def show_simple_pipeline():
    """Show simple pipeline interface"""
    config.pipeline_container.clear()
    config.pipeline_container.set_visibility(True)
    
    with config.pipeline_container:
        ui.label('Phylogenetic Analysis').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-4')
        
        # Buttons
        button_row = ui.row().classes('gap-4 mb-4')
        
        # Row container for card + download button side by side
        display_row = ui.row().classes('w-full items-start gap-4')
        
        # Left side: status container (flex-grow)
        status_container = ui.column().classes('flex-grow')
        
        # Right side: download button container (fixed width)
        download_container = ui.column().classes('flex-shrink-0')
        download_container.set_visibility(False)
        
        with button_row:
            async def handle_launch():
                run_id = await launch_full_pipeline()
                if run_id:
                    # Hide the launch button after clicking
                    launch_btn.set_visibility(False)
                    # Wait a moment for state file to be written
                    await asyncio.sleep(0.5)
                    # Show initial status
                    html = await get_run_status_html(run_id)
                    status_container.clear()
                    with status_container:
                        ui.html(html)
                    # Check if completed to show download button
                    await check_and_show_download_button()
            
            async def handle_refresh():
                if config.current_run_id:
                    html = await get_run_status_html(config.current_run_id)
                    status_container.clear()
                    with status_container:
                        ui.html(html)
                    # Check if completed to show download button
                    await check_and_show_download_button()
                else:
                    ui.notify('No pipeline running', color='warning')
            
            async def check_and_show_download_button():
                """Check if run is completed and show download button"""
                if config.current_run_id:
                    try:
                        async with httpx.AsyncClient(timeout=10) as client:
                            response = await client.get(
                                f"{config.API_BASE_URL}/get_run_status/{config.current_run_id}"
                            )
                            if response.status_code == 200:
                                # Simple check: if "COMPLETED" is in the HTML response
                                if "COMPLETED" in response.text:
                                    download_container.set_visibility(True)
                                else:
                                    download_container.set_visibility(False)
                    except Exception as e:
                        print(f"Error checking status: {e}")
            
            def handle_download():
                """Download the ZIP file"""
                if config.current_run_id:
                    download_url = f"{config.API_BASE_URL}/download_run_zip/{config.current_run_id}"
                    ui.download(download_url)
                    ui.notify('Download started!', color='positive')
            
            launch_btn = ui.button('▶️ Run Pipeline', on_click=handle_launch)
            launch_btn.style(f'background-color: {config.VIOLET_COLOR} !important')
            
            refresh_btn = ui.button('🔄 Refresh', on_click=handle_refresh)
            refresh_btn.style('background-color: #6B7280 !important')
        
        # Display row with card and download button
        with display_row:
            # Status display area (left side)
            with status_container:
                ui.markdown('_Click "Run Pipeline" to start both phylogenetic analyses_').classes('text-gray-500')
            
            # Download button (right side, shown only when completed)
            with download_container:
                download_btn = ui.button('Download Results (ZIP)', on_click=handle_download)
                download_btn.style('background-color: #10B981 !important; white-space: pre-line; text-align: center; padding: 12px 16px; min-width: 120px;')


async def show_run_history():
    """Show history"""
    config.run_history_container.clear()
    config.run_history_container.set_visibility(True)
    
    with config.run_history_container:
        ui.label('History').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-4')
        
        # Container for runs display
        runs_container = ui.column().classes('w-full')
        
        async def handle_refresh():
            runs_container.clear()
            
            # Get list of runs from server
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(f"{config.API_BASE_URL}/list_runs_json")
                    
                    if response.status_code == 200:
                        runs = response.json()
                        
                        if not runs:
                            with runs_container:
                                ui.label('No runs found').classes('text-gray-500')
                        else:
                            # Display each run with its own card and download button
                            for run_info in runs:
                                run_id = run_info['run_id']
                                status = run_info['status']
                                
                                with runs_container:
                                    # Create a row container for card + buttons side by side
                                    run_row = ui.row().classes('w-full items-start')
                                    
                                    with run_row:
                                        # Left side: HTML card (flex-grow to take available space)
                                        card_container = ui.column()

                                        # Right side: Buttons (fixed width, aligned to top)
                                        button_container = ui.column().classes('flex-shrink-0 gap-2')
                                        
                                        # Get and display the HTML card
                                        try:
                                            html_response = await client.get(
                                                f"{config.API_BASE_URL}/get_run_status/{run_id}"
                                            )
                                            if html_response.status_code == 200:
                                                with card_container:
                                                    ui.html(html_response.text)
                                                
                                                # Add buttons
                                                with button_container:
                                                    # Details button (always shown)
                                                    def make_details_handler(rid):
                                                        async def handler():
                                                            try:
                                                                async with httpx.AsyncClient(timeout=10) as details_client:
                                                                    state_response = await details_client.get(
                                                                        f"{config.API_BASE_URL}/get_run_state/{rid}"
                                                                    )
                                                                    if state_response.status_code == 200:
                                                                        state_data = state_response.json()
                                                                        # Format JSON nicely
                                                                        import json
                                                                        formatted_json = json.dumps(state_data, indent=2)
                                                                        
                                                                        # Create dialog to show the JSON
                                                                        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl'):
                                                                            ui.label(f'Run Details: {rid}').classes('text-xl font-bold mb-4')
                                                                            
                                                                            # Display JSON in a scrollable pre element
                                                                            ui.html(f'''
                                                                                <pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; 
                                                                                           border-radius: 8px; overflow-x: auto; max-height: 600px; 
                                                                                           overflow-y: auto; font-family: 'Courier New', monospace; 
                                                                                           font-size: 12px; line-height: 1.5;">{formatted_json}</pre>
                                                                            ''')
                                                                            
                                                                            # Close button
                                                                            ui.button('Close', on_click=dialog.close).classes('mt-4')
                                                                        
                                                                        dialog.open()
                                                                    else:
                                                                        ui.notify(f'Error loading details: {state_response.status_code}', color='negative')
                                                            except Exception as e:
                                                                ui.notify(f'Error: {str(e)}', color='negative')
                                                        return handler
                                                    
                                                    details_btn = ui.button('📋 Details', 
                                                                           on_click=make_details_handler(run_id))
                                                    details_btn.style('background-color: #3B82F6 !important;')
                                                    
                                                    # Download button (only if completed)
                                                    if status == 'completed':
                                                        def make_download_handler(rid):
                                                            def handler():
                                                                download_url = f"{config.API_BASE_URL}/download_run_zip/{rid}"
                                                                ui.download(download_url)
                                                                ui.notify('Download started!', color='positive')
                                                            return handler
                                                        
                                                        ui.button('Download Results (ZIP)', 
                                                                       on_click=make_download_handler(run_id))
                                                    
                                                    # Delete button (always shown)
                                                    def make_delete_handler(rid):
                                                        async def handler():
                                                            # Confirm deletion
                                                            try:
                                                                async with httpx.AsyncClient(timeout=10) as delete_client:
                                                                    delete_response = await delete_client.delete(
                                                                        f"{config.API_BASE_URL}/delete_run/{rid}"
                                                                    )
                                                                    if delete_response.status_code == 200:
                                                                        ui.notify(f'Run {rid} deleted!', color='positive')
                                                                        # Refresh the list
                                                                        await handle_refresh()
                                                                    else:
                                                                        ui.notify(f'Error deleting run: {delete_response.status_code}', color='negative')
                                                            except Exception as e:
                                                                ui.notify(f'Error: {str(e)}', color='negative')
                                                        return handler
                                                    
                                                    delete_btn = ui.button('🗑️ Delete Run', 
                                                                        on_click=make_delete_handler(run_id))
                                                    delete_btn.style('background-color: #EF4444 !important; white-space: pre-line')
                                        
                                        except Exception as e:
                                            with card_container:
                                                ui.label(f'Error loading run {run_id}: {str(e)}').classes('text-red-500')
                    else:
                        with runs_container:
                            ui.label(f'Error loading runs: {response.status_code}').classes('text-red-500')
                            
            except Exception as e:
                with runs_container:
                    ui.label(f'Error: {str(e)}').classes('text-red-500')
        
        # Refresh button
        refresh_btn = ui.button('🔄 Refresh', on_click=handle_refresh)
        refresh_btn.style('background-color: #6B7280 !important')
        refresh_btn.classes('mb-4')
        
        # Initial load
        await handle_refresh()
