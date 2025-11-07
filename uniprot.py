import requests
import httpx
from datetime import datetime

def fetch_taxonomy(taxonomy_name):
    base_url = "https://rest.uniprot.org/taxonomy/search"
    params = {
        "query": taxonomy_name,
        "format": "json",
        "size": 500
    }
    data = requests_get(base_url, params)
    if data:
        for taxo in data:
            if taxonomy_name.isdigit():
                if taxo['taxonId'] == int(taxonomy_name):
                    return {
                        "scientific_name": taxo.get('scientificName'),
                        "taxid": taxo.get('taxonId'),
                        "rank": taxo.get('rank')
                    }
            if taxo['scientificName'].lower() == taxonomy_name.lower():
                return {
                    "scientific_name": taxo.get('scientificName'),
                    "taxid": taxo.get('taxonId'),
                    "rank": taxo.get('rank')
                }
    
    raise ValueError(f"Taxonomy name '{taxonomy_name}' not found.")

def fetch_uniprot_data(protein_name, taxid=None, min_length=None, max_length=None):
    protein_name = protein_name.replace(" ", "+")
    base_url = "https://rest.uniprot.org/uniprotkb/stream"
    query_parts = [f"protein_name:{protein_name}"]
    
    if taxid is not None:
        query_parts.append(f"taxonomy_id:{taxid}")
    if min_length is not None and max_length is not None:
        query_parts.append(f"length:[{min_length} TO {max_length}]")
    elif min_length is not None:
        query_parts.append(f"length:[{min_length} TO *]")
    elif max_length is not None:
        query_parts.append(f"length:[* TO {max_length}]")
    
    query = " AND ".join(query_parts)
    params = {
        "query": query,
        "format": "json",
        "fields": "accession,id,protein_name,organism_name,organism_id,gene_names,length,xref_embl,xref_refseq",
    }
    
    results = requests_get(base_url, params)
    if results:
        # Restructure data to use sequence_length like NCBI
        for protein in results:
            # Add sequence_length field from the existing sequence structure
            if 'sequence' in protein and 'length' in protein['sequence']:
                protein['sequence_length'] = protein['sequence']['length']
            elif 'length' in protein:
                # If length is directly in protein (from API fields)
                protein['sequence_length'] = protein['length']
            else:
                protein['sequence_length'] = 0
        return results
    return []

def fetch_rank(taxid, selected_rank):
    url = f"https://rest.uniprot.org/taxonomy/search?query=(tax_id:{taxid})&format=json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()['results'][0]
            lineage = data.get('lineage', [])
            if data.get('rank') == selected_rank:
                return (data['taxonId'], data['scientificName'])
            for i in range(len(lineage)-1, -1, -1):
                if lineage[i]['rank'] == selected_rank:
                    return (lineage[i]['taxonId'], lineage[i]['scientificName'])
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    return None, None


def requests_get(url, params):
    results = []
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results.extend(response.json().get("results", []))
            while response.links.get("next", {}).get("url"):
                next_url = response.links["next"]["url"]
                response = requests.get(next_url, params=None)
                results.extend(response.json().get("results", []))
            return results
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")


async def create_uniprot_fasta(base_url, params, loading_spinner):
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    fasta_file = f"{identifier}_Uniprot.fasta"
    loading_spinner.set_visibility(True)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://134.158.151.55/create_uniprot_fasta", json={"base_url": base_url, "params": params, "fasta_file": fasta_file})
            if response.status_code == 200:
                data = response.json()
                print(f"Response from Flask (create_uniprot_fasta): {data}")
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error occurred (create_uniprot_fasta): {e}")
        return 'Failed'
    finally:
        loading_spinner.set_visibility(False)
        