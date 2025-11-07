import requests
import xml.etree.ElementTree as ET
import time
import httpx
import re
from datetime import datetime

def ncbi_esearch(query, database, start=0, max_results=500):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        'db': database,
        'term': query,
        'retstart': start,
        'retmax': max_results,
        'retmode': 'xml',
        'email': 'your.email@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error in ESearch {database}: {e}")
        return None

def ncbi_esearch_count(query, database):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        'db': database,
        'term': query,
        'rettype': 'count',
        'retmode': 'xml',
        'email': 'your.email@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error getting {database} count: {e}")
        return None
    
def ncbi_efetch_mrna_genbank(mrna_ids):
    """
    Retrieve mRNA details in GenBank format from Nucleotide database
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'nucleotide',
        'id': ','.join(mrna_ids),
        'rettype': 'gb',
        'retmode': 'xml',
        'tool': 'evotree',
        'email': 'your.email@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error in EFetch mRNA GenBank: {e}")
        return None

def ncbi_efetch_proteins_genbank(protein_ids):
    """
    Retrieve protein details in GenBank format
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'protein',
        'id': ','.join(protein_ids),
        'rettype': 'gb',
        'retmode': 'xml',
        'tool': 'evotree',
        'email': 'your.email@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error in EFetch proteins: {e}")
        return None

def ncbi_efetch_proteins_fasta(protein_ids):
    """
    Retrieve protein details in FASTA format
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        'db': 'protein',
        'id': ','.join(protein_ids),
        'rettype': 'fasta',
        'retmode': 'xml',
        'tool': 'evotree',
        'email': 'your.email@example.com'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=60)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error in EFetch FASTA: {e}")
        return None

# =============================================================================
# XML PARSING FUNCTIONS
# =============================================================================

def parse_esearch_ids(xml_content):
    """
    Extract IDs from an ESearch result
    """
    if not xml_content:
        return []
    
    try:
        root = ET.fromstring(xml_content)
        ids = [id_elem.text for id_elem in root.findall('.//Id')]
        return ids
    except Exception as e:
        print(f"Error parsing ESearch IDs: {e}")
        return []

def parse_esearch_count(xml_content):
    """
    Extract result count from ESearch
    """
    if not xml_content:
        return 0
    
    try:
        root = ET.fromstring(xml_content)
        count = int(root.findtext('.//Count', '0'))
        return count
    except Exception as e:
        print(f"Error parsing count: {e}")
        return 0

def parse_genbank_proteins(xml_content):
    """
    Parse proteins from GenBank XML
    """
    if not xml_content:
        return []
    
    proteins = []
    try:
        root = ET.fromstring(xml_content)
        seq_elements = root.findall('.//GBSeq')
        
        for seq_elem in seq_elements:
            protein = extract_genbank_protein_info(seq_elem)
            if protein:
                proteins.append(protein)
                
    except Exception as e:
        print(f"Error parsing GenBank proteins: {e}")
    
    return proteins

def parse_fasta_proteins(xml_content):
    """
    Parse proteins from FASTA XML
    """
    if not xml_content:
        return []
    
    proteins = []
    try:
        root = ET.fromstring(xml_content)
        seq_elements = root.findall('.//TSeq')
        
        for seq_elem in seq_elements:
            protein = extract_fasta_protein_info(seq_elem)
            if protein:
                proteins.append(protein)
                
    except Exception as e:
        print(f"Error parsing FASTA proteins: {e}")
    
    return proteins

def parse_genbank_mrna(xml_content):
    """
    Parse mRNA sequences from GenBank XML (Nucleotide database)
    Filters to keep only mRNA sequences
    """
    if not xml_content:
        return []
    
    mrna_sequences = []
    try:
        root = ET.fromstring(xml_content)
        seq_elements = root.findall('.//GBSeq')
        
        for seq_elem in seq_elements:
            mrna = extract_genbank_mrna_info(seq_elem)
            if mrna:
                mrna_sequences.append(mrna)
                
    except Exception as e:
        print(f"Error parsing GenBank mRNA: {e}")
    
    return mrna_sequences

# =============================================================================
# DATA EXTRACTION FUNCTIONS
# =============================================================================

def extract_genbank_protein_info(seq_elem):
    """
    Extract protein information from GenBank XML element
    """
    try:
        accession = seq_elem.findtext('GBSeq_accession-version', 'Unknown')
        sequence_length = int(seq_elem.findtext('GBSeq_length', '0'))
        scientific_name = seq_elem.findtext('GBSeq_organism', None)
        definition = seq_elem.findtext('GBSeq_definition', '')
        sequence = seq_elem.findtext('GBSeq_sequence', '').upper()
        
        if '[' in definition:
            protein_name = definition.split('[')[0].strip()
        else:
            protein_name = definition.strip()

        taxid = extract_genbank_taxid(seq_elem)
        mrna_id = extract_genbank_mrna(seq_elem)
        
        return {
            'accession': accession,
            'protein_name': protein_name,
            'sequence': sequence,
            'scientific_name': scientific_name,
            'taxid': taxid,
            'sequence_length': sequence_length,
            'mRNA': mrna_id,
            'database': 'NCBI'
        }
        
    except Exception as e:
        print(f"Error extracting GenBank protein: {e}")
        return None

def extract_fasta_protein_info(seq_elem):
    """
    Extract protein information from FASTA XML element
    """
    try:
        accession = seq_elem.findtext('TSeq_accver', 'Unknown')
        sequence_length = int(seq_elem.findtext('TSeq_length', '0'))
        taxid = seq_elem.findtext('TSeq_taxid', None)
        scientific_name = seq_elem.findtext('TSeq_orgname', None)
        title = seq_elem.findtext('TSeq_defline', '')
        
        protein_name = parse_protein_title(title)
        
        return {
            'accession': accession,
            'protein_name': protein_name,
            'scientific_name': scientific_name,
            'taxid': int(taxid) if taxid and taxid.isdigit() else 'N/A',
            'sequence_length': sequence_length,
            'database': 'NCBI'
        }
        
    except Exception as e:
        print(f"Error extracting FASTA protein: {e}")
        return None

def extract_genbank_mrna_info(seq_elem):
    """
    Extract mRNA information from GenBank XML element (Nucleotide database)
    """
    try:
        accession = seq_elem.findtext('GBSeq_accession-version', 'Unknown')
        sequence_length = int(seq_elem.findtext('GBSeq_length', '0'))
        scientific_name = seq_elem.findtext('GBSeq_organism', None)
        definition = seq_elem.findtext('GBSeq_definition', '')
        sequence = seq_elem.findtext('GBSeq_sequence', '').upper()
        taxid = extract_genbank_taxid(seq_elem)
        if definition.endswith(', mRNA'):
            gene_name = definition[:-6].strip()
        else:
            gene_name = definition.strip()

        return {
            'accession': accession,
            'gene_name': gene_name,
            'sequence': sequence,
            'scientific_name': scientific_name,
            'taxid': taxid,
            'sequence_length': sequence_length,
            'database': 'NCBI'
        }
        
    except Exception as e:
        print(f"Error extracting GenBank mRNA: {e}")
        return None

def extract_gene_name_from_definition(definition):
    """
    Extract gene name from sequence definition
    """
    try:
        # Common patterns for gene names in definitions
        patterns = [
            r'(\w+)\s+(?:gene|mRNA)',
            r'(\w+)\s+transcript',
            r'(\w+)\s+protein',
            r'^(\w+)\s',  # First word
        ]
        
        for pattern in patterns:
            match = re.search(pattern, definition, re.IGNORECASE)
            if match:
                gene_name = match.group(1)
                # Filter out common non-gene words
                if gene_name.lower() not in ['complete', 'partial', 'predicted', 'hypothetical', 'unknown']:
                    return gene_name
        
        return None
        
    except Exception as e:
        print(f"Error extracting gene name from definition: {e}")
        return None

def extract_gene_name_from_features(seq_elem):
    """
    Extract gene name from GenBank features
    """
    try:
        features = seq_elem.findall('.//GBFeature')
        
        for feature in features:
            if feature.findtext('GBFeature_key', '') == 'gene':
                qualifiers = feature.findall('.//GBQualifier')
                
                for qualifier in qualifiers:
                    qual_name = qualifier.findtext('GBQualifier_name', '')
                    qual_value = qualifier.findtext('GBQualifier_value', '')
                    
                    if qual_name == 'gene':
                        return qual_value
        
        return None
        
    except Exception as e:
        print(f"Error extracting gene name from features: {e}")
        return None

def extract_genbank_taxid(seq_elem):
    """
    Extract taxid from GenBank features
    """
    try:
        features = seq_elem.findall('.//GBFeature')
        for feature in features:
            if feature.findtext('GBFeature_key', '') == 'source':
                qualifiers = feature.findall('.//GBQualifier')
                
                for qualifier in qualifiers:
                    qual_name = qualifier.findtext('GBQualifier_name', '')
                    qual_value = qualifier.findtext('GBQualifier_value', '')
                    
                    if qual_name == 'db_xref' and 'taxon:' in qual_value:
                        taxid_str = qual_value.replace('taxon:', '')
                        if taxid_str.isdigit():
                            return int(taxid_str)
    except Exception as e:
        print(f"Error extracting taxid: {e}")
    
    return 'N/A'

def extract_genbank_mrna(seq_elem):
    """
    Extract mRNA ID from GenBank features
    """
    try:
        features = seq_elem.findall('.//GBFeature')
        
        for feature in features:
            if feature.findtext('GBFeature_key', '') == 'CDS':
                qualifiers = feature.findall('.//GBQualifier')
                
                for qualifier in qualifiers:
                    qual_name = qualifier.findtext('GBQualifier_name', '')
                    qual_value = qualifier.findtext('GBQualifier_value', '')
                    
                    if qual_name in ['transcript_id', 'coded_by']:
                        mrna_id = extract_mrna_id_from_text(qual_value)
                        if mrna_id:
                            return mrna_id
                    
                    elif qual_name == 'db_xref' and 'RefSeq:' in qual_value:
                        refseq_id = qual_value.replace('RefSeq:', '')
                        if refseq_id.startswith(('NM_', 'XM_')):
                            refseq_id = refseq_id.split('.')[0]
                            return refseq_id
    except Exception as e:
        print(f"Error extracting mRNA from features: {e}")
    
    return None

def extract_mrna_id_from_text(text):
    """
    Extract mRNA ID from text using regex
    """
    pattern = r'([NX]M_\d+\.\d+)'
    match = re.search(pattern, text)
    return match.group(1) if match else None


# =============================================================================
# QUERY BUILDING FUNCTIONS
# =============================================================================

def build_protein_query(protein_name, taxid=None):
    query = [f'(*{protein_name.replace(" ", "*")}*)[Protein Name]']
    if taxid:
        query.append(f"txid{taxid}[porgn]")
    return " AND ".join(query)

def build_mrna_query(gene_name, taxid=None):
    query = [f'(*{gene_name.replace(" ", "*")}*) AND biomol_mrna[PROP]']
    if taxid:
        query.append(f"txid{taxid}[porgn]")
    return " AND ".join(query)

# =============================================================================
# HIGH-LEVEL ORCHESTRATION FUNCTIONS
# =============================================================================

def search_proteins_by_name(protein_name, taxid=None, max_results=None):
    query = build_protein_query(protein_name, taxid)
    # Count first
    count_xml = ncbi_esearch_count(query, database='protein')
    total_count = parse_esearch_count(count_xml)
    if total_count == 0:
        return []
    
    # Use all results if max_results is None, otherwise limit
    actual_max = total_count if max_results is None else min(total_count, max_results)
    print(f"Found {total_count} proteins, retrieving {actual_max}...")
    
    # Retrieve IDs in batches
    all_proteins = []
    search_batch_size = 500  # For ESearch
    efetch_batch_size = 50   # Smaller batches for EFetch to avoid URI too long error
    
    for start in range(0, actual_max, search_batch_size):
        current_batch = min(search_batch_size, actual_max - start)
        
        # Search for IDs
        search_xml = ncbi_esearch(query, 'protein', start, current_batch)
        protein_ids = parse_esearch_ids(search_xml)
        
        if protein_ids:
            # Process IDs in smaller chunks for EFetch
            for i in range(0, len(protein_ids), efetch_batch_size):
                chunk_ids = protein_ids[i:i + efetch_batch_size]
                
                # Retrieve details for this chunk
                details_xml = ncbi_efetch_proteins_genbank(chunk_ids)
                proteins = parse_genbank_proteins(details_xml)
                all_proteins.extend(proteins)
                
                time.sleep(0.3)  # Rate limiting between EFetch calls
        
        time.sleep(0.5)  # Rate limiting between ESearch calls
    
    return all_proteins

def search_genes_by_name(gene_name, taxid=None, max_results=None):
    query = build_mrna_query(gene_name, taxid)
    # Count first
    count_xml = ncbi_esearch_count(query, database='nucleotide')
    total_count = parse_esearch_count(count_xml)
    
    if total_count == 0:
        return []
    
    # Use all results if max_results is None, otherwise limit
    actual_max = total_count if max_results is None else min(total_count, max_results)
    
    # Retrieve IDs in batches
    all_mrna = []
    search_batch_size = 500  # For ESearch
    efetch_batch_size = 50   # Smaller batches for EFetch to avoid URI too long error
    print(f"Found {total_count} mRNA sequences, retrieving up to {actual_max}...")
    for start in range(0, actual_max, search_batch_size):
        current_batch = min(search_batch_size, actual_max - start)
        
        # Search for mRNA IDs in Nucleotide database
        search_xml = ncbi_esearch(query, 'nucleotide', start, current_batch)
        mrna_ids = parse_esearch_ids(search_xml)
        
        if mrna_ids:
            # Process IDs in smaller chunks for EFetch
            for i in range(0, len(mrna_ids), efetch_batch_size):
                chunk_ids = mrna_ids[i:i + efetch_batch_size]
                
                # Retrieve GenBank details for this chunk
                details_xml = ncbi_efetch_mrna_genbank(chunk_ids)
                mrna_sequences = parse_genbank_mrna(details_xml)
                all_mrna.extend(mrna_sequences)
                
                time.sleep(0.3)  # Rate limiting between EFetch calls
        
        time.sleep(0.5)  # Rate limiting between ESearch calls
    
    return all_mrna

# =============================================================================
# MAIN API FUNCTION
# =============================================================================

def fetch_ncbi_proteins(protein_name, taxid=None, max_results=None):
    """
    Fetch proteins by name from NCBI Protein database
    If max_results is None, retrieves ALL available results
    """
    proteins = search_proteins_by_name(protein_name, taxid, max_results)
    return proteins

def fetch_ncbi_genes(gene_name, taxid=None, max_results=None):
    """
    Fetch mRNA sequences by gene name from NCBI Nucleotide database
    If max_results is None, retrieves ALL available results
    """
    mrna_sequences = search_genes_by_name(gene_name, taxid, max_results)
    return mrna_sequences

# =============================================================================
# FASTA CREATION (for compatibility)
# =============================================================================

async def create_ncbi_fasta(selected_data, loading_spinner):
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    fasta_file = f"{identifier}_NCBI.fasta"
    loading_spinner.set_visibility(True)
    
    try:
        async with httpx.AsyncClient(timeout=360000) as client:
            response = await client.post(
                "http://134.158.151.55/create_ncbi_fasta", 
                json={"selected_data": selected_data, "fasta_file": fasta_file}
            )
            if response.status_code == 200:
                data = response.json()
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error creating FASTA: {e}")
        return 'Failed'
    finally:
        loading_spinner.set_visibility(False)

# =============================================================================
# mRNA EXTRACTION FUNCTIONS
# =============================================================================

def mrna_from_mrna_accession(mrna_accessions):
    if not mrna_accessions:
        return []
    
    unique_accessions = list(dict.fromkeys(mrna_accessions))
    print(f"{len(unique_accessions)} unique mRNA accessions to process")
    
    all_mrna = []
    found_accessions = set()
    search_batch_size = 50
    efetch_batch_size = 50
    
    for i in range(0, len(unique_accessions), efetch_batch_size):
        batch_accessions = unique_accessions[i:i + efetch_batch_size]
        try:
            accession_query = ' OR '.join([f'{acc}[ACCN]' for acc in batch_accessions])
            search_xml = ncbi_esearch(accession_query, 'nucleotide', 0, search_batch_size)
            mrna_ids = parse_esearch_ids(search_xml)
            if mrna_ids:               
                for j in range(0, len(mrna_ids), efetch_batch_size):
                    chunk_ids = mrna_ids[j:j + efetch_batch_size]
                    
                    details_xml = ncbi_efetch_mrna_genbank(chunk_ids)
                    mrna_sequences = parse_genbank_mrna(details_xml)
                    
                    for mrna in mrna_sequences:
                        found_accessions.add(mrna.get('accession', ''))
                    all_mrna.extend(mrna_sequences)
                    time.sleep(0.3)
            else:
                print(f"No IDs found for batch {i//efetch_batch_size + 1}")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error processing accession batch {i//efetch_batch_size + 1}: {e}")
            continue
    
    requested_accessions = set(unique_accessions)
    parsed_found_accessions = set(acc.split('.')[0] for acc in found_accessions if acc)
    missing_accessions = requested_accessions - parsed_found_accessions
    
    print(f"Successfully retrieved {len(all_mrna)} mRNA sequences from {len(unique_accessions)} accessions")
    
    if missing_accessions:
        print(f"\n❌ {len(missing_accessions)} accessions NOT found:")
        for acc in sorted(missing_accessions):
            print(f"  - {acc}")
    else:
        print("✅ All accessions were successfully retrieved!")
    
    return all_mrna
