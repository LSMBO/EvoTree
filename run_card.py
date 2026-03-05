"""
Run Card Component - Reusable card to display run information
"""
from nicegui import ui
import config
from datetime import datetime


def create_run_card(run_summary, show_actions=False, show_details_only=False, on_view_details=None, on_resume=None, on_delete=None):
    """
    Create a reusable run card component
    
    Args:
        run_summary: Dict with run summary information
        show_actions: Whether to show all action buttons (View/Resume/Delete)
        show_details_only: Whether to show only the View Details button
        on_view_details: Callback for view details button
        on_resume: Callback for resume button
        on_delete: Callback for delete button
    """
    # Determine status color
    status_colors = {
        'completed': 'green',
        'running': 'blue',
        'failed': 'red',
        'initialized': 'orange',
    }
    status_color = status_colors.get(run_summary.get('status', 'unknown'), 'gray')
    
    # Format creation date
    try:
        created_dt = datetime.fromisoformat(run_summary['created_at'])
        created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        created_str = run_summary.get('created_at', 'Unknown')
    
    # Determine search type icon
    search_type = run_summary.get('search_type', 'protein')
    search_icon = '🧬' if search_type == 'protein' else '🔬'
    
    # Determine pipeline type
    pipeline_type = run_summary.get('pipeline_type', 'selection')
    if pipeline_type == 'selection':
        pipeline_badge = '📊 Pipeline'
        pipeline_color = '#9333EA'  # Purple
        pipeline_desc = 'One sequence per species'
    else:  # 'analysis'
        pipeline_badge = '🌳 Analysis Pipeline'  
        pipeline_color = '#16A34A'  # Green
        pipeline_desc = 'With BMGE filtering'
    
    card_border_color = pipeline_color
    
    with ui.card().classes('w-full p-4 rounded-lg shadow-md hover:shadow-lg transition-shadow').style(f'border: 2px solid {card_border_color}'):
        with ui.row().classes('w-full justify-between items-start'):
            # Left side: Run info
            with ui.column().classes('flex-grow gap-2'):
                # Pipeline type badge
                ui.badge(pipeline_badge, color=pipeline_color).classes('text-sm mb-1')
                
                # Run ID and status
                with ui.row().classes('items-center gap-2'):
                    ui.label(f'Run ID: {run_summary.get("run_id", "Unknown")}').classes('text-lg font-bold')
                    ui.badge(run_summary.get('status', 'unknown'), color=status_color).classes('text-sm')
                
                # Search details
                ui.label(f'{search_icon} {search_type.capitalize()}: {run_summary.get("term", "Unknown")}').classes('text-md mt-1')
                
                if run_summary.get('taxonomy'):
                    ui.label(f'🌍 Taxonomy: {run_summary["taxonomy"]}').classes('text-sm text-gray-600')
                
                # Statistics
                with ui.row().classes('gap-4 mt-2'):
                    ui.label(f'📊 {run_summary.get("num_sequences", 0)} sequences').classes('text-sm text-gray-600')
                    ui.label(f'🦋 {run_summary.get("num_species", 0)} species').classes('text-sm text-gray-600')
                    completed = run_summary.get('completed_steps', 0)
                    total = run_summary.get('total_steps', 0)
                    ui.label(f'✓ {completed}/{total} steps').classes('text-sm text-gray-600')
                
                ui.label(f'📅 {created_str}').classes('text-xs text-gray-500 mt-1')
            
            # Right side: Actions (if enabled)
            if show_actions or show_details_only:
                with ui.column().classes('gap-2'):
                    if on_view_details:
                        view_btn = ui.button('View Details', on_click=on_view_details)
                        view_btn.classes('px-4 py-2 text-sm')
                        view_btn.style('background-color: #6B7280 !important')
                    
                    if show_actions:  # Only show Resume/Delete if full actions enabled
                        if on_resume and run_summary.get('status') != 'completed':
                            resume_btn = ui.button('Resume', on_click=on_resume)
                            resume_btn.props('icon=play_arrow')
                            resume_btn.classes('px-4 py-2 text-sm')
                            resume_btn.style(f'background-color: {config.VIOLET_COLOR} !important')
                        
                        if on_delete:
                            delete_btn = ui.button(icon='delete', on_click=on_delete)
                            delete_btn.props('flat dense color=red')


def create_run_card_from_metadata(metadata, show_actions=False, show_details_only=False, on_view_details=None, on_resume=None, on_delete=None):
    """
    Create a run card from full metadata (not just summary)
    """
    # Count only truly completed steps (exclude skipped)
    completed_steps = sum(
        1 for step in metadata['steps'].values() 
        if step['status'] == 'completed'
    )
    
    # Total steps = all steps that are not skipped
    total_steps = sum(
        1 for step in metadata['steps'].values() 
        if step['status'] != 'skipped'
    )
    
    # Get pipeline type from config
    pipeline_type = metadata.get('pipeline_config', {}).get('pipeline_type', 'selection')
    
    summary = {
        'run_id': metadata['run_id'],
        'created_at': metadata['created_at'],
        'status': metadata['status'],
        'search_type': metadata['search_params']['search_type'],
        'term': metadata['search_params']['term'],
        'taxonomy': metadata['search_params']['taxonomy'],
        'num_sequences': metadata['stats']['num_sequences'],
        'num_species': metadata['stats']['num_species'],
        'completed_steps': completed_steps,
        'total_steps': total_steps,
        'pipeline_type': pipeline_type
    }
    
    return create_run_card(summary, show_actions, show_details_only, on_view_details, on_resume, on_delete)
