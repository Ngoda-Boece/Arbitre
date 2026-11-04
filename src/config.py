import os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

Data_RAW = RACINE / "data" / "raw"
Data_CLEAN = RACINE / "data" / "clean"

FICHIER_BRUT = Data_RAW / "regularite-mensuelle-tgv-aqst.csv"
FICHIER_PROPRE = Data_CLEAN / "regularite_propre.csv"
JOURNAL_NETTOYAGE = RACINE / "data" / "journal_nettoyage.md"

DOSSIER_TRACES = RACINE / "traces"    # une trace par exécution, non versionnée
DOSSIER_PREUVES = RACINE / "preuves"  # les résultats gardés pour EVIDENCE.md
FICHIER_TACHES = RACINE / "taches" / "taches.json"


def reglages_llm():
    """Par défaut : Ollama en local. Les variables d'environnement permettent
    de passer sur llama-server (port 8080) ou sur Cerebras sans toucher au code."""
    return {
        "model": os.environ.get("LLM_MODEL", "qwen3.5:4b-q4_K_M"),
        "base_url": os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        "api_key": os.environ.get("LLM_API_KEY", "local"),
    }
