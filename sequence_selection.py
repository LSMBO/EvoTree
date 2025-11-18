
from nicegui import ui
import asyncio
import config
import styles
from length_distribution import create_length_distribution_chart, get_sequence_length
from pipeline import create_fasta
from ncbi import mrna_from_mrna_accession

def show_sequence_selection_form():    
    with config.sequence_selection_container:
        config.sequence_selection_container.set_visibility(True)
        
        # Dynamic label based on search type
        ui.label("Sequence selection").classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        with ui.row().classes('w-full gap-6'):
            with ui.column().classes('flex-1'):
                # Only show database selection for proteins (genes are always NCBI)
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
                    
                config.download_section = ui.row().classes('w-full mt-6 gap-4')
                
            with ui.column().classes('flex-1'):
                ui.label('Length Distribution:').classes('text-lg font-semibold mb-2')
                config.length_distribution_container = ui.column().classes('w-full max-w-full overflow-hidden border border-gray-200 rounded-lg p-4')       
                with config.length_distribution_container:
                    create_length_distribution_chart(config.current_data)
    
        config.download_section = ui.row().classes('w-full gap-6')
        
        # Set initial data based on search type
        if config.current_search_type == 'gene':
            config.current_data = config.ncbi_genes
            config.selected_data = config.selected_genes = config.ncbi_genes
        else:
            config.current_data = config.all_proteins  
            config.selected_data = config.selected_proteins = config.all_proteins
            
        update_button_section()
            
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

def apply_filter(uniprot_only, ncbi_only, having_mrna, min_length, max_length):
    user_min = None
    user_max = None
    
    if min_length:
        try:
            config.search_params['min_length'] = int(min_length)
            user_min = int(min_length)
        except ValueError:
            config.search_params['min_length'] = '*'
    else:
        config.search_params['min_length'] = '*'
        
    if max_length:
        try:
            config.search_params['max_length'] = int(max_length)
            user_max = int(max_length)
        except ValueError:
            config.search_params['max_length'] = '*'
    else:
        config.search_params['max_length'] = '*'

    # Database filtering (only for proteins)
    if config.current_search_type == 'gene':
        # For genes, always use ncbi_genes data
        selected_data = config.ncbi_genes.copy()
    else:
        # For proteins, apply database filter
        if uniprot_only:
            config.search_params['uniprot'] = True
            config.search_params['ncbi'] = False
            selected_data = config.uniprot_proteins.copy()
        elif ncbi_only:
            config.search_params['uniprot'] = False
            config.search_params['ncbi'] = True
            selected_data = config.ncbi_proteins.copy()
        else:
            config.search_params['uniprot'] = True
            config.search_params['ncbi'] = True
            selected_data = config.all_proteins.copy()
    
        if having_mrna:
            config.use_mrna_from_proteins_button.set_visibility(True)
            selected_data = [item for item in selected_data if item.get('mRNA', False)]
        else:
            config.use_mrna_from_proteins_button.set_visibility(False)

    if min_length or max_length:
        try:
            min_len = int(min_length) if min_length else '*'
            max_len = int(max_length) if max_length else '*'
            user_min = min_len
            user_max = max_len
            
            length_filtered = []
            for item in selected_data:
                seq_length = get_sequence_length(item)
                if isinstance(seq_length, str):
                    try:
                        seq_length = int(seq_length)
                    except ValueError:
                        continue
                
                if min_len != '*' and seq_length < min_len:
                    continue
                if max_len != '*' and seq_length > max_len:
                    continue
                length_filtered.append(item)
            
            selected_data = length_filtered
            data_type = "genes" if config.current_search_type == 'gene' else "proteins"
                
        except ValueError:
            ui.notify('Please enter valid numbers for length filters', color='orange')
            return
    
    # Update the appropriate config variables
    if config.current_search_type == 'gene':
        config.selected_genes = selected_data
        config.current_data = selected_data
        config.selected_data = selected_data
    else:
        config.selected_proteins = selected_data
        config.current_data = selected_data
        config.selected_data = selected_data
    
    if config.selected_data:
        config.length_distribution_container.clear()
        with config.length_distribution_container:
            config.length_distribution_container.set_visibility(True)
            create_length_distribution_chart(config.selected_data, user_min, user_max)
        
        update_button_section()
    else:
        data_type = "genes" if config.current_search_type == 'gene' else "proteins"
        ui.notify(f'No {data_type} match your filter criteria', color='orange')

