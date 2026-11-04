"""Démonstration de soutenance, en trois actes.

Acte 1 : Qwen seul répond à une question de ponctualité.
Acte 2 : le système répond à la même question avec un vrai calcul.
Acte 3 : on injecte une réponse au chiffre inventé, et l'Arbitre la bloque.

Usage :
  python src/demo.py                (les trois actes, Ollama doit tourner)
  python src/demo.py --sans-modele  (acte 3 seul, sans Ollama)
"""
import argparse

import outils
from agent import repondre, repondre_seul

QUESTION = "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"


def faux_modele_menteur():
    """Fabrique un modèle simulé : il appelle le vrai outil, puis invente quand même 97,5 %.

    La fermeture garde son compteur `tour` entre deux appels. Elle remplace le vrai
    modèle dans repondre(), exactement comme dans les tests.
    """
    tour = {"numero": 0}

    def modele(messages, liste_outils, seed):
        tour["numero"] += 1
        if tour["numero"] == 1:
            arguments = {"debut": "2025", "fin": "2025", "depart": "Bordeaux", "arrivee": "Paris"}
            return {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "taux_ponctualite", "arguments": arguments}}
            ]}
        return {"role": "assistant", "content": "La ponctualité est excellente : 97,5 %."}

    return modele


def titre(texte):
    print(f"\n{'=' * 70}\n{texte}\n{'=' * 70}")


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--sans-modele", action="store_true")
    arguments = analyseur.parse_args()
    df = outils.charger()

    if not arguments.sans_modele:
        titre("ACTE 1 : Qwen seul, sans outils ni Arbitre")
        print(f"Question : {QUESTION}\n")
        print(repondre_seul(QUESTION)["reponse"])

        titre("ACTE 2 : le système complet")
        print(f"Question : {QUESTION}\n")
        trace = repondre(QUESTION, df)
        for appel in trace["appels"]:
            print(f"Outil appelé : {appel['outil']} {appel['arguments']}")
            resultat = appel["resultat"]
            if "taux_ponctualite_pct" in resultat:
                print(f"Résultat : {resultat['taux_ponctualite_pct']} % "
                      f"(intervalle à 95 % : {resultat['ic95_bas_pct']} à {resultat['ic95_haut_pct']})")
        print(f"\nRéponse [{trace['statut']}] : {trace['reponse']}")

    titre("ACTE 3 : on injecte un chiffre inventé (modèle simulé)")
    trace = repondre(QUESTION, df, modele=faux_modele_menteur())
    for rejet in trace["rejets"]:
        print(f"Bloqué : « {rejet['reponse']} »\nMotif : {rejet['motif']}\n")
    print(f"Réponse montrée à l'utilisateur [{trace['statut']}] : {trace['reponse']}")


if __name__ == "__main__":
    main()
