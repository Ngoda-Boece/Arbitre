"""Télécharge le jeu de données SNCF « Régularité mensuelle TGV par liaisons ».

Usage : python src/telecharger.py [--force]
Le fichier du dépôt est une photo datée : ne le remplacez (--force) que si vous
voulez aussi recalculer les réponses connues, car les données changent chaque mois.
"""
import argparse
import hashlib
from pathlib import Path

import requests

from config import FICHIER_BRUT

URL = (
    "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/"
    "regularite-mensuelle-tgv-aqst/exports/csv"
)
PARAMETRES = {"delimiter": ";", "use_labels": "true", "with_bom": "true"}


def telecharger(sortie: Path, force: bool = False) -> Path:
    if sortie.exists() and not force:
        print(f"Déjà présent, rien à faire : {sortie} (--force pour remplacer)")
        return sortie

    reponse = requests.get(URL, params=PARAMETRES, timeout=120)
    reponse.raise_for_status()
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_bytes(reponse.content)

    empreinte = hashlib.sha256(reponse.content).hexdigest()
    print(f"Écrit : {sortie} ({len(reponse.content)} octets, sha256 {empreinte})")
    return sortie


if __name__ == "__main__":
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--force", action="store_true")
    analyseur.add_argument("--sortie", type=Path, default=FICHIER_BRUT)
    arguments = analyseur.parse_args()
    telecharger(arguments.sortie, arguments.force)
