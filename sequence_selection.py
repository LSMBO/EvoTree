
from nicegui import ui
import asyncio
import config
import styles
from length_distribution import create_length_distribution_chart, get_sequence_length
from pipeline import create_fasta, run_full_pipeline
from pipeline_results import show_pipeline1_results
from ncbi import mrna_from_mrna_accession
from Bio import SeqIO
from io import StringIO

def show_sequence_selection_form():    
    with config.sequence_selection_container:
        config.sequence_selection_container.set_visibility(True)
        
        ui.label("Sequence selection").classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        with ui.tabs().classes('w-full') as tabs:
            database_tab = ui.tab('Sequences from the search')
            custom_tab = ui.tab('Custom FASTA')
        
        tabs.on_value_change(lambda e: switch_to_tab(e.value, database_tab))
        
        with ui.tab_panels(tabs, value=database_tab).classes('w-full'):
            with ui.tab_panel(database_tab):
                with ui.row().classes('w-full gap-6'):
                    with ui.column().classes('flex-1'):
                        if config.current_search_type == 'protein':
                            ui.label('Database selection:').classes('text-lg font-semibold mb-2')
                            with ui.row().classes('w-full gap-6'):
                                all_checkbox = ui.checkbox('All databases', value=True).classes('text-lg')
                                uniprot_only_checkbox = ui.checkbox('UniProtKB', value=False).classes('text-lg')
                                ncbi_only_checkbox = ui.checkbox('NCBI', value=False).classes('text-lg')
                                having_mrna_checkbox = ui.checkbox('Having mRNA', value=False).classes('text-lg')
                        else:
                            all_checkbox = ui.checkbox('All databases', value=True).classes('hidden')
                            uniprot_only_checkbox = ui.checkbox('UniProtKB', value=False).classes('hidden')
                            ncbi_only_checkbox = ui.checkbox('NCBI', value=False).classes('hidden')
                            having_mrna_checkbox = ui.checkbox('Having mRNA', value=False).classes('hidden')

                        with ui.row().classes('w-full gap-4 mb-3 items-center'):
                            ui.label('Length filter (optional):').classes('text-lg font-semibold')
                            min_length_input = ui.input('Min length (residues)').classes('flex-grow')
                            max_length_input = ui.input('Max length (residues)').classes('flex-grow')
                        
                        with ui.row().classes('w-full gap-4'):                       
                            filter_btn = ui.button('Select', on_click=lambda: apply_filter(
                                uniprot_only_checkbox.value,
                                ncbi_only_checkbox.value,
                                having_mrna_checkbox.value,
                                min_length_input.value,
                                max_length_input.value
                            )).classes('w-full')
                            styles.apply_default_color(filter_btn)
                            styles.apply_filter_icon(filter_btn)
                            
                        config.use_mrna_from_proteins_button = ui.button(
                            'Use mRNA sequences of the selected proteins', 
                            on_click=lambda: show_mrna_sequence_selection()
                        ).classes('w-full mt-4')
                        config.use_mrna_from_proteins_button.set_visibility(False)
                        styles.apply_violet_color(config.use_mrna_from_proteins_button)
                        
                    with ui.column().classes('flex-1'):
                        ui.label('Length Distribution:').classes('text-lg font-semibold mb-2')
                        config.length_distribution_container = ui.column().classes('w-full max-w-full overflow-hidden border border-gray-200 rounded-lg p-4')       
                        with config.length_distribution_container:
                            create_length_distribution_chart(config.selected_data)
                
                config.database_buttons_section = ui.column().classes('w-full mt-6')
            
            with ui.tab_panel(custom_tab):
                ui.label('Upload your FASTA file:').classes('text-lg font-semibold mb-4')
                
                with ui.row().classes('w-full gap-2 items-center'):
                    custom_upload = ui.upload(
                        on_upload=lambda e: handle_custom_fasta_upload(e),
                        auto_upload=True,
                        multiple=False,
                        on_rejected=lambda: ui.notify('Invalid file type. Please upload a FASTA file.', color='warning')
                    ).props('accept=".fasta,.fa,.faa,.fna" max-files="1"')
                    custom_upload.classes('flex-grow')
                    
                    clear_btn = ui.button(icon='close', on_click=lambda: custom_upload.reset()).props('flat round dense')
                    clear_btn.classes('ml-2')
                    clear_btn.tooltip('Remove file')
                
                ui.markdown('**Accepted formats**: .fasta, .fa, .faa, .fna').classes('text-sm text-gray-600 mt-2')
                
                config.custom_buttons_section = ui.column().classes('w-full mt-6')
        
        # Initialize data
        initialize_sequence_data()
            
        def ensure_single_selection(selected_checkbox):
            if selected_checkbox == 'all' and all_checkbox.value:
                uniprot_only_checkbox.set_value(False)
                ncbi_only_checkbox.set_value(False)
            elif selected_checkbox == 'uniprot' and uniprot_only_checkbox.value:
                all_checkbox.set_value(False)
                ncbi_only_checkbox.set_value(False)
            elif selected_checkbox == 'ncbi' and ncbi_only_checkbox.value:
                all_checkbox.set_value(False)
                uniprot_only_checkbox.set_value(False)
            
            if not (all_checkbox.value or uniprot_only_checkbox.value or ncbi_only_checkbox.value):
                all_checkbox.set_value(True)
                
        all_checkbox.on('update:model-value', lambda: ensure_single_selection('all'))
        uniprot_only_checkbox.on('update:model-value', lambda: ensure_single_selection('uniprot'))
        ncbi_only_checkbox.on('update:model-value', lambda: ensure_single_selection('ncbi'))


