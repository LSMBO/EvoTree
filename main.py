from nicegui import ui
import requests
from datetime import datetime
import config
import styles
from search import search_protein, search_genes
from protein_gene_table import create_protein_table, create_gene_table
from sequence_selection import show_sequence_selection_form

with ui.row().classes('w-full justify-center mb-4'):
    ui.label('EvoTree').style(f'color: {config.VIOLET_COLOR}; font-size: 2rem; font-weight: bold; text-align: center;')


async def handle_search_proteins(protein_name, taxonomy_name, selected_rank):
    if not protein_name.strip():
        ui.notify('Please enter a protein name.', color='warning')
        return
    
    result = await search_protein(protein_name, taxonomy_name, selected_rank)
    if result and result['success']:
        create_protein_table(result["uniprot_proteins"], result["ncbi_proteins"])
        show_sequence_selection_form()

async def handle_search_genes(gene_name, taxonomy_name, selected_rank):
    if not gene_name.strip():
        ui.notify('Please enter a gene name.', color='warning')
        return
    
    result = await search_genes(gene_name, taxonomy_name, selected_rank)
    if result and result['success']:
        create_gene_table(result["ncbi_genes"])
        show_sequence_selection_form()


with ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6'):
    with ui.row().classes('w-full gap-4 mx-auto'):
        input_name = ui.input('Protein or Gene name*').classes('flex-grow')
        taxonomy_input = ui.input('Taxonomy name or ID').classes('flex-grow')
        rank_select = ui.select(
            options=['species', 'subspecies', 'strain'],
            label='Rank',
            value='species'
        ).classes('flex-grow')
    
    with ui.row().classes('w-full gap-4'):
        search_proteins_button = ui.button(
            'Search Proteins',
            on_click=lambda: handle_search_proteins(
                input_name.value,
                taxonomy_input.value,
                rank_select.value
            )
        ).classes('flex-1')
        styles.apply_violet_color(search_proteins_button)
        
        search_genes_button = ui.button(
            'Search Genes (mRNA)',
            on_click=lambda: handle_search_genes(
                input_name.value,
                taxonomy_input.value,
                rank_select.value
            )
        ).classes('flex-1')
        styles.apply_violet_color(search_genes_button)

config.table_container = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.table_container.set_visibility(False)

config.sequence_selection_container = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.sequence_selection_container.set_visibility(False)

config.length_distribution_container = ui.column().classes('w-full mt-4') 
config.length_distribution_container.set_visibility(False)

config.pipeline1_container = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.pipeline1_container.set_visibility(False)

config.pipeline2_launcher_container = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.pipeline2_launcher_container.set_visibility(False)

config.pipeline2_container = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.pipeline2_container.set_visibility(False)

config.pipeline2_results = ui.card().classes(f'w-full border-2 border-[{config.VIOLET_COLOR}] rounded-xl shadow-lg p-6')
config.pipeline2_results.set_visibility(False)

config.loading_spinner = ui.spinner(size='lg', color=config.VIOLET_COLOR).classes('mx-auto my-8')
config.loading_spinner.set_visibility(False)



clear_flask = ui.button('Clear Flask TMP',
          on_click=lambda: requests.post(f"{config.API_BASE_URL}/clear", json={"date_limit": datetime.now().strftime("%d%m%Y%H%M%S")})).classes('mt-20')
styles.apply_default_color(clear_flask)
styles.apply_full_width(clear_flask)

ui.run(port=8080, show=True, reload=True)