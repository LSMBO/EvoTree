from nicegui import ui

def download_file_from_server(file):
    ui.download(f"http://134.158.151.55/download?file={file}")