# =============================================================================
# TAB MANAGEMENT
# =============================================================================

def switch_to_tab(tab_value, database_tab):
    if tab_value == database_tab:
        switch_to_database_tab()
    else:
        switch_to_custom_tab()

def switch_to_database_tab():
    config.select_sequence_active_tab = 'sequences_from_search'
    
    if config.current_search_type == 'gene':
        config.selected_data = config.ncbi_genes
    else:
        config.selected_data = config.all_proteins
    
    # Update the UI buttons to reflect database data
    update_database_buttons()

def switch_to_custom_tab():
    config.select_sequence_active_tab = 'custom_fasta'

def initialize_sequence_data():
    if config.current_search_type == 'gene':
        config.selected_data = config.ncbi_genes
    else:
        config.selected_data = config.all_proteins
    
    config.database_selected_data = config.selected_data
        
    update_database_buttons()
    
    config.selected_data = []
    update_custom_buttons()

def restore_database_data():
    if config.current_search_type == 'gene':
        config.selected_data = config.ncbi_genes
    else:
        config.selected_data = config.all_proteins


# =============================================================================
# FILTER MANAGEMENT
# =============================================================================

def apply_filter(uniprot_only, ncbi_only, having_mrna, min_length, max_length):
    user_min, user_max = parse_length_filters(min_length, max_length)
    
    selected_data = filter_by_database(uniprot_only, ncbi_only, having_mrna)
    
    if min_length or max_length:
        selected_data = filter_by_length(selected_data, user_min, user_max)
        if not selected_data:
            data_type = "genes" if config.current_search_type == 'gene' else "proteins"
            ui.notify(f'No {data_type} match your filter criteria', color='orange')
            return
    
    update_selected_data(selected_data)
    
    update_length_chart(selected_data, user_min, user_max)
    update_database_buttons()

def parse_length_filters(min_length, max_length):
    user_min = None
    user_max = None
    
    if min_length:
        try:
            config.selection_params['min_length'] = int(min_length)
            user_min = int(min_length)
        except ValueError:
            config.selection_params['min_length'] = '*'
    else:
        config.selection_params['min_length'] = '*'
        
    if max_length:
        try:
            config.selection_params['max_length'] = int(max_length)
            user_max = int(max_length)
        except ValueError:
            config.selection_params['max_length'] = '*'
    else:
        config.selection_params['max_length'] = '*'
    
    return user_min, user_max

