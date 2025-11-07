import asyncio
import httpx
from nicegui import ui
from datetime import datetime
import config
from uniprot import create_uniprot_fasta
from ncbi import create_ncbi_fasta
from utils import download_file_from_server
import styles

async def create_fasta(download):
    min_length = config.search_params['min_length']
    max_length = config.search_params['max_length']
    uniprot_file_path = None
    ncbi_file_path = None
    print("config search parameters:", config.search_params)
    print("Length of all_proteins:", len(config.all_proteins))
    print("Length of selected_proteins:", len(config.selected_proteins))
    print("Length of uniprot_proteins:", len(config.uniprot_proteins))
    print("Length of ncbi_proteins:", len(config.ncbi_proteins))
    print("Length of ncbi_genes:", len(config.ncbi_genes))
    print("Length of selected_genes:", len(config.selected_genes))
    print("Length of selected_data:", len(config.selected_data))
    print("Length of current_data:", len(config.current_data))
    if config.search_params['uniprot']:
        try:
            base_url = "https://rest.uniprot.org/uniprotkb/stream"
            params = {
                'query': f"taxonomy_id:{config.search_params['taxid']} AND protein_name:{config.search_params['term'].replace(' ', '+')} AND length:[{min_length} TO {max_length}]",
                'format': 'fasta'
            }
            uniprot_file_path = await create_uniprot_fasta(base_url, params, config.loading_spinner)
            if uniprot_file_path == "Failed":
                print(f"Failed to create UniProt FASTA file.")
                return
        except Exception as e:
            print(f"Error occurred (create_uniprot_fasta): {e}")
            ui.notify(f'Error: {str(e)}', color='red')            

    if config.search_params['ncbi']:
        try:
            ncbi_file_path = await create_ncbi_fasta(config.selected_data, config.loading_spinner)
            if ncbi_file_path == "Failed":
                print(f"Failed to create NCBI FASTA file.")
                return
        except Exception as e:
            print(f"Error occurred (create_ncbi_fasta p): {e}")
            ui.notify(f'Error: {str(e)}', color='red')

    if uniprot_file_path and ncbi_file_path:
        try:
            print(f"Merging UniProt file: {uniprot_file_path} and NCBI file: {ncbi_file_path}...")
            merged_fasta_path = await merge_uniprot_ncbi_fasta(uniprot_file_path, ncbi_file_path, config.loading_spinner)
            if merged_fasta_path == "Failed":
                print(f"Failed to merge UniProt and NCBI FASTA files.")
                return
            
            if download:
                download_file_from_server(merged_fasta_path)
            return merged_fasta_path
        except Exception as e:
            ui.notify(f'Error: {str(e)}', color='red')

    elif uniprot_file_path:
        if download:
            download_file_from_server(uniprot_file_path)
        return uniprot_file_path
    elif ncbi_file_path:
        if download:
            download_file_from_server(ncbi_file_path)
        return ncbi_file_path

async def merge_uniprot_ncbi_fasta(uniprot_file_path, ncbi_file_path, loading_spinner):
    identifier = datetime.now().strftime("%d%m%Y%H%M%S")
    fasta_file = f"{identifier}_Merged.fasta"
    loading_spinner.set_visibility(True)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://134.158.151.55/merge_uniprot_ncbi_fasta", json={"uniprot_file": uniprot_file_path, "ncbi_file": ncbi_file_path, "merged_file": fasta_file})
            if response.status_code == 200:
                data = response.json()
                print(f"Response from Flask: {data}")
                return data['file']
            else:
                print(f"Flask request failed with status code: {response.status_code}")
                return 'Failed'
    except Exception as e:
        print(f"Error occurred: {e}")
        return 'Failed'
    finally:
        loading_spinner.set_visibility(False)
        
