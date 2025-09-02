from nicegui import ui
from uniprot import fetch_taxonomy_id, fetch_uniprot_data
from protein_table import create_protein_table
from length_distribution import create_length_distribution_chart
import asyncio

ui.label('Welcome to EvoTree!').style('color: #654DF0; font-size: 2rem; font-weight: bold; margin-bottom: 1rem;')

with ui.row().classes('w-[90%] gap-4 mx-auto border-2 border-[#654DF0] rounded-xl shadow-md p-4'):

    with ui.row().classes('w-full gap-4 mx-auto'):
        protein_input = ui.input('Protein name or ID *').classes('flex-grow')
        taxonomy_input = ui.input('Taxonomy name or ID').classes('flex-grow')

    with ui.expansion('Length filters (optional)', icon='tune', value=False).classes('w-full mx-auto'):
        with ui.row().classes('w-full gap-4 mx-auto'):    
            min_length_input = ui.input('Minimal sequence length (# residues)').classes('flex-grow')
            max_length_input = ui.input('Maximal sequence length (# residues)').classes('flex-grow')

    ui.button(  
        'Search',
        color="#654DF0",
        on_click=lambda: search_protein(
            protein_input.value,
            taxonomy_input.value,
            min_length_input.value,
            max_length_input.value
        )
    ).classes('px-6 text-white self-end')

uniprot_table_container = ui.column().classes('w-full mt-4')
length_distribution_container = ui.column().classes('w-full mt-4')
loading_spinner = ui.spinner(size='lg', color='#654DF0').classes('mx-auto my-8')
loading_spinner.set_visibility(False)


async def search_protein(protein_name, taxonomy_name, min_length, max_length):
    if protein_name:
        loading_spinner.set_visibility(True)
        uniprot_table_container.clear()
        try:
            loop = asyncio.get_event_loop()
            min_length = int(min_length) if min_length else None
            max_length = int(max_length) if max_length else None
            taxid = await loop.run_in_executor(None, fetch_taxonomy_id, taxonomy_name) if taxonomy_name else None
            proteins = await loop.run_in_executor(None, fetch_uniprot_data, protein_name, taxid, min_length, max_length)
            species_count = len(set(protein['organism']['scientificName'] for protein in proteins))
            with uniprot_table_container:
                ui.markdown(f'**"{protein_name}" found {len(proteins)} times in {species_count} different species in UniprotKB**')
                if proteins:
                    create_protein_table(proteins)
                    create_length_distribution_chart(proteins)
        except Exception as e:
            with uniprot_table_container:
                ui.markdown(f'**Error:** {str(e)}')
        loading_spinner.set_visibility(False)
    else:
        ui.notify('Please enter a protein name.')

ui.run()