def filter_by_database(uniprot_only, ncbi_only, having_mrna):
    if config.current_search_type == 'gene':
        return config.ncbi_genes.copy()
    
    if uniprot_only:
        config.selection_params['uniprot'] = True
        config.selection_params['ncbi'] = False
        selected_data = config.uniprot_proteins.copy()
    elif ncbi_only:
        config.selection_params['uniprot'] = False
        config.selection_params['ncbi'] = True
        selected_data = config.ncbi_proteins.copy()
    else:
        config.selection_params['uniprot'] = True
        config.selection_params['ncbi'] = True
        selected_data = config.all_proteins.copy()

    if having_mrna:
        config.use_mrna_from_proteins_button.set_visibility(True)
        selected_data = [item for item in selected_data if item.get('mRNA', False)]
    else:
        config.use_mrna_from_proteins_button.set_visibility(False)
    
    return selected_data

def filter_by_length(selected_data, min_len, max_len):
    try:
        length_filtered = []
        for item in selected_data:
            seq_length = get_sequence_length(item)
            if isinstance(seq_length, str):
                try:
                    seq_length = int(seq_length)
                except ValueError:
                    continue
            
            if min_len != '*' and min_len and seq_length < min_len:
                continue
            if max_len != '*' and max_len and seq_length > max_len:
                continue
            length_filtered.append(item)
        
        return length_filtered
    except ValueError:
        ui.notify('Please enter valid numbers for length filters', color='orange')
        return []

def update_selected_data(selected_data):
    config.selected_data = selected_data

def update_length_chart(selected_data, user_min, user_max):
    config.length_distribution_container.clear()
    with config.length_distribution_container:
        config.length_distribution_container.set_visibility(True)
        create_length_distribution_chart(selected_data, user_min, user_max)


# =============================================================================
# CUSTOM FASTA MANAGEMENT
# =============================================================================

async def show_mrna_sequence_selection():
    try:
        mrna_accessions = []
        for entry in config.selected_data:
            if entry.get('mRNA') is None:
                print(f"No mRNA found for entry: {entry.get('primaryAccession', 'Unknown')}")
            else:
                mrna_accessions.append(entry['mRNA'].split('.')[0])
        
        if not mrna_accessions:
            ui.notify('No mRNA accessions found in selected proteins', color='warning')
            return
        
        config.loading_spinner.set_visibility(True)
        ui.notify(f'Retrieving {len(mrna_accessions)} mRNA sequences from NCBI...', color='info')
        
        loop = asyncio.get_event_loop()
        selected_genes = await loop.run_in_executor(None, mrna_from_mrna_accession, mrna_accessions)
        
        print(f"Retrieved {len(selected_genes)} mRNA sequences from {len(mrna_accessions)} selected proteins")
        
        if selected_genes:
            # Switch to gene mode and update config
            config.current_search_type = 'gene'
            config.ncbi_genes = selected_genes
            config.selected_data = selected_genes
            
            # Update search params for gene mode
            config.selection_params['uniprot'] = False
            config.selection_params['ncbi'] = True
            
            config.length_distribution_container.clear()
            with config.length_distribution_container:
                config.length_distribution_container.set_visibility(True)
                create_length_distribution_chart(config.selected_data)
            
            update_database_buttons()
            
            config.use_mrna_from_proteins_button.set_visibility(False)
            
            config.sequence_selection_container.clear()
            show_sequence_selection_form()
            
            ui.notify(f'Successfully retrieved {len(selected_genes)} mRNA sequences!', color='positive')
        else:
            ui.notify('No mRNA sequences could be retrieved', color='warning')
        
    except Exception as e:
        print(f"Error retrieving mRNA sequences: {e}")
        ui.notify(f'Error retrieving mRNA sequences: {str(e)}', color='negative')
        
    finally:
        config.loading_spinner.set_visibility(False)

