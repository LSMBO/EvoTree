# Global configuration

# Interface colors
VIOLET_COLOR = "#654DF0"
VIOLET_HOVER = "#5B45D9"

# API Configuration
API_BASE_URL = "http://134.158.151.55"


# Global variables shared between modules
current_url = None
current_fasta_file = None
current_mafft_file = None
current_bmge_file = None
current_iqtree_file = None
current_nw_distance_file = None

pipeline1_data = {
    'fasta_file': None,
    'mafft_file': None,
    'iqtree_file': None,
    'nw_distance_file': None
}

pipeline2_data = {
    'fasta_file': None,
    'mafft_file': None,
    'bmge_file': None,
    'iqtree_file': None,
    'nw_distance_file': None
}

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
uniprot_table_container = None
sequence_selection_container = None
length_distribution_container = None
pipeline1_container = None
pipeline2_launcher_container = None
pipeline2_container = None
pipeline2_results = None
loading_spinner = None