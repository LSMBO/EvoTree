import requests
import time

def requests_get(url, params):
    attempt = 0
    while attempt < 3:
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response
            else:
                print(f"Error: Received status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        attempt += 1
        if attempt < 3:
            print(f"Retrying in 5 seconds...")
            time.sleep(5)
    raise Exception(f"Failed to fetch data from {url} after 3 attempts")

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
            if taxo['scientificName'].lower() == taxonomy_name.lower():
                return taxo['taxonId']
    raise ValueError(f"Taxonomy name '{taxonomy_name}' not found.")

def fetch_uniprot_data(protein_name, taxid):
    protein_name = protein_name.replace(" ", "+")
    base_url = "https://rest.uniprot.org/uniprotkb/search"
    if taxid is not None:
        query = f"protein_name:{protein_name} AND taxonomy_id:{taxid}"
    else:
        query = f"protein_name:{protein_name}"
    params = {
        "query": query,
        "format": "json",
        "fields": "accession,id,protein_name,organism_name,organism_id,gene_names,length",
        "size": 500
    }
    
    url = f"https://rest.uniprot.org/uniprotkb/search?query=(protein_name:{protein_name})%20AND%20(taxonomy_id:{taxid})&format=json"
    print(url)
    response = requests_get(base_url, params)
    if response and response.json()["results"]:
        return response.json()["results"]
    return {}

