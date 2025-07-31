from nicegui import ui

def create_protein_table(data):
    columns = [
        {'name': 'entry_type', 'label': 'Entry Type', 'field': 'entry_type', 'sortable': True},
        {'name': 'accession', 'label': 'Accession', 'field': 'accession', 'sortable': True},
        {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True},
        {'name': 'taxid', 'label': 'Tax ID', 'field': 'taxid', 'sortable': True},
        {'name': 'scientific_name', 'label': 'Scientific Name', 'field': 'scientific_name', 'sortable': True, 'style': 'max-width: 20vw; width: 20%; white-space: nowrap; overflow-x: auto;'},
        {'name': 'protein_name', 'label': 'Protein Name', 'field': 'protein_name', 'sortable': True},
        {'name': 'gene_name', 'label': 'Gene Name', 'field': 'gene_name', 'sortable': True},
        {'name': 'sequence_length', 'label': 'Sequence Length', 'field': 'sequence_length', 'sortable': True}
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

        row['accession'] = item.get('primaryAccession', 'N/A')
        row['id'] = item.get('uniProtkbId', 'N/A')

        try:
            row['taxid'] = item['organism']['taxonId']
        except (KeyError, TypeError):
            row['taxid'] = 'N/A'
        
        try:
            row['scientific_name'] = item['organism']['scientificName']
        except (KeyError, TypeError, IndexError):
            row['scientific_name'] = 'N/A'
        
        try:
            row['protein_name'] = item['proteinDescription']['recommendedName']['fullName']['value']
        except (KeyError, TypeError):
            row['protein_name'] = 'N/A'
        
        try:
            row['gene_name'] = item['genes'][0]['geneName']['value']
        except (KeyError, TypeError, IndexError): 
            row['gene_name'] = 'N/A'

        try:
            row['sequence_length'] = item['sequence']['length']
        except (KeyError, TypeError):
            row['sequence_length'] = 'N/A'

        except Exception:
            row['entry_type'] = 'N/A'
        
        rows.append(row)

    with ui.element('div').style('overflow-y:auto; max-height:40vh; width:100%;'):
        ui.table(
            columns=columns,
            rows=rows,
            row_key='accession',
        )
