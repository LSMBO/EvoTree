from nicegui import ui
import config
import styles
from utils import download_file_from_server
from pipeline import create_fasta_from_branch_length, run_full_pipeline

def show_pipeline1_results(pipeline_data):
    with config.pipeline2_launcher_container:
        config.pipeline2_launcher_container.set_visibility(True)
        
        ui.label('Phylogenetic Analysis Results').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        # Show download buttons for pipeline1 results
        show_download_results(config.pipeline2_launcher_container, pipeline_data, run_bmge=False)
        
        # Show pipeline2 launcher section
        show_pipeline2_launcher()


def show_pipeline2_results(pipeline_data):
    with config.pipeline2_results:
        config.pipeline2_results.set_visibility(True)
        
        ui.label('Phylogenetic Analysis Results').classes(f'text-2xl font-bold text-[{config.VIOLET_COLOR}] mb-6')
        
        # Show download buttons for pipeline2 results
        show_download_results(config.pipeline2_results, pipeline_data, run_bmge=True)
        
        # Final message
        ui.markdown(
            "You can combine the phylogenetic distances of the branch length file with other life history traits of the species "
            "to create a comprehensive dataset. This dataset could be used in a multivariate model "
            "to explore potential correlations and relationships between phylogenetic distances and "
            "species traits."
        ).classes('text-lg')
        
        ui.markdown('Thanks for using EvoTree').classes('text-lg font-bold mt-6')


def show_pipeline2_launcher():
    ui.markdown(
        "The phylogenetic analysis performed on the selected sequences has conducted to the selection of one sequence per species."
    ).classes('text-lg mb-6')
    
    with ui.row().classes('w-full gap-4 items-center'):
        ui.markdown(
            "Download a FASTA file containing one representative sequence per species. "
            "For nucleotide sequences, you may also continue your analysis on [DataMonkey](http://www.datamonkey.org/)."
        ).classes('text-lg flex-grow')

        create_species_fasta_btn = ui.button(
            'Download FASTA',
            on_click=lambda: create_fasta_from_branch_length(True, config.current_fasta_file, config.current_nw_distance_file)
        )
        styles.apply_purple_color(create_species_fasta_btn)
        styles.apply_download_icon(create_species_fasta_btn)
    
    ui.separator().classes('my-6')
    
    # Pipeline2 option
    with ui.row().classes('w-full gap-4'):
        with ui.column().classes('flex-grow'):
            ui.markdown(
                "Restart the phylogenetic analysis pipeline to obtain accurate phylogenetic distances between species."
            ).classes('text-lg')
            ui.markdown(
                "NB: The current results may be biased due to the presence of multiple sequences per species in the initial dataset."
            ).classes('text-sm italic')
        
        async def handle_pipeline2():
            try:
                config.pipeline2_data = await run_full_pipeline(config.pipeline2_container, run_bmge=True)
                
                if config.pipeline2_data != "failed":
                    ui.notify('Pipeline completed successfully!', color='positive')
                    show_pipeline2_results(config.pipeline2_data)
                else:
                    ui.notify('Pipeline failed', color='negative')
            except Exception as e:
                ui.notify(f'Pipeline error: {str(e)}', color='negative')
        
        run_pipeline2_btn = ui.button(
            'Build Phylogenetic Tree',
            on_click=lambda: handle_pipeline2()
        )
        styles.apply_violet_color(run_pipeline2_btn)
        styles.apply_play_icon(run_pipeline2_btn)


def show_download_results(container, pipeline_data, run_bmge):
    with container:        
        files_to_download = [
            {
                'file': pipeline_data['fasta_file'],
                'label': '📄 Original FASTA',
                'color': '#FF6B35'
            },
            {
                'file': pipeline_data['mafft_file'],
                'label': '⛓️ MAFFT Alignment',
                'color': '#F7931E'
            }
        ]
        
        if run_bmge and config.current_bmge_file != config.current_mafft_file:
            files_to_download.append({
                'file': pipeline_data['bmge_file'],
                'label': '✂️ BMGE Filtered',
                'color': '#FFD23F'
            })
        
        files_to_download.extend([
            {
                'file': pipeline_data['iqtree_file'],
                'label': '🌴 IQ-TREE Result',
                'color': '#06FFA5'
            },
            {
                'file': pipeline_data['nw_distance_file'],
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
