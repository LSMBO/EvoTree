from nicegui import ui
import numpy as np
import config

def get_sequence_length(item):
    """Extract sequence length from unified data structure"""
    # All data now uses sequence_length (both proteins and genes)
    return item.get('sequence_length', 0)

def create_length_distribution_chart(data_items, user_min_length=None, user_max_length=None):
    if user_min_length == '*':
        user_min_length = None
    if user_max_length == '*':
        user_max_length = None
    
    # Extract lengths using the new unified function
    lengths = []
    for item in data_items:
        length = get_sequence_length(item)
        if length and length > 0:
            lengths.append(length)
    
    if not lengths:
        data_type = "genes" if config.current_search_type == 'gene' else "proteins"
        ui.markdown(f"**No valid sequence lengths found for the provided {data_type}.**")
        return
    
    if user_min_length is not None and user_max_length is not None:
        min_length = user_min_length
        max_length = user_max_length
    else:
        min_length = min(lengths)
        max_length = max(lengths)
    
    length_range = max_length - min_length
    default_interval = 1000
    if length_range < 5000:
        default_interval = 50
    if length_range < 100:
        default_interval = 10
        

    intervals = ui.input(f'Amino acids per bar (press Enter)', value=str(default_interval)).classes('w-full mb-4')

    def update_chart():
        try:
            interval_value = int(intervals.value)
            if interval_value <= 0:
                interval_value = default_interval
        except ValueError:
            interval_value = default_interval

        # Create bins starting exactly from min_length
        bins = [min_length]
        current_bin = min_length
        
        # Add bins with regular intervals until we exceed max_length
        while current_bin + interval_value < max_length:
            current_bin += interval_value
            bins.append(current_bin)
        
        # Add the final bin edge (max_length)
        bins.append(max_length)

        counts, _ = np.histogram(lengths, bins=bins)
        
        # Create labels for each bin
        x_labels = []
        for i in range(len(bins)-1):
            start = bins[i]
            end = bins[i+1]
            x_labels.append(f"{start}-{end}") 
        
        chart_area.clear()
        
        with chart_area:
            needs_rotation = len(x_labels) > 6
            
            xaxis_label = {
                'interval': 0,
                'rotate': 90 if needs_rotation else 0,
                'fontSize': 10 if needs_rotation else 12,
            }
            
            grid_options = {
                'top': 20,
                'left': 60,
                'right': 20,
                'bottom': 120 if needs_rotation else 60
            }
            
            ui.echart({
                'xAxis': {
                    'type': 'category',
                    'data': x_labels,
                    'axisLabel': xaxis_label
                },
                'yAxis': {
                    'type': 'value',
                    'axisLabel': {'fontSize': 10}
                },
                'series': [{
                    'type': 'bar',
                    'data': counts.tolist(),
                    'itemStyle': {'color': '#3B82F6'}
                }],
                'grid': grid_options,
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'shadow'},
                }
            }).classes('w-full').style('height: 300px;')

            avg_length = sum(lengths) / len(lengths)
            ui.markdown(f"**{len(lengths)} sequences** | Avg: {avg_length:.1f} residues | Min: {min_length} residues | Max: {max_length} residues").classes('text-sm text-gray-600 mt-2')

    chart_area = ui.column().classes('w-full')
    
    intervals.on('keydown.enter', lambda _: update_chart())
    
    update_chart()