def pipeline2_launcher():
    config.pipeline2_launcher_container.set_visibility(True)
    
    with config.pipeline2_launcher_container:
        ui.markdown(
            "The phylogenetic analysis performed on the selected sequences has conducted to the selection of one sequence per species."
        ).classes('text-lg mb-6')
        
        with ui.row():
            ui.markdown(
                "Download a FASTA file containing one representative sequence per species. "
                "For nucleotide sequences, you may also continue your analysis on [DataMonkey](http://www.datamonkey.org/)."
            ).classes('text-lg')
            create_species_fasta_btn = ui.button(
                'Download FASTA',
                on_click=lambda: ui.notify('Feature coming soon!', color='info')
            )
            styles.apply_purple_color(create_species_fasta_btn)
            styles.apply_download_icon(create_species_fasta_btn)
            
        with ui.row():
            with ui.column():
                ui.markdown(
                    "Restart the phylogenetic analysis pipeline to obtain accurate phylogenetic distances between species."
                ).classes('text-lg')
                ui.markdown(
                    "NB: The current results may be biased due to the presence of multiple sequences per species in the initial dataset."
                ).classes('text-sm italic')
            run_pipeline2_btn = ui.button(
                'Build phylogenetic Tree',
                on_click=lambda: handle_pipeline2()
            )
            styles.apply_violet_color(run_pipeline2_btn)
            styles.apply_play_icon(run_pipeline2_btn)

async def handle_pipeline2():
    try:
        result = await run_full_pipeline(config.pipeline2_container, run_bmge=True)
        if result == "success":
            ui.notify('Pipeline completed successfully!', color='positive')
            with config.pipeline2_results:
                config.pipeline2_results.set_visibility(True)
                ui.label('Phylogenetic Analysis Results').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
                show_download_results(config.pipeline2_results, run_bmge=True)

                ui.markdown(
                    "You can combine the phylogenetic distances of the branch length file with other life history traits of the species "
                    "to create a comprehensive dataset. This dataset could be used in a multivariate model "
                    "to explore potential correlations and relationships between phylogenetic distances and "
                    "species traits."
                ).classes('text-lg')
                
                ui.markdown('Thanks for using EvoTree').classes('text-lg')
        else:
            ui.notify('Pipeline failed', color='negative')
    except Exception as e:
        ui.notify(f'Pipeline error: {str(e)}', color='negative')
        
async def run_full_pipeline(pipeline_container, run_bmge=False):
    pipeline_container.clear()
    pipeline_container.set_visibility(True)
    
    with pipeline_container:
        pipeline_steps = [
            {"name": "Creating FASTA file", "color": "#FF6B35"},
            {"name": "Running MAFFT alignment", "color": "#F7931E"}, 
        ]
        if run_bmge:
            pipeline_steps += [{"name": "Filtering with BMGE", "color": "#FFD23F"}]
        pipeline_steps += [
                {"name": "Building tree with IQTREE", "color": "#06FFA5"},
                {"name": "Calculating distances", "color": "#4ECDC4"}
        ]
        ui.label('Pipeline Progress').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        progress_label = ui.label('Starting pipeline...').classes('text-lg font-semibold mb-6 text-center')
        
        step_container = ui.row().classes('w-full justify-between mb-3')
        step_indicators = []
        for i, step in enumerate(pipeline_steps):
            with step_container:
                indicator = ui.column().classes('items-center')
                with indicator:
                    circle = ui.element('div').classes(f'w-12 h-12 rounded-full border-4 border-gray-300 flex items-center justify-center text-white font-bold text-lg transition-all duration-500 ease-in-out')
                    ui.label(step['name']).classes('text-sm text-center mt-3 max-w-24')
                step_indicators.append((circle, step['color']))
    
    try:
        # Step 1: Create FASTA
        await update_progress(progress_label, step_indicators, 0, "Creating FASTA file...")
        config.current_fasta_file = await create_fasta(download=False)
        if config.current_fasta_file == 'Failed':
            raise Exception("Failed to create FASTA file")
        
        # Step 2: MAFFT
        await update_progress(progress_label, step_indicators, 1, "Running MAFFT alignment...")
        config.current_mafft_file = await run_mafft_pipeline(config.current_fasta_file)
        
        # config.current_mafft_file = "evotree/simul/29102025131303_Merged_mafft.fasta"
        
        if run_bmge:
            # Step 3: BMGE  
            await update_progress(progress_label, step_indicators, 2, "Filtering with BMGE...")
            config.current_bmge_file = await run_bmge_pipeline(config.current_mafft_file)
            
            # config.current_bmge_file = "evotree/simul/29102025131303_Merged_mafft_bmge.fasta"
        else:
            config.current_bmge_file = config.current_mafft_file
        
        # Step 4: IQTREE
        await update_progress(progress_label, step_indicators, 2 if not run_bmge else 3, "Building phylogenetic tree...")
        config.current_iqtree_file = await run_iqtree_pipeline(config.current_bmge_file)
        
        # config.current_iqtree_file = "evotree/simul/29102025131303_Merged_mafft_bmge.fasta.treefile"
        
        # Step 5: NW Distance
        await update_progress(progress_label, step_indicators, 3 if not run_bmge else 4, "Calculating branch lengths...")
        config.current_nw_distance_file = await run_nw_distance_pipeline(config.current_iqtree_file)
        
        await update_progress(progress_label, step_indicators, 5, "")

        return "success"
    except Exception as e:
        progress_label.text = f"Pipeline failed: {str(e)}"
        ui.notify(f'Pipeline error: {str(e)}', color='red')
        return "failed"

