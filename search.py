import asyncio
import traceback
from nicegui import ui
import config
from uniprot import fetch_taxonomy, fetch_uniprot_data, fetch_rank
from ncbi import fetch_ncbi_proteins, fetch_ncbi_genes

# Variable globale pour gérer l'état de recherche
current_search_task = None

def reset_search_state():
    """Reset all search-related UI components and config"""
    # Clear containers
    config.table_container.clear()
    config.table_container.set_visibility(False)
    
    config.sequence_selection_container.clear()
    config.sequence_selection_container.set_visibility(False)
    
    config.length_distribution_container.clear()
    config.length_distribution_container.set_visibility(False)
    
    config.pipeline1_container.clear()
    config.pipeline1_container.set_visibility(False)
    
    config.pipeline2_launcher_container.clear()
    config.pipeline2_launcher_container.set_visibility(False)
    
    config.pipeline2_container.clear()
    config.pipeline2_container.set_visibility(False)
    
    config.pipeline2_results.clear()
    config.pipeline2_results.set_visibility(False)
    
    # Reset config data
    config.uniprot_proteins = []
    config.ncbi_proteins = []
    config.ncbi_genes = []
    config.all_proteins = []
    config.selected_proteins = []
    config.selected_genes = []
    
    # Hide loading spinner
    config.loading_spinner.set_visibility(False)

def start_search():
    """Start a new search - reset state and show loading"""
    global current_search_task
    
    # Cancel any ongoing search
    if current_search_task and not current_search_task.done():
        current_search_task.cancel()
    
    # Reset all UI components
    reset_search_state()
    
    # Show loading spinner
    config.loading_spinner.set_visibility(True)

def finish_search(success=True):
    """Finish search - hide loading and show table if successful"""
    config.loading_spinner.set_visibility(False)
    if success:
        config.table_container.set_visibility(True)

def extract_nucleotide_reference(cross_references):
    """
    Extract nucleotide reference from UniProt cross-references
    """
    if not cross_references:
        return None
    
    refseq_ref = None
    mrna_ref = None
    
    for ref in cross_references:
        database = ref.get('database', '')
        ref_id = ref.get('id', '')
        
        if database == 'RefSeq':
            properties = ref.get('properties', [])
            for prop in properties:
                if prop.get('key') == 'NucleotideSequenceId':
                    refseq_ref = prop.get('value')
            
        elif database == 'EMBL':
            properties = ref.get('properties', [])
            for prop in properties:
                if prop.get('key') == 'MoleculeType' and prop.get('value') == 'mRNA':
                    mrna_ref = ref_id
                    break
    
    return refseq_ref or mrna_ref

async def update_taxonomic_rank(items, rank_dict, selected_rank, taxid_key, name_key):
    loop = asyncio.get_event_loop()
    processed_items = []
    
    for item in items:
        # Extract taxid and scientific name using the provided keys
        if '.' in taxid_key:  # Handle nested keys like 'organism.taxonId'
            keys = taxid_key.split('.')
            taxid = item
            for key in keys:
                taxid = taxid.get(key) if isinstance(taxid, dict) else None
        else:
            taxid = item.get(taxid_key)
            
        if '.' in name_key:  # Handle nested keys like 'organism.scientificName'
            keys = name_key.split('.')
            scientific_name = item
            for key in keys:
                scientific_name = scientific_name.get(key) if isinstance(scientific_name, dict) else None
        else:
            scientific_name = item.get(name_key)
        
        # Only process rank if the scientific name has more than 2 words (not species level)
        if scientific_name and scientific_name.count(' ') > 1:
            if taxid in rank_dict:
                updated_taxid, updated_scientific_name = rank_dict[taxid]
            else:
                updated_taxid, updated_scientific_name = await loop.run_in_executor(None, fetch_rank, taxid, selected_rank)
                rank_dict[taxid] = (updated_taxid, updated_scientific_name)
            
            if not updated_taxid:
                continue
                
            # Update the item with new taxonomic info
            if '.' in taxid_key:
                keys = taxid_key.split('.')
                target = item
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = updated_taxid
            else:
                item[taxid_key] = updated_taxid
                
            if '.' in name_key:
                keys = name_key.split('.')
                target = item
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = updated_scientific_name
            else:
                item[name_key] = updated_scientific_name
        
        processed_items.append(item)
    
    return processed_items

