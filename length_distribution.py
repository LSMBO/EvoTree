from nicegui import ui
import numpy as np
import math

def create_length_distribution_chart(proteins):
    lengths = [protein['sequence']['length'] for protein in proteins if protein['sequence']['length'] is not None]
    
    if not lengths:
        ui.markdown("**No valid sequence lengths found for the provided proteins.**")
        return
    
    intervals = ui.input('Intervals (e.g., 50)', value='50').classes('flex-grow')
    chart_container = ui.row()

    def update_chart():
        try:
            interval_value = int(intervals.value)
        except ValueError:
            interval_value = 50

        min_length = min(lengths)
        max_length = max(lengths)

        bin_start = (min_length // interval_value) * interval_value
        bin_end = math.ceil(max_length / interval_value) * interval_value
        bins = np.arange(bin_start, bin_end + interval_value, interval_value)

        counts, _ = np.histogram(lengths, bins=bins)
        x_labels = []
        for i in range(len(bins)-1):
            if interval_value == 1:
                if i < len(bins)-2:
                    x_labels.append(f"{bins[i]} residues")
                else:
                    x_labels.append(f"{bins[i]} or {bins[i]+1} residues")
            else:
                if i < len(bins)-2:
                    x_labels.append(f"{bins[i]} to {bins[i+1]-1} residues")
                else:
                    x_labels.append(f"{bins[i]} to {bins[i+1]} residues")
        chart_container.clear()
        xaxis_label = {
            'interval': 0,
            'rotate': 90 if len(x_labels) > 6 else 0,
        }
        with chart_container:
            ui.markdown("### Sequence Length Distribution")
            ui.echart({
                'xAxis': {
                    'type': 'category',
                    'data': x_labels,
                    'axisLabel': xaxis_label
                },
                'yAxis': {'type': 'value'},
                'series': [{
                    'type': 'bar',
                    'data': counts.tolist(),
                    'itemStyle': {'color': '#3B82F6'}
                }],
                'grid': {
                    'bottom': 150
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'shadow'}
                }
            }).classes('w-full h-96')

            avg_length = sum(lengths) / len(lengths)
            ui.markdown(f"**Average Length:** {avg_length:.2f} amino acids")
            ui.markdown(f"**Max Length:** {max_length} amino acids")
            ui.markdown(f"**Min Length:** {min_length} amino acids")

    intervals.on('blur', lambda _: update_chart())  # Update chart when input loses focus
    update_chart()  # Initial chart rendering

