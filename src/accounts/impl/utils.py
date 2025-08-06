import json
from pathlib import Path
from typing import Dict, Any


def load_json_data(json_path: Path) -> Dict[str, Any]:
    with open(json_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        return data

def save_json_data(path: Path, data: Dict[str, Any]) -> bool:
    """
    Перезаписывает JSON-файл по path содержимым data.
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        return True