def count_species(items, taxid_key):
    taxids = set()
    for item in items:
        if '.' in taxid_key:
            keys = taxid_key.split('.')
            taxid = item
            for key in keys:
                taxid = taxid.get(key) if isinstance(taxid, dict) else None
        else:
            taxid = item.get(taxid_key)
        taxids.add(taxid if taxid else 'Unknown')
    return len(taxids)

async def search_genes(gene_name, taxonomy_name, selected_rank):
    global current_search_task
    
    if not gene_name:
        ui.notify('Please enter a gene name.')
        return {'success': False, 'error': 'No gene name provided'}
    
    # Set search type for unified selection system
    config.current_search_type = 'gene'
    
    # Start new search
    start_search()
    
    try:
        current_search_task = asyncio.current_task()
        config.search_params['uniprot'] = False
        config.search_params['ncbi'] = True
        config.search_params['term'] = gene_name
        gene_rank_dict = {}
        
        loop = asyncio.get_event_loop()
        
        # Get taxonomy if specified
        ui.notify('Searching in NCBI...', color='info')
        taxo = await loop.run_in_executor(None, fetch_taxonomy, taxonomy_name) if taxonomy_name else None
        taxid = taxo['taxid'] if taxo else None
        config.search_params['taxid'] = taxid     
        
        # Fetch genes from NCBI
        ncbi_genes = await loop.run_in_executor(None, fetch_ncbi_genes, gene_name, taxid)
        
        # Update taxonomic ranks
        ncbi_genes_correct_rank = await update_taxonomic_rank(
            ncbi_genes, gene_rank_dict, selected_rank, 'taxid', 'scientific_name'
        )
        
        print("NCBI search completed.")
        config.ncbi_genes = ncbi_genes_correct_rank
        config.selected_genes = config.ncbi_genes
        config.current_data = config.ncbi_genes
        config.selected_data = config.ncbi_genes

        # Count species
        ncbi_species_count = count_species(config.ncbi_genes, 'taxid')

        # Display results
        with config.table_container:
            ui.label('Search Results').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}]')
            search_results_text = f'Search results for "{gene_name}"'
            if taxonomy_name:
                search_results_text += f' in taxonomy "{taxonomy_name}"'
            ui.markdown(search_results_text)
            ui.markdown(
                f'Found **{len(config.ncbi_genes)}** entries '
                f'in **{ncbi_species_count}** species '
            )

        # Finish search successfully
        finish_search(success=True)
        
        return {
            'success': True,
            'gene_name': gene_name,
            'taxonomy_name': taxonomy_name,
            'ncbi_genes': ncbi_genes_correct_rank,
            'ncbi_species_count': ncbi_species_count,
            'total_species': ncbi_species_count
        }
                                 
    except asyncio.CancelledError:
        # Search was cancelled, reset state
        reset_search_state()
        print("Gene search was cancelled")
        return {'success': False, 'error': 'Search was cancelled'}
        
    except Exception as e:
        # Print full traceback to console for debugging
        print("Full traceback:")
        print(traceback.format_exc())
        
        # Display error in UI
        config.table_container.clear()
        error_message = f"**Error:** {str(e)}\n\n**Traceback:**\n```\n{traceback.format_exc()}\n```"
        with config.table_container:
            ui.markdown(error_message)
            
        # Finish search with error
        finish_search(success=True)  # Show table with error message
        
        return {'success': False, 'error': str(e)}

