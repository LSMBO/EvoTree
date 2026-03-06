# Global configuration

# Interface colors
VIOLET_COLOR = "#654DF0"
VIOLET_HOVER = "#5B45D9"

# API Configuration
API_BASE_URL = "http://134.158.151.55"


# Global variables shared between modules
search_params = {
    'term': None,
    'taxid': None,
    'uniprot': True,
    'ncbi': True
}

selection_params = {
    'min_length': '*',
    'max_length': '*',
    'uniprot': True,
    'ncbi': True
}

current_search_type = None  # 'protein' or 'gene'
all_proteins = []
uniprot_proteins = []
ncbi_proteins = []
ncbi_genes = []
selected_data = []

# Custom FASTA upload variables
select_sequence_active_tab = 'sequences_from_search'  # 'sequences_from_search' or 'custom_fasta'
custom_fasta_content = None  # Content of uploaded custom FASTA file
custom_fasta_filename = None  # Filename of uploaded custom FASTA file

use_mrna_from_proteins_button = None

# UI containers (initialized in main.py)
table_container = None
sequence_selection_container = None
length_distribution_container = None
pipeline_container = None
run_history_container = None
loading_spinner = None

# Current run tracking
current_run_id = None