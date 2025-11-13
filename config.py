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

# Search and filter parameters for download
search_params = {
    'term': None,
    'taxid': None,
    'min_length': '*',
    'max_length': '*',
    'uniprot': True,
    'ncbi': True
}

# Data for protein and gene searches
current_search_type = None  # 'protein' or 'gene'
all_proteins = []
selected_proteins = []
uniprot_proteins = []
ncbi_proteins = []

# Gene data
ncbi_genes = []
selected_genes = []

# Unified selection data (points to the currently selected data based on search type)
current_data = []  # Will point to selected_proteins or selected_genes
selected_data = []  # Alias for current_data for backward compatibility

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