def read_loaded_fasta(content):
    fasta_entries = []
    fasta_io = StringIO(content)

    for record in SeqIO.parse(fasta_io, "fasta"):
        try:
            header_parts = record.description.split(' ', 1)
            
            accession = header_parts[0] if len(header_parts) > 0 else record.id
            name = header_parts[1].strip() if len(header_parts) > 1 else 'Unknown'
            
            accession_parts = accession.split('_')
            scientific_name = ' '.join(accession_parts[:-1]) if len(accession_parts) > 1 else 'Unknown'
            
            entry = {
                'accession': accession,
                'scientific_name': scientific_name,
                'name': name,
                'length': len(record.seq),
                'sequence': str(record.seq)
            }
            fasta_entries.append(entry)
        except Exception as e:
            return f"Invalid header format: {record.description}"

    return fasta_entries

async def handle_custom_fasta_upload(e):
    try:
        content_bytes = await e.file.read()
        content = content_bytes.decode('utf-8')
        filename = e.file.name if hasattr(e.file, 'name') else 'uploaded.fasta'
        
        fasta_entries = read_loaded_fasta(content)
        if isinstance(fasta_entries, str):
            ui.notify(fasta_entries, color='negative')
            return
        
        # Store custom FASTA for upload to server
        config.custom_fasta_content = content
        config.custom_fasta_filename = filename
        
        # Store parsed data in selected_data
        config.selected_data = fasta_entries
        
        update_custom_buttons()
        ui.notify(f'FASTA file "{filename}" loaded successfully with {len(fasta_entries)} sequences!', color='positive')

    except Exception as ex:
        print(f"Error uploading FASTA: {ex}")
        import traceback
        traceback.print_exc()
        ui.notify(f'Error loading FASTA file: {str(ex)}', color='negative')


# =============================================================================
# BUTTON SECTION MANAGEMENT
# =============================================================================


def update_database_buttons():
    species_list = get_species_list()
    species_count = len(species_list)
    data_type = "genes" if config.current_search_type == 'gene' else "sequences"
    
    config.database_buttons_section.clear()
    with config.database_buttons_section:
        with ui.row().classes('w-full gap-4 mb-2'):
            ui.markdown(f"**Selection**: {len(config.selected_data)} {data_type} from {species_count} species").classes('text-lg')
        
        with ui.row().classes('w-full gap-4'):
            create_fasta_btn = ui.button("Download FASTA", on_click=lambda: create_fasta(download=True)).classes('flex-1')
            styles.apply_purple_color(create_fasta_btn)
            styles.apply_download_icon(create_fasta_btn)

            species_list_btn = ui.button(f"Species List", on_click=lambda: show_species_list(species_list)).classes('flex-1')
            styles.apply_default_color(species_list_btn)

            pipeline_btn = ui.button('Build Phylogenetic Tree', on_click=lambda: handle_pipeline1()).classes('flex-1')
            styles.apply_violet_color(pipeline_btn)
            styles.apply_play_icon(pipeline_btn)

def get_species_list():
    species_list = set()
    
    if config.current_search_type == 'gene':
        for gene in config.selected_data:
            scientific_name = gene.get('scientific_name', 'Unknown')
            taxid = gene.get('taxid', 'Unknown')
            species_list.add((scientific_name, taxid))
    else:
        for protein in config.selected_data:
            scientific_name = protein.get('organism', {}).get('scientificName', protein.get('scientific_name', 'Unknown'))
            taxid = protein.get('organism', {}).get('taxonId', protein.get('taxid', 'Unknown'))
            species_list.add((scientific_name, taxid))
    
    return species_list

def update_custom_buttons():
    config.custom_buttons_section.clear()
    # Check if we have custom FASTA content uploaded
    has_data = (hasattr(config, 'custom_fasta_content') and 
                config.custom_fasta_content and 
                config.selected_data and 
                len(config.selected_data) > 0)
    
    if has_data:
        species_list = get_custom_species_list()
        render_custom_buttons_enabled(species_list)
    else:
        render_custom_buttons_disabled()

