import requests
from flask import Blueprint, request, jsonify
import os, shutil, sys
from datetime import datetime
import logging

clear_bp = Blueprint('clear_bp', __name__)
    
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler(sys.stdout)])

@clear_bp.route('/clear', methods=['POST'])
def clear():
    date_limit_input = request.json.get('date_limit', None)
    if not date_limit_input:
        date_limit_input = datetime.now().strftime("%d%m%Y%H%M%S")
    
    date_limit = {
        'y': date_limit_input[4:8],
        'm': date_limit_input[2:4],
        'd': date_limit_input[0:2],
        'h': date_limit_input[8:10],
        'min': date_limit_input[10:12],
        's': date_limit_input[12:14]
    }

    tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
    logger.info(f"Clearing files older than {date_limit_input} in {tmp_dir}")
    for file in os.listdir(tmp_dir):
        file_path = os.path.join(tmp_dir, file)

        # Skip files or directories that don't start with a number
        if not file[0].isdigit():
            logger.info(f"Warning: Skipping {file} as it does not start with a number")
            continue

        file_date = {
            'y': file[4:8],
            'm': file[2:4],
            'd': file[0:2],
            'h': file[8:10],
            'min': file[10:12],
            's': file[12:14]
        }

        # Compare file date with date_limit
        for attr in ['y', 'm', 'd', 'h', 'min', 's']:
            if int(file_date[attr]) < int(date_limit[attr]):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                break
            elif int(file_date[attr]) > int(date_limit[attr]):
                break

    return jsonify({"status": "success", "message": "Old files and directories cleared"})

