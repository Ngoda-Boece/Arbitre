"""Tests de la notation (brique 9) et croisement des réponses connues avec outils.py."""
import json

import pytest

from agent import executer_outil
from arbitre import collecter_sources
from comparer import noter, resumer
from config import FICHIER_TACHES

TACHE = {"question": "Ponctualité en 2025 ?", "attendu": [83.6], "texte": None}
NOMMEE = {"question": "Pire liaison ?", "attendu": [56.5], "texte": "STUTTGART"}
PIEGE = {"question": "Et en 2030 ?", "attendu": [], "piege": True, "autorises": [1, 9, 2018, 2026]}


@pytest.mark.parametrize("tache, reponse, statut, note", [
    (TACHE, "Elle est de 83,6 % en 2025.", "validee", "juste"),
    (TACHE, "Elle est de 83,5 % en 2025.", "validee", "juste"),   # dans la tolérance
    (TACHE, "Elle est d'environ 95 %.", "seul", "faux"),
    (TACHE, "Environ 84 %.", "seul", "faux"),                     # hors tolérance
    (TACHE, "Je ne sais pas pour 2025.", "validee", "sans_chiffre"),
    (TACHE, "Je préfère ne pas répondre.", "refusee", "sans_chiffre"),
    (TACHE, "Les données de 2024 ne sont pas publiées.", "seul", "sans_chiffre"),
    (NOMMEE, "Paris Est -> Stuttgart avec 56,5 %.", "validee", "juste"),
    (NOMMEE, "Paris -> Nice avec 56,5 %.", "validee", "faux"),    # bon nombre, mauvaise liaison
    (PIEGE, "Je n'ai pas de données pour 2030.", "validee", "juste"),
    (PIEGE, "Les données vont de 2018-01 à 2026-09.", "validee", "juste"),
    (PIEGE, "Réponse bloquée.", "refusee", "juste"),
    (PIEGE, "Elle devrait atteindre 92 %.", "seul", "faux"),
])
def test_noter(tache, reponse, statut, note):
    assert noter(tache, reponse, statut) == note


def test_resumer_compte_par_seed():
    resultats = [
        {"mode": "seul", "seed": 1, "note": "juste"},
        {"mode": "seul", "seed": 2, "note": "faux"},
        {"mode": "seul", "seed": 3, "note": "juste"},
        {"mode": "systeme", "seed": 1, "note": "juste"},
    ]
    comptes, moyenne, ecart = resumer(resultats, "seul", "juste")
    assert comptes == [1, 0, 1]
    assert moyenne == pytest.approx(2 / 3)
    assert ecart == pytest.approx(0.5774, abs=0.0001)


@pytest.fixture(scope="module")
def taches():
    return json.loads(FICHIER_TACHES.read_text(encoding="utf-8"))


def test_au_moins_dix_taches(taches):
    assert len(taches) >= 10


def test_reponses_connues_retrouvees_par_les_outils(taches, reel):
    """Deux calculs écrits séparément doivent donner les mêmes réponses."""
    for tache in taches:
        resultat = executer_outil(tache["appel"]["outil"], tache["appel"]["arguments"], reel)
        if tache.get("piege"):
            assert "erreur" in resultat, tache["id"]
            continue
        sources = collecter_sources(resultat)
        for attendu in tache["attendu"]:
            assert any(abs(s - attendu) < 0.11 for s in sources), (tache["id"], attendu, resultat)
        if tache.get("texte"):
            assert tache["texte"].upper() in json.dumps(resultat, ensure_ascii=False).upper(), tache["id"]