def show_download_results(container, run_bmge):
    with container:        
        files_to_download = [
            {
                'file': config.current_fasta_file,
                'label': '📄 Original FASTA',
                'color': '#FF6B35'
            },
            {
                'file': config.current_mafft_file,
                'label': '⛓️ MAFFT Alignment',
                'color': '#F7931E'
            }
        ]
        
        if run_bmge and config.current_bmge_file != config.current_mafft_file:
            files_to_download.append({
                'file': config.current_bmge_file,
                'label': '✂️ BMGE Filtered',
                'color': '#FFD23F'
            })
        
        files_to_download.extend([
            {
                'file': config.current_iqtree_file,
                'label': '🌴 IQ-TREE Result',
                'color': '#06FFA5'
            },
            {
                'file': config.current_nw_distance_file,
                'label': '📊 Branch Length',
                'color': '#4ECDC4'
            }
        ])

        with ui.row().classes('w-full justify-between mb-6'):
            for file_info in files_to_download:
                if file_info['file']:
                    with ui.column().classes('items-center'):
                        ui.label(file_info['label']).classes('text-base font-medium')
                        download_btn = ui.button(
                        '', 
                        on_click=lambda f=file_info['file']: download_file_from_server(f)
                        ).classes('px-4 py-1')
                        
                        styles.apply_download_icon(download_btn)
                        styles.apply_custom_color(download_btn, file_info['color'])
            
async def update_progress(progress_label, step_indicators, current_step, message):
    progress_label.text = message
    for i, (circle, color) in enumerate(step_indicators):            
        if i < current_step:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 border-green-500 bg-green-500 flex items-center justify-center text-white font-bold text-lg transition-all duration-500 ease-in-out transform scale-110 shadow-lg')
        elif i == current_step:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 flex items-center justify-center text-white font-bold text-lg transition-all duration-300 ease-in-out transform scale-125 shadow-2xl animate-bounce')
            circle.style(f'border-color: {color}; background-color: {color}; box-shadow: 0 0 20px {color}50;')
            circle.text = str(i + 1)
        else:
            circle.classes(replace=f'w-12 h-12 rounded-full border-4 border-gray-300 bg-gray-100 flex items-center justify-center text-gray-500 font-bold text-lg transition-all duration-500 ease-in-out')
            circle.text = str(i + 1)

async def run_mafft_pipeline(fasta_file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/mafft_start", json={"fasta_file": fasta_file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/mafft_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"MAFFT error: {status_data.get('message', '')}")
        else:
            raise Exception(f"MAFFT request failed with status code: {response.status_code}")

async def run_bmge_pipeline(mafft_file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/bmge_start", json={"fasta_file": mafft_file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/bmge_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"BMGE error: {status_data.get('message', '')}")
        else:
            raise Exception(f"BMGE request failed with status code: {response.status_code}")

async def run_iqtree_pipeline(file_path):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/iqtree_start", json={"fasta_file": file_path}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/iqtree_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"IQTREE error: {status_data.get('message', '')}")
        else:
            raise Exception(f"IQTREE request failed with status code: {response.status_code}")

async def run_nw_distance_pipeline(treefile):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{config.API_BASE_URL}/nw_distance_start", json={"treefile": treefile}, timeout=10)
        if response.status_code == 200:
            job_id = response.json()['job_id']
            while True:
                await asyncio.sleep(2)
                status_resp = await client.get(f"{config.API_BASE_URL}/nw_distance_status?id={job_id}")
                status_data = status_resp.json()
                if status_data['status'] == 'finished':
                    return status_data['file']
                elif status_data['status'] == 'error':
                    raise Exception(f"NW Distance error: {status_data.get('message', '')}")
        else:
            raise Exception(f"NW Distance request failed with status code: {response.status_code}")
        