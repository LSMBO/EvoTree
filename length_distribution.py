from nicegui import ui
import numpy as np
import math

def create_length_distribution_chart(proteins):
    lengths = [protein['sequence']['length'] for protein in proteins if protein['sequence']['length'] is not None]
    
    if not lengths:
        ui.markdown("**No valid sequence lengths found for the provided proteins.**")
        return

    min_length = min(lengths)
    max_length = max(lengths)

    bin_start = (min_length // 50) * 50
    bin_end = math.ceil(max_length / 50) * 50
    bins = np.arange(bin_start, bin_end + 50, 50)

    counts, _ = np.histogram(lengths, bins=bins)

    x_labels = [bins[i] for i in range(len(bins)-1)]

    ui.markdown("### Sequence Length Distribution")
    ui.echart({
        'xAxis': {
            'type': 'category',
            'data': x_labels,
            'axisLabel': {
                'interval': 0,
                'align': 'right',
                'rotate': 90
            }
        },
        'yAxis': {'type': 'value'},
        'series': [{
            'type': 'bar',
            'data': counts.tolist(),
            'itemStyle': {'color': '#3B82F6'}
        }]
    }).classes('w-full h-64')

    avg_length = sum(lengths) / len(lengths)
    ui.markdown(f"**Average Length:** {avg_length:.2f} amino acids")
    ui.markdown(f"**Max Length:** {max_length} amino acids")
    ui.markdown(f"**Min Length:** {min_length} amino acids")