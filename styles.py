import config

def apply_violet_color(btn):
    btn.classes('px-6 py-2 h-11 text-white rounded-lg shadow-md text-sm hover:text-base transition-all duration-200')
    btn.style(f'background-color: {config.VIOLET_COLOR} !important')

def apply_purple_color(btn):
    btn.classes('px-6 py-2 h-11 text-white rounded-lg shadow-md text-sm hover:text-base transition-all duration-200')
    btn.style('background-color: #A64AC9 !important')

def apply_default_color(btn):
    btn.classes('px-6 py-2 h-11 text-white rounded-lg shadow-md text-sm hover:text-base transition-all duration-200')

def apply_custom_color(btn, color):
    btn.classes('px-6 py-2 h-11 text-white rounded-lg shadow-md text-sm hover:text-base transition-all duration-200')
    btn.style(f'background-color: {color} !important')

def apply_custom_border_color(card, color):
    card.style(f'border-color: {color} !important')

def apply_download_icon(btn):
    btn.props('icon=download')

def apply_play_icon(btn):
    btn.props('icon=play_arrow')

def apply_filter_icon(btn):
    btn.props('icon=filter_list')

def apply_full_width(btn):
    btn.classes(add='w-full')
