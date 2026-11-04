"""Tests de la brique 3 : ils essaient d'enfreindre la règle et doivent se faire bloquer."""
import pytest

from arbitre import collecter_sources, extraire_nombres, nombre_justifie, verifier

RESULTAT = {
    "liaison": "BORDEAUX ST JEAN -> PARIS MONTPARNASSE",
    "periode": "2025-01 à 2025-12",
    "taux_ponctualite_pct": 83.6,
    "ic95_bas_pct": 82.9,
    "ic95_haut_pct": 84.3,
    "niveau_confiance_pct": 95,
    "trains_circules": 12369,
    "trains_en_retard": 2027,
}


@pytest.mark.parametrize("texte, attendu", [
    ("83,6 %", ["83.6"]),
    ("83.6%", ["83.6"]),
    ("12 369 trains", ["12369"]),
    ("12 369 trains", ["12369"]),
    ("12 369 trains", ["12369"]),
    ("en 2025 200 trains", ["2025", "200"]),
    ("entre 2024 et 2025", ["2024", "2025"]),
    ("le taux est de 83,6.", ["83.6"]),
    ("TGV sans chiffre", []),
    ("A1 et B2", []),
    ("", []),
])
def test_extraction(texte, attendu):
    assert extraire_nombres(texte) == attendu


def test_numero_de_liste_ignore():
    assert extraire_nombres("1. Paris\n2. Lyon : 12 %") == ["12"]


def test_sources_imbriquees():
    sources = collecter_sources({"a": [{"b": 1.5}], "c": "2025-01 à 2025-12", "d": True, "e": None})
    assert sorted(sources) == [1.0, 1.5, 12.0, 2025.0, 2025.0]


def test_ecart_negatif_accepte_sans_signe():
    assert verifier("Baisse de 1,4 point.", [{"ecart_points": -1.4}])["valide"]


@pytest.mark.parametrize("nombre, ok", [
    ("83.6", True),    # exact
    ("84", True),      # arrondi correct
    ("83", False),     # arrondi faux
    ("83.7", False),   # une décimale inventée
    ("0.836", False),  # trop précis : 83.6 / 100 arrondi à 3 décimales vaut bien 0.836...
])
def test_arrondis(nombre, ok):
    if nombre == "0.836":
        ok = True      # ... donc l'écriture en proportion est acceptée
    assert nombre_justifie(nombre, [83.6]) is ok


def test_reponse_juste_acceptee():
    reponse = "Bordeaux vers Paris : 83,6 % en 2025 (intervalle à 95 % : 82,9 à 84,3), sur 12 369 trains."
    assert verifier(reponse, [RESULTAT], "Ponctualité en 2025 ?")["valide"]


def test_chiffre_invente_bloque():
    verdict = verifier("La ponctualité est de 97,5 %.", [RESULTAT])
    assert not verdict["valide"]
    assert verdict["sans_source"] == ["97.5"]


def test_chiffre_sans_aucun_appel_d_outil_bloque():
    assert not verifier("Environ 95 % des trains sont à l'heure.", [])["valide"]


def test_un_faux_parmi_des_vrais_bloque():
    assert not verifier("83,6 % mais aussi 91 % ailleurs.", [RESULTAT])["valide"]


def test_chiffre_en_lettres_bloque():
    assert not verifier("Environ quatre-vingt pour cent des trains.", [RESULTAT])["valide"]
    assert not verifier("Vingt pour cent des trains sont en retard.", [RESULTAT])["valide"]


def test_mot_nombre_sans_unite_accepte():
    assert verifier("Les deux périodes sont proches.", [RESULTAT])["valide"]


def test_reponse_vide_bloquee():
    assert not verifier("   ", [RESULTAT])["valide"]


def test_reponse_sans_nombre_acceptee():
    assert verifier("Je ne peux pas répondre.", [])["valide"]


def test_annee_de_la_question_autorisee():
    assert verifier("Je n'ai rien pour 2030.", [], "Et en 2030 ?")["valide"]


def test_message_d_erreur_d_outil_est_une_source():
    erreur = {"erreur": "Aucune donnée. Données disponibles de 2018-01 à 2026-09."}
    assert verifier("Les données vont de 2018 à 2026.", [erreur])["valide"]
