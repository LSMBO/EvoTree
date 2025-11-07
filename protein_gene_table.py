from nicegui import ui
import config

def create_gene_table(ncbi_data):
    with config.table_container:
        if ncbi_data:
            create_ncbi_table(ncbi_data, mode='gene')
        else:
            ui.markdown('**No NCBI Gene results found**')

def create_protein_table(uniprot_data, ncbi_data):
    with config.table_container:
        with ui.tabs() as tabs:
            uniprot_tab = ui.tab(f'UniProtKB ({len(uniprot_data)})')
            ncbi_tab = ui.tab(f'NCBI ({len(ncbi_data)})')
        
        with ui.tab_panels(tabs, value=uniprot_tab).classes('w-full'):
            with ui.tab_panel(uniprot_tab):
                if uniprot_data:
                    create_uniprot_table(uniprot_data)
                else:
                    ui.markdown('**No UniProtKB results found**')
            
            with ui.tab_panel(ncbi_tab):
                if ncbi_data:
                    create_ncbi_table(ncbi_data, mode="protein")
                else:
                    ui.markdown('**No NCBI results found**')

def create_uniprot_table(data):
    columns = [
        {'name': 'entry_type', 'label': 'Entry Type', 'field': 'entry_type', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'accession', 'label': 'Accession', 'field': 'accession', 'sortable': True, 'align': 'left', 'style': 'width: 15%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'taxid', 'label': 'Tax ID', 'field': 'taxid', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'scientific_name', 'label': 'Scientific Name', 'field': 'scientific_name', 'sortable': True, 'align': 'left', 'style': 'width: 20%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'gene_name', 'label': 'Gene Name', 'field': 'gene_name', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'sequence_length', 'label': 'Sequence Length', 'field': 'sequence_length', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'mRNA', 'label': 'mRNA', 'field': 'mRNA', 'sortable': True, 'align': 'left', 'style': 'width: 10%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'protein_name', 'label': 'Protein Name', 'field': 'protein_name', 'sortable': True, 'align': 'left', 'style': 'width: 35%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
    
    ]
    
    rows = []
    for item in data:
        row = {}

        entry_type = item.get('entryType', '')
        if 'unreviewed' in entry_type.lower():
            row['entry_type'] = 'TrEMBL'
        elif 'reviewed' in entry_type.lower():
            row['entry_type'] = 'SwissProt'
        else:
            row['entry_type'] = entry_type or 'N/A'

        accession = item.get('primaryAccession', 'N/A')
        id = item.get('uniProtkbId', 'N/A')
        if row['entry_type'] == 'SwissProt':
            row['accession'] = f"sp|{accession}|{id}"
        else:
            row['accession'] = f"tr|{accession}|{id}"

        try:
            row['taxid'] = item['organism']['taxonId']
        except (KeyError, TypeError):
            row['taxid'] = 'N/A'
        
        try:
            row['scientific_name'] = item['organism']['scientificName']
        except (KeyError, TypeError, IndexError):
            row['scientific_name'] = 'N/A'
        
        try:
            if 'recommendedName' in item['proteinDescription']:
                row['protein_name'] = item['proteinDescription']['recommendedName']['fullName']['value']
            elif 'submissionNames' in item['proteinDescription']:
                row['protein_name'] = item['proteinDescription']['submissionNames'][0]['fullName']['value']
            else:
                row['protein_name'] = 'N/A'
        except (KeyError, TypeError, IndexError):
            print(item)
            row['protein_name'] = 'N/A'
        try:
            row['gene_name'] = item['genes'][0]['geneName']['value']
        except (KeyError, TypeError, IndexError): 
            row['gene_name'] = 'N/A'

        try:
            row['sequence_length'] = item.get('sequence_length', item.get('sequence', {}).get('length', 'N/A'))
        except (KeyError, TypeError):
            row['sequence_length'] = 'N/A'

        try:
            if item['mRNA']:
                row['mRNA'] = item['mRNA']
            else:
                row['mRNA'] = ''
        except (KeyError, TypeError):
            row['mRNA'] = ''


        rows.append(row)

    with ui.element('div').style('overflow-y: auto; max-height: 40vh; width: 100%;'):
        ui.table(
            columns=columns,
            rows=rows,
            row_key='accession',
        ).classes('w-full')

def create_ncbi_table(data, mode):
    columns = [
        {'name': 'database', 'label': 'Database', 'field': 'database', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'accession', 'label': 'Accession', 'field': 'accession', 'sortable': True, 'align': 'left', 'style': 'width: 10%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'taxid', 'label': 'Tax ID', 'field': 'taxid', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
        {'name': 'scientific_name', 'label': 'Scientific Name', 'field': 'scientific_name', 'sortable': True, 'align': 'left', 'style': 'width: 25%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
    ]    
    if mode == 'protein':
        columns.extend([
            {'name': 'sequence_length', 'label': 'Sequence Length', 'field': 'sequence_length', 'sortable': True, 'align': 'left', 'style': 'width: 5%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
            {'name': 'mRNA', 'label': 'mRNA', 'field': 'mRNA', 'sortable': True, 'align': 'left', 'style': 'width: 10%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
            {'name': 'protein_name', 'label': 'Protein Name', 'field': 'protein_name', 'sortable': True, 'align': 'left', 'style': 'width: 40%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'}
        ])
    else:
        columns.extend([
            {'name': 'sequence_length', 'label': 'Sequence Length', 'field': 'sequence_length', 'sortable': True, 'align': 'left', 'style': 'width: 10%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'},
            {'name': 'gene_name', 'label': 'Gene Name', 'field': 'gene_name', 'sortable': True, 'align': 'left', 'style': 'width: 45%; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'}

        ])
        
    rows = []
    for item in data:
        row = {
            'database': item.get('database', 'NCBI'),
            'accession': item.get('accession', 'N/A'),
            'taxid': item.get('taxid', 'N/A'),
            'scientific_name': item.get('scientific_name', 'N/A'),
        }
        
        if mode == 'protein':
            row.update({
                'protein_name': item.get('protein_name', 'N/A'),
                'sequence_length': item.get('sequence_length', 'N/A'),
                'mRNA': item.get('mRNA', ''),
            })
        else:
            row.update({
                'gene_name': item.get('gene_name', 'N/A'),
                'sequence_length': item.get('sequence_length', 'N/A'),
            })
        
        rows.append(row)

    with ui.element('div').style('overflow-y: auto; max-height: 40vh; width: 100%;'):
        ui.table(
            columns=columns,
            rows=rows,
            row_key='accession',
        ).classes('w-full')
