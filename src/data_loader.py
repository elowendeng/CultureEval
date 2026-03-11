# src/data_loader.py
import json
from typing import List, Dict


# Load JSON file
def load_benchmark(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data