async def show_mrna_sequence_selection():
    try:
        # Prepare mRNA accessions from selected proteins
        mrna_accessions = []
        for entry in config.selected_data:
            if entry.get('mRNA') is None:
                print(f"No mRNA found for entry: {entry.get('primaryAccession', 'Unknown')}")
            else:
                mrna_accessions.append(entry['mRNA'].split('.')[0])
        
        if not mrna_accessions:
            ui.notify('No mRNA accessions found in selected proteins', color='warning')
            return
        
        # Show loading spinner and notify user
        config.loading_spinner.set_visibility(True)
        ui.notify(f'Retrieving {len(mrna_accessions)} mRNA sequences from NCBI...', color='info')
        
        # Run mrna_from_mrna_accession in executor (async)
        loop = asyncio.get_event_loop()
        selected_genes = await loop.run_in_executor(None, mrna_from_mrna_accession, mrna_accessions)
        
        print(f"Retrieved {len(selected_genes)} mRNA sequences from {len(mrna_accessions)} selected proteins")
        
        if selected_genes:
            # Switch to gene mode and update config
            config.current_search_type = 'gene'
            config.ncbi_genes = selected_genes
            config.selected_genes = selected_genes
            config.current_data = selected_genes
            config.selected_data = selected_genes
            
            # Update search params for gene mode
            config.search_params['uniprot'] = False
            config.search_params['ncbi'] = True
            
            # Update UI components
            config.length_distribution_container.clear()
            with config.length_distribution_container:
                config.length_distribution_container.set_visibility(True)
                create_length_distribution_chart(config.selected_data)
            
            # Update button section
            update_button_section()
            
            # Hide the mRNA button since we're now in gene mode
            config.use_mrna_from_proteins_button.set_visibility(False)
            
            # Rebuild the sequence selection form to reflect gene mode
            config.sequence_selection_container.clear()
            show_sequence_selection_form()
            
            ui.notify(f'Successfully retrieved {len(selected_genes)} mRNA sequences!', color='positive')
        else:
            ui.notify('No mRNA sequences could be retrieved', color='warning')
        
    except Exception as e:
        print(f"Error retrieving mRNA sequences: {e}")
        ui.notify(f'Error retrieving mRNA sequences: {str(e)}', color='negative')
        
    finally:
        # Always hide loading spinner
        config.loading_spinner.set_visibility(False)

def update_button_section():
    species_list = set()
    
    # Handle different data structures for genes vs proteins
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

    species_count = len(species_list)
    
    config.download_section.clear()
    data_type = "genes" if config.current_search_type == 'gene' else "sequences"
    stats = f"**Selection**: {len(config.selected_data)} {data_type} from {species_count} species"
    
    with config.download_section:
        with ui.row().classes('w-full gap-4'):
            ui.markdown(stats).classes('text-lg')
        with ui.row().classes('w-full gap-4'):
            create_fasta_btn = ui.button("Download FASTA", on_click=lambda: create_fasta(download=True)).classes('flex-1')
            styles.apply_purple_color(create_fasta_btn)
            styles.apply_download_icon(create_fasta_btn)

            species_list_btn = ui.button(f"Species List", on_click=lambda: show_species_list(species_list)).classes('flex-1')
            styles.apply_default_color(species_list_btn)

            pipeline_btn = ui.button('Build Phylogenetic Tree', 
                                    on_click=lambda: handle_pipeline1()).classes('flex-1')
            styles.apply_violet_color(pipeline_btn)
            styles.apply_play_icon(pipeline_btn)

async def handle_pipeline1():
    try:
        # Reset all pipeline containers before starting new pipeline
        config.pipeline1_container.clear()
        config.pipeline1_container.set_visibility(False)
        
        config.pipeline2_launcher_container.clear()
        config.pipeline2_launcher_container.set_visibility(False)
        
        config.pipeline2_container.clear()
        config.pipeline2_container.set_visibility(False)
        
        config.pipeline2_results.clear()
        config.pipeline2_results.set_visibility(False)

        from pipeline import run_full_pipeline
        config.pipeline1_data = await run_full_pipeline(config.pipeline1_container, run_bmge=False)
        
        if config.pipeline1_data != "failed":
            ui.notify('Pipeline completed successfully!', color='positive')
            from pipeline_results import show_pipeline1_results
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
    