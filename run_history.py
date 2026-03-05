"""
Run History UI - Interface to view and resume previous pipeline runs
"""
from nicegui import ui
import config
import styles
from run_manager_client import list_all_runs, get_run_metadata, delete_run, update_run_step
from pipeline import run_full_pipeline
from pipeline_results import show_pipeline1_results, show_pipeline2_results
from utils import download_file_from_server
from datetime import datetime
from run_card import create_run_card


async def show_run_history():
    """Display the run history interface"""
    config.run_history_container.clear()
    config.run_history_container.set_visibility(True)
    
    with config.run_history_container:
        ui.label('Run History').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        ui.markdown(
            'View and resume your previous pipeline runs. '
            'You can continue interrupted runs or review completed analyses.'
        ).classes('text-lg mb-4')
        
        refresh_btn = ui.button('🔄 Refresh', on_click=lambda: show_run_history())
        styles.apply_default_color(refresh_btn)
        
        ui.separator().classes('my-4')
        
        # Get all runs
        config.loading_spinner.set_visibility(True)
        runs = await list_all_runs()
        config.loading_spinner.set_visibility(False)
        
        if not runs:
            ui.markdown('**No previous runs found.**').classes('text-lg text-gray-500 text-center mt-8')
            ui.markdown('Start a new analysis by searching for proteins or genes.').classes('text-md text-gray-400 text-center')
            return
        
        # Display runs in a table
        runs_container = ui.column().classes('w-full gap-4')
        
        with runs_container:
            for run in runs:
                create_run_card(
                    run, 
                    show_actions=True,
                    on_view_details=lambda r=run: view_run_details(r['run_id']),
                    on_resume=lambda r=run: resume_run(r['run_id']) if r['status'] != 'completed' else None,
                    on_delete=lambda r=run: confirm_delete_run(r['run_id'])
                )


async def view_run_details(run_id):
    """Display detailed information about a run in a dialog"""
    metadata = await get_run_metadata(run_id)
    
    if metadata is None:
        ui.notify('Failed to load run details', color='negative')
        return
    
    with ui.dialog() as dialog, ui.card().classes('w-[800px] max-h-[600px] overflow-y-auto p-6'):
        ui.label(f'Run Details: {run_id}').classes('text-2xl font-bold mb-4')
        
        # Search parameters
        ui.label('Search Parameters').classes('text-lg font-semibold mt-4 mb-2')
        with ui.column().classes('pl-4 gap-1'):
            ui.label(f'Type: {metadata["search_params"]["search_type"]}')
            ui.label(f'Term: {metadata["search_params"]["term"]}')
            if metadata["search_params"]["taxonomy"]:
                ui.label(f'Taxonomy: {metadata["search_params"]["taxonomy"]}')
            ui.label(f'Rank: {metadata["search_params"]["rank"]}')
        
        # Selection parameters
        ui.label('Selection Parameters').classes('text-lg font-semibold mt-4 mb-2')
        with ui.column().classes('pl-4 gap-1'):
            ui.label(f'Length range: {metadata["selection_params"]["min_length"]} - {metadata["selection_params"]["max_length"]}')
            ui.label(f'UniProt: {"✓" if metadata["selection_params"]["uniprot"] else "✗"}')
            ui.label(f'NCBI: {"✓" if metadata["selection_params"]["ncbi"] else "✗"}')
        
        # Pipeline steps (in correct order)
        ui.label('Pipeline Steps').classes('text-lg font-semibold mt-4 mb-2')
        step_order = ['fasta_creation', 'mafft', 'bmge', 'iqtree', 'nw_distance']
        with ui.column().classes('pl-4 gap-2'):
            for step_name in step_order:
                if step_name not in metadata["steps"]:
                    continue
                    
                step_info = metadata["steps"][step_name]
                status_icon = '✓' if step_info['status'] == 'completed' else \
                             '⏸' if step_info['status'] == 'skipped' else \
                             '❌' if step_info['status'] == 'failed' else '⏳'
                
                ui.label(f'{status_icon} {step_name.replace("_", " ").title()}: {step_info["status"]}')
                
                if step_info.get('completed_at'):
                    try:
                        completed_dt = datetime.fromisoformat(step_info['completed_at'])
                        ui.label(f'  Completed: {completed_dt.strftime("%Y-%m-%d %H:%M:%S")}').classes('text-sm text-gray-600 pl-4')
                    except:
                        pass
        
        # Files with download buttons (in correct order)
        ui.label('Generated Files').classes('text-lg font-semibold mt-4 mb-2')
        file_order = [
            ('fasta', '📄 FASTA File'),
            ('mafft', '⛓️ MAFFT Alignment'),
            ('bmge', '🔬 BMGE Filtered'),
            ('iqtree', '🌳 IQ-TREE Result'),
            ('nw_distance', '📏 Distance Matrix'),
            ('branch_length_fasta', '📊 Branch Length FASTA')
        ]
        
        with ui.column().classes('pl-4 gap-2'):
            for file_type, label in file_order:
                file_path = metadata["files"].get(file_type)
                if file_path:
                    with ui.row().classes('gap-2 items-center'):
                        ui.label(f'{label}:').classes('text-sm font-semibold min-w-[150px]')
                        ui.label(file_path).classes('text-sm text-gray-600 flex-grow')
                        download_btn = ui.button(
                            icon='download',
                            on_click=lambda fp=file_path: download_file_from_server(fp)
                        ).props('flat dense size=sm')
                        download_btn.tooltip('Download file')
        
        # Statistics
        ui.label('Statistics').classes('text-lg font-semibold mt-4 mb-2')
        with ui.column().classes('pl-4 gap-1'):
            ui.label(f'Sequences: {metadata["stats"]["num_sequences"]}')
            ui.label(f'Species: {metadata["stats"]["num_species"]}')
        
        # Action buttons
        with ui.row().classes('w-full justify-end gap-2 mt-6'):
            if metadata.get('resumable_step'):
                async def do_resume():
                    dialog.close()
                    await resume_run(run_id)
                
                resume_btn = ui.button('Resume Run', on_click=do_resume)
                styles.apply_violet_color(resume_btn)
                styles.apply_play_icon(resume_btn)
            
            close_btn = ui.button('Close', on_click=dialog.close)
            styles.apply_default_color(close_btn)
    
    dialog.open()


async def resume_run(run_id):
    """Resume a pipeline run from where it left off"""
    from pipeline import run_mafft_pipeline, run_bmge_pipeline, run_iqtree_pipeline, run_nw_distance_pipeline
    from pipeline_results import show_pipeline1_results, show_pipeline2_results
    
    ui.notify(f'Resuming run {run_id}...', color='info')
    
    # Get run metadata
    metadata = await get_run_metadata(run_id)
    
    if metadata is None:
        ui.notify('Failed to load run metadata', color='negative')
        return
    
    # Determine which step to resume from
    resumable_step = metadata.get('resumable_step')
    
    if resumable_step is None:
        ui.notify('This run is already complete', color='warning')
        return
    
    # Restore config state from metadata
    config.current_run_id = run_id
    config.current_search_type = metadata['search_params']['search_type']
    config.search_params['term'] = metadata['search_params']['term']
    config.search_params['taxid'] = metadata['search_params']['taxonomy']
    
    config.selection_params['min_length'] = metadata['selection_params']['min_length']
    config.selection_params['max_length'] = metadata['selection_params']['max_length']
    config.selection_params['uniprot'] = metadata['selection_params']['uniprot']
    config.selection_params['ncbi'] = metadata['selection_params']['ncbi']
    
    # Restore file paths from completed steps
    config.current_fasta_file = metadata['files'].get('fasta')
    config.current_mafft_file = metadata['files'].get('mafft')
    config.current_bmge_file = metadata['files'].get('bmge')
    config.current_iqtree_file = metadata['files'].get('iqtree')
    config.current_nw_distance_file = metadata['files'].get('nw_distance')
    
    # Determine if BMGE was used
    use_bmge = metadata['steps']['bmge']['status'] == 'completed'
    
    # Clear and show progress container
    config.pipeline1_container.clear()
    config.pipeline1_container.set_visibility(True)
    
    ui.notify(f'Resuming from step: {resumable_step.replace("_", " ").title()}', color='info')
    
    try:
        # Execute remaining steps based on resumable_step
        if resumable_step == 'fasta_creation':
            ui.notify('Cannot resume from FASTA creation. Please start a new run.', color='warning')
            return
        
        elif resumable_step == 'mafft':
            # FASTA exists, run MAFFT
            await update_run_step(run_id, 'mafft', 'running')
            config.current_mafft_file = await run_mafft_pipeline(config.current_fasta_file)
            await update_run_step(run_id, 'mafft', 'completed', config.current_mafft_file)
            resumable_step = 'iqtree'  # Continue to next step
        
        if resumable_step == 'bmge':
            # MAFFT exists, run BMGE
            await update_run_step(run_id, 'bmge', 'running')
            config.current_bmge_file = await run_bmge_pipeline(config.current_mafft_file)
            await update_run_step(run_id, 'bmge', 'completed', config.current_bmge_file)
            resumable_step = 'iqtree'
        
        if resumable_step == 'iqtree':
            # Use BMGE file if available, otherwise MAFFT file
            input_file = config.current_bmge_file if use_bmge and config.current_bmge_file else config.current_mafft_file
            
            if not input_file:
                ui.notify('Missing alignment file. Cannot resume IQ-TREE.', color='negative')
                return
            
            await update_run_step(run_id, 'iqtree', 'running')
            config.current_iqtree_file = await run_iqtree_pipeline(input_file)
            await update_run_step(run_id, 'iqtree', 'completed', config.current_iqtree_file)
            resumable_step = 'nw_distance'
        
        if resumable_step == 'nw_distance':
            # IQ-TREE file exists, run NW Distance
            if not config.current_iqtree_file:
                ui.notify('Missing IQ-TREE file. Cannot resume NW Distance.', color='negative')
                return
            
            await update_run_step(run_id, 'nw_distance', 'running')
            config.current_nw_distance_file = await run_nw_distance_pipeline(config.current_iqtree_file)
            await update_run_step(run_id, 'nw_distance', 'completed', config.current_nw_distance_file)
        
        # Pipeline completed successfully
        ui.notify('Pipeline resumed and completed successfully!', color='positive')
        
        # Store results in config
        if use_bmge:
            config.pipeline2_data = {
                'fasta_file': config.current_fasta_file,
                'mafft_file': config.current_mafft_file,
                'bmge_file': config.current_bmge_file,
                'iqtree_file': config.current_iqtree_file,
                'nw_distance_file': config.current_nw_distance_file
            }
            show_pipeline2_results(config.pipeline2_data)
        else:
            config.pipeline1_data = {
                'fasta_file': config.current_fasta_file,
                'mafft_file': config.current_mafft_file,
                'iqtree_file': config.current_iqtree_file,
                'nw_distance_file': config.current_nw_distance_file
            }
            show_pipeline1_results(config.pipeline1_data)
        
        # Refresh run history
        await show_run_history()
        
    except Exception as e:
        ui.notify(f'Resume failed: {str(e)}', color='negative')
        await update_run_step(run_id, resumable_step, 'failed')


async def confirm_delete_run(run_id):
    """Show confirmation dialog before deleting a run"""
    with ui.dialog() as dialog, ui.card().classes('p-6'):
        ui.label('Confirm Delete').classes('text-xl font-bold mb-4')
        ui.label(f'Are you sure you want to delete run {run_id}?').classes('mb-4')
        ui.label('This will only delete the metadata, not the generated files.').classes('text-sm text-gray-600 mb-4')
        
        with ui.row().classes('w-full justify-end gap-2'):
            cancel_btn = ui.button('Cancel', on_click=dialog.close)
            styles.apply_default_color(cancel_btn)
            
            async def do_delete():
                dialog.close()
                success = await delete_run(run_id)
                if success:
                    ui.notify('Run deleted successfully', color='positive')
                    await show_run_history()  # Refresh the list
                else:
                    ui.notify('Failed to delete run', color='negative')
            
            delete_btn = ui.button('Delete', on_click=do_delete)
            delete_btn.style('background-color: #EF4444 !important')
    
    dialog.open()
