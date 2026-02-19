import json
import os

def load_data():
    """
    Carga el JSON desde grammarflow/data/data.json
    Funciona aunque ejecutes el proyecto desde diferentes rutas.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))  # .../grammarflow
    data_path = os.path.join(base_dir, "data", "data.json")

    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)
