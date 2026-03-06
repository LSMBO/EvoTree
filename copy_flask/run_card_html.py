"""
Composant HTML réutilisable pour afficher une run card
"""
import os


def generate_run_card_html(state):
    """
    Generate HTML for a run card (always detailed view)
    
    Args:
        state: State dictionary from state.json
    
    Returns:
        HTML string for the run card
    """
    run_id = state.get('run_id', 'Unknown')
    
    status_color = {
        'running': '#3B82F6',
        'completed': '#10B981',
        'failed': '#EF4444',
        'pending': '#F59E0B'
    }
    
    status = state.get('status', 'unknown')
    border_color = status_color.get(status, '#666')
    
    # Read p2_distances.txt if completed
    distances_content = ""
    if status == 'completed':
        pipeline2 = state.get('pipeline2', {})
        distances_file = pipeline2.get('nw_distance_file')
        if distances_file and os.path.exists(distances_file):
            try:
                with open(distances_file, 'r') as f:
                    distances_content = f.read()
            except Exception as e:
                distances_content = f"Error reading file: {e}"
    
    # Base card with colored border - use flex layout if completed
    card_style = "padding: 15px;border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid " + border_color + "; font-family: Arial, sans-serif;"
    
    html = f"""
    <div style="{card_style}">
    """
    
    # If completed, use two-column layout
    if status == 'completed' and distances_content:
        html += """
        <div style="display: flex; gap: 20px;">
            <div>
        """
    
    # Header
    html += f"""
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 10px;">
            Run ID: {run_id}
            <span style="color: {border_color}; margin-left: 10px;">
                [{status.upper()}]
            </span>
        </div>
    """
    
    # Search params
    search_params = state.get('search_params', {})
    if search_params:
        html += f"""
        <div style="color: #666; font-size: 14px; margin: 5px 0;">
            🧬 {search_params.get('search_type', 'N/A')}: {search_params.get('term', 'N/A')}
        </div>
        """
    
    # Creation date
    created_at = state.get('created_at', '')
    if created_at:
        html += f"""
        <div style="color: #666; font-size: 14px; margin: 5px 0;">
            📅 {created_at[:19]}
        </div>
        """
    
    # Current step (if running)
    if status == 'running':
        current_step = state.get('current_step', '')
        if current_step:
            html += f"""
            <div style="color: #3B82F6; font-size: 14px; margin: 10px 0; font-weight: bold;">
                ⏳ {current_step}
            </div>
            """
    
    # Pipeline status
    pipeline1 = state.get('pipeline1', {})
    pipeline2 = state.get('pipeline2', {})
    
    html += """
    <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #E5E7EB;">
    """
    
    # Always show detailed view
    html += f"""
    <div style="margin: 10px 0;">
        <h4 style="color: #9333EA; font-size: 14px; margin-bottom: 5px;">📊 Pipeline 1 (Selection)</h4>
        <div style="padding-left: 15px; font-size: 12px;">
            <div>Status: <strong>{pipeline1.get('status', 'pending')}</strong></div>
            <div style="flex-directon: row; gap: 10px; display: flex;">
                <div>FASTA: {'✅' if pipeline1.get('fasta_file') else '⏳'}</div>
                <div>MAFFT: {'✅' if pipeline1.get('mafft_file') else '⏳'}</div>
                <div>IQ-TREE: {'✅' if pipeline1.get('iqtree_file') else '⏳'}</div>
                <div>Distances: {'✅' if pipeline1.get('nw_distance_file') else '⏳'}</div>
            </div>
        </div>
    </div>
    
    <div style="margin: 10px 0;">
        <h4 style="color: #16A34A; font-size: 14px; margin-bottom: 5px;">🌳 Pipeline 2 (Analysis)</h4>
        <div style="padding-left: 15px; font-size: 12px;">
            <div>Status: <strong>{pipeline2.get('status', 'pending')}</strong></div>
            <div style="flex-directon: row; gap: 10px; display: flex;">
                <div>FASTA: {'✅' if pipeline2.get('bl_fasta_file') else '⏳'}</div>
                <div>MAFFT: {'✅' if pipeline2.get('mafft_file') else '⏳'}</div>
                <div>BMGE: {'✅' if pipeline2.get('bmge_file') else '⏳'}</div>
                <div>IQ-TREE: {'✅' if pipeline2.get('iqtree_file') else '⏳'}</div>
                <div>Distances: {'✅' if pipeline2.get('nw_distance_file') else '⏳'}</div>
            </div>
        </div>
    </div>
    """
    
    html += """
    </div>
    """
    
    # Last updated (no download button in HTML anymore)
    updated_at = state.get('updated_at', '')
    if updated_at:
        html += f"""
        <div style="margin-top: 10px; font-size: 11px; color: #999;">
            Last updated: {updated_at[:19]}
        </div>
        """
    
    # Close first column if two-column layout
    if status == 'completed' and distances_content:
        html += """
            </div>
        """
        
        # Add second column with distances file content
        # Escape HTML characters in distances content
        distances_html = distances_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        html += f"""
            <div style="flex: 1; border-left: 2px solid #E5E7EB; padding-left: 20px;">
                <h4 style="color: #16A34A; font-size: 14px; margin-top: 0; margin-bottom: 10px;">Branch Lengths (p2_distances.txt)</h4>
                <pre style="margin: 0; padding: 10px; background: #F9FAFB; border-radius: 4px; font-size: 11px; font-family: 'Courier New', monospace; overflow-y: auto; max-height: 400px; line-height: 1.4;">{distances_html}</pre>
            </div>
        </div>
        """
    
    html += """
    </div>
    """
    
    return html