async def search_protein(protein_name, taxonomy_name, selected_rank):
    global current_search_task
    
    if not protein_name:
        ui.notify('Please enter a protein name.')
        return {'success': False, 'error': 'No protein name provided'}
    
    # Set search type for unified selection system
    config.current_search_type = 'protein'
    
    # Start new search
    start_search()
    
    try:
        current_search_task = asyncio.current_task()
        
        config.search_params['uniprot'] = True
        config.search_params['ncbi'] = True
        config.search_params['term'] = protein_name
        protein_rank_dict = {}
        
        loop = asyncio.get_event_loop()
        
        # Get taxonomy if specified
        taxo = await loop.run_in_executor(None, fetch_taxonomy, taxonomy_name) if taxonomy_name else None
        taxid = taxo['taxid'] if taxo else None
        config.search_params['taxid'] = taxid
        
        # Search in UniProt
        ui.notify('Searching in UniProtKB...', color='info')
        uniprot_proteins = await loop.run_in_executor(None, fetch_uniprot_data, protein_name, taxid)
                
        # Update taxonomic ranks for UniProt proteins
        uniprot_proteins_correct_rank = await update_taxonomic_rank(
            uniprot_proteins, protein_rank_dict, selected_rank, 'organism.taxonId', 'organism.scientificName'
        )
        
        # Add mRNA information for UniProt proteins
        for prot in uniprot_proteins_correct_rank:
            original_crossrefs = prot.get('uniProtKBCrossReferences', [])
            nucleotide_ref = extract_nucleotide_reference(original_crossrefs)
            prot['mRNA'] = nucleotide_ref
            
        print("UniProt search completed.")
        
        # Search in NCBI
        ui.notify('Searching in NCBI...', color='info')
        ncbi_proteins = await loop.run_in_executor(None, fetch_ncbi_proteins, protein_name, taxid)
        
        # Update taxonomic ranks for NCBI proteins
        ncbi_proteins_correct_rank = await update_taxonomic_rank(
            ncbi_proteins, protein_rank_dict, selected_rank, 'taxid', 'scientific_name'
        )
        
        print("NCBI search completed.")
        
        # Store results in config
        config.uniprot_proteins = uniprot_proteins_correct_rank
        config.ncbi_proteins = ncbi_proteins_correct_rank
        config.all_proteins = uniprot_proteins_correct_rank + ncbi_proteins_correct_rank
        config.selected_proteins = config.all_proteins
        config.current_data = config.all_proteins
        config.selected_data = config.all_proteins

        # Count species
        uniprot_species_count = count_species(config.uniprot_proteins, 'organism.taxonId')
        ncbi_species_count = count_species(config.ncbi_proteins, 'taxid')
        
        # Count total unique species
        all_taxids = set()
        for protein in config.all_proteins:
            taxid = protein.get('organism', {}).get('taxonId') or protein.get('taxid', 'Unknown')
            all_taxids.add(taxid)
        total_species = len(all_taxids)

        # Display results
        with config.table_container:
            ui.label('Search Results').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}]')
            search_results_text = f'Search results for "{protein_name}"'
            if taxonomy_name:
                search_results_text += f' in taxonomy "{taxonomy_name}"'
            ui.markdown(search_results_text)
            ui.markdown(
                f'Found **{len(config.uniprot_proteins)}** UniProtKB entries '
                f'in **{uniprot_species_count}** species and '
                f'**{len(config.ncbi_proteins)}** NCBI entries '
                f'in **{ncbi_species_count}** species '
                f'(Total: **{len(config.all_proteins)}** '
                f'in **{total_species}** unique species)'
            )

        # Finish search successfully
        finish_search(success=True)
        
        return {
            'success': True,
            'protein_name': protein_name,
            'taxonomy_name': taxonomy_name,
            'uniprot_proteins': uniprot_proteins_correct_rank,
            'ncbi_proteins': ncbi_proteins_correct_rank,
            'uniprot_species_count': uniprot_species_count,
            'ncbi_species_count': ncbi_species_count,
            'total_species': total_species
        }
    
    except asyncio.CancelledError:
        # Search was cancelled, reset state
        reset_search_state()
        print("Protein search was cancelled")
        return {'success': False, 'error': 'Search was cancelled'}
                    
    except Exception as e:
        # Print full traceback to console for debugging
        print("Full traceback:")
        print(traceback.format_exc())
        
        # Display error in UI
        config.table_container.clear()
        error_message = f"**Error:** {str(e)}\n\n**Traceback:**\n```\n{traceback.format_exc()}\n```"
        with config.table_container:
            ui.markdown(error_message)
            
        # Finish search with error
        finish_search(success=True)  # Show table with error message
        
        return {'success': False, 'error': str(e)}
        