def get_custom_species_list():
    species_list = set()
    for entry in config.selected_data:
        scientific_name = entry.get('scientific_name', 'Unknown')
        species_list.add(scientific_name)
    return species_list

def render_custom_buttons_enabled(species_list):
    with config.custom_buttons_section:
        with ui.row().classes('w-full gap-4 mb-2'):
            ui.markdown(f"**Selection**: {len(config.selected_data)} sequences from {len(species_list)} species").classes('text-lg')
        
        with ui.row().classes('w-full gap-4'):
            species_list_btn = ui.button(f"Species List", on_click=lambda: show_species_list_custom(species_list)).classes('flex-1')
            styles.apply_default_color(species_list_btn)

            pipeline_btn = ui.button('Build Phylogenetic Tree', on_click=lambda: handle_pipeline1()).classes('flex-1')
            styles.apply_violet_color(pipeline_btn)
            styles.apply_play_icon(pipeline_btn)

def render_custom_buttons_disabled():
    with config.custom_buttons_section:
        with ui.row().classes('w-full gap-4'):
            species_list_btn = ui.button(f"Species List").classes('flex-1')
            species_list_btn.set_enabled(False)
            styles.apply_default_color(species_list_btn)

            pipeline_btn = ui.button('Build Phylogenetic Tree').classes('flex-1')
            pipeline_btn.set_enabled(False)
            styles.apply_violet_color(pipeline_btn)
            styles.apply_play_icon(pipeline_btn)


# =============================================================================
# DIALOG MANAGEMENT
# =============================================================================

def show_species_list_custom(species_list):
    sorted_species_list = sorted(species_list)
    with ui.dialog() as dialog, ui.card().classes('w-96 max-h-96 overflow-y-auto'):
        ui.label('Species List').classes('text-xl font-bold mb-4')
        species_text = ""
        for scientific_name in sorted_species_list:
            ui.label(scientific_name).classes('text-md mb-0')
            species_text += f"{scientific_name}\n"
        with ui.row().classes('mt-4 w-full gap-4'):
            ui.button('Copy', on_click=lambda: ui.run_javascript(f'navigator.clipboard.writeText(`{species_text.strip()}`)')).classes('flex-1')
            ui.button('Close', on_click=dialog.close).classes('flex-1')
    dialog.open()

async def handle_pipeline1():
    try:
        config.pipeline1_container.clear()
        config.pipeline1_container.set_visibility(False)
        
        config.pipeline2_launcher_container.clear()
        config.pipeline2_launcher_container.set_visibility(False)
        
        config.pipeline2_container.clear()
        config.pipeline2_container.set_visibility(False)
        
        config.pipeline2_results.clear()
        config.pipeline2_results.set_visibility(False)

        config.pipeline1_data = await run_full_pipeline(config.pipeline1_container, run_bmge=False)
        
        if config.pipeline1_data != "failed":
            ui.notify('Pipeline completed successfully!', color='positive')

            show_pipeline1_results(config.pipeline1_data)
        else:
            ui.notify('Pipeline failed', color='negative')
    except Exception as e:
        ui.notify(f'Pipeline error: {str(e)}', color='negative')

def show_species_list(species_list):
    sorted_species_list = sorted(species_list, key=lambda x: x[0])
    with ui.dialog() as dialog, ui.card().classes('w-96 max-h-96 overflow-y-auto'):
        ui.label('Species List').classes('text-xl font-bold mb-4')
        with ui.row().classes('mt-4 w-full gap-4'):
            ui.button('Copy', on_click=lambda: ui.run_javascript(f'navigator.clipboard.writeText(`{species_text.strip()}`)')).classes('flex-1')
            ui.button('Close', on_click=dialog.close).classes('flex-1')
        species_text = ""
        for scientific_name, _ in sorted_species_list:
            ui.label(scientific_name).classes('text-md mb-0')
            species_text += f"{scientific_name}\n"
        
    dialog.open()
    