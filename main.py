from nicegui import ui
import requests

ui.markdown('### Welcome to EvoTree!')

ui.link('Go to UniprotKB', 'https://www.uniprot.org/uniprotkb')
ui.link('Go to NCBI', 'https://www.ncbi.nlm.nih.gov/')

def fetch_uniprot_data(protein_query):
    url = f"https://www.ebi.ac.uk/proteins/api/proteins?offset=0&size=500&protein={protein_query}"
    response = requests.get(url, headers={"Accept": "application/json"})
    if not response.ok:
        response.raise_for_status()
    return response.json()

def create_protein_table(data):
    columns = [
        {'name': 'accession', 'label': 'Accession', 'field': 'accession', 'sortable': True},
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'taxid', 'label': 'Tax ID', 'field': 'taxid', 'sortable': True},
        {'name': 'scientific_name', 'label': 'Scientific Name', 'field': 'scientific_name', 'sortable': True},
        {'name': 'protein_name', 'label': 'Protein Name', 'field': 'protein_name', 'sortable': True},
    ]
    
    rows = []
    for item in data:
        row = {}
        row['accession'] = item.get('accession', 'N/A')
        row['id'] = item.get('id', 'N/A')

        try:
            row['taxid'] = item['organism']['taxonomy']
        except (KeyError, TypeError):
            row['taxid'] = 'N/A'
        
        try:
            row['scientific_name'] = item['organism']['names'][0]['value']
        except (KeyError, TypeError, IndexError):
            row['scientific_name'] = 'N/A'
        
        try:
            row['protein_name'] = item['protein']['recommendedName']['fullName']['value']
        except (KeyError, TypeError):
            row['protein_name'] = 'N/A'
        
        rows.append(row)
    print(data[0]['gene'])
    
    return ui.table(
        columns=columns,
        rows=rows,
        row_key='accession'
    ).classes('w-full h-96')

def search_protein(value):
    if value:        
        results_container.clear()
        try:
            response_body = fetch_uniprot_data(value)
            with results_container:
                ui.markdown(f'**{len(response_body)} results found**')
                if response_body:
                    create_protein_table(response_body)
                    
        except Exception as e:
            with results_container:
                ui.markdown(f'**Error:** {str(e)}')
    else:
        ui.notify('Please enter a protein name or ID.')

with ui.row().classes('w-[90%] gap-4 mx-auto'):
    protein_input = ui.input('Enter a protein name or ID:').classes('flex-grow')
    ui.button('Search', color="#654DF0", on_click=lambda: search_protein(protein_input.value)).classes('px-6 text-white')

results_container = ui.column().classes('w-full mt-4')

ui.run()