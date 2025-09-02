import requests
import time


def fetch_taxonomy_id(taxonomy_name):
    base_url = "https://rest.uniprot.org/taxonomy/search"
    params = {
        "query": taxonomy_name,
        "format": "json",
        "size": 500
    }
    response = requests_get(base_url, params)
    if response and response.json()["results"]:
        data = response.json()['results']
        for taxo in data:
            if taxonomy_name.isdigit():
                if taxo['taxonId'] == int(taxonomy_name):
                    return taxo['taxonId']
            if taxo['scientificName'].lower() == taxonomy_name.lower():
                return taxo['taxonId']
            
    raise ValueError(f"Taxonomy name '{taxonomy_name}' not found.")

def fetch_uniprot_data(protein_name, taxid=None, min_length=None, max_length=None):
    protein_name = protein_name.replace(" ", "+")
    base_url = "https://rest.uniprot.org/uniprotkb/search"
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
        "fields": "accession,id,protein_name,organism_name,organism_id,gene_names,length",
        "size": 500
    }
    
    results = requests_get(base_url, params)
    if results:
        return results
    return []

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
