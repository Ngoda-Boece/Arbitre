"""Banc de comparaison (brique 9) : mon système face à Qwen seul.

Chaque question passe sur les deux systèmes, avec 3 seeds, soit 72 exécutions.
Une seed est le point de départ du hasard du modèle : changer de seed donne une autre
réponse possible, ce qui permet de mesurer la dispersion.

Chaque résultat est écrit dès qu'il arrive : si le PC s'arrête, on relance la même
commande et elle reprend là où elle en était.

Usage :
  python src/comparer.py            lance ce qui manque, puis écrit le rapport
  python src/comparer.py --rapport  recalcule les notes et le rapport, sans le modèle
"""
import argparse
import json
import statistics

import outils
from agent import repondre, repondre_seul
from arbitre import extraire_nombres
from config import DOSSIER_PREUVES, FICHIER_TACHES

SEEDS = [1, 2, 3]
MODES = ["systeme", "seul"]
TOLERANCE = 0.11  # 83,6 attendu : 83,5 à 83,7 acceptés, 84 non
FICHIER_RESULTATS = DOSSIER_PREUVES / "resultats.jsonl"  # une exécution par ligne
FICHIER_RAPPORT = DOSSIER_PREUVES / "comparaison.md"


def noter(tache, reponse, statut):
    """Classe une réponse en trois catégories.

    juste        : les nombres (et le nom) attendus sont présents.
    sans_chiffre : aucun chiffre donné. Inutile, mais personne n'est trompé.
    faux         : un chiffre est affirmé et il n'est pas le bon. C'est le pire cas.
    """
    if statut == "refusee":
        return "juste" if tache.get("piege") else "sans_chiffre"

    question = {float(n) for n in extraire_nombres(tache["question"])}
    nombres = [float(n) for n in extraire_nombres(reponse)]
    # Une année citée (« les données de 2024 ») n'est pas un chiffre de ponctualité affirmé.
    nouveaux = [n for n in nombres if n not in question and not 1900 <= n <= 2100]

    if tache.get("piege"):
        # Citer les bornes des données est permis ; tout autre nombre est inventé.
        inventes = [n for n in nouveaux if n not in tache["autorises"]]
        return "faux" if inventes else "juste"

    nombres_ok = all(
        any(abs(n - attendu) <= TOLERANCE for n in nombres) for attendu in tache["attendu"]
    )
    texte_ok = not tache.get("texte") or tache["texte"].upper() in reponse.upper()
    if nombres_ok and texte_ok:
        return "juste"
    return "faux" if nouveaux else "sans_chiffre"


def lire_resultats():
    if not FICHIER_RESULTATS.exists():
        return []
    with open(FICHIER_RESULTATS, encoding="utf-8") as fichier:
        return [json.loads(ligne) for ligne in fichier if ligne.strip()]


def renoter(taches, resultats):
    """Recalcule les notes depuis les réponses déjà enregistrées, sans relancer le modèle.

    Ainsi, corriger la notation s'applique aussi aux anciennes exécutions.
    """
    par_id = {tache["id"]: tache for tache in taches}
    for resultat in resultats:
        resultat["note"] = noter(par_id[resultat["tache"]], resultat["reponse"], resultat["statut"])
    with open(FICHIER_RESULTATS, "w", encoding="utf-8") as fichier:
        for resultat in resultats:
            print(json.dumps(resultat, ensure_ascii=False), file=fichier)
    return resultats


def lancer(taches):
    """Exécute uniquement les combinaisons qui ne sont pas déjà dans le fichier."""
    deja_faits = {(r["mode"], r["tache"], r["seed"]) for r in lire_resultats()}
    df = outils.charger()
    DOSSIER_PREUVES.mkdir(exist_ok=True)

    for seed in SEEDS:
        for tache in taches:
            for mode in MODES:
                if (mode, tache["id"], seed) in deja_faits:
                    continue
                if mode == "systeme":
                    trace = repondre(tache["question"], df, seed=seed)
                else:
                    trace = repondre_seul(tache["question"], seed=seed)
                trace.update(
                    mode=mode, tache=tache["id"],
                    note=noter(tache, trace["reponse"], trace["statut"]),
                )
                with open(FICHIER_RESULTATS, "a", encoding="utf-8") as fichier:
                    fichier.write(json.dumps(trace, ensure_ascii=False) + "\n")
                print(f"{tache['id']} {mode:8} seed {seed} : {trace['note']:12} {trace['secondes']} s",
                      flush=True)


def resumer(resultats, mode, note):
    """Pour une note, renvoie le compte par seed, leur moyenne et leur écart-type."""
    comptes = [
        sum(r["mode"] == mode and r["seed"] == seed and r["note"] == note for r in resultats)
        for seed in SEEDS
    ]
    return comptes, statistics.mean(comptes), statistics.stdev(comptes)


def ecrire_rapport(taches, resultats):
    lignes = [
        "# Comparaison mesurée (brique 9)", "",
        f"{len(taches)} questions à réponse connue, seeds {SEEDS}, modèle Qwen3.5-4B.",
        f"Exécutions enregistrées : {len(resultats)}.", "",
        "| Mesure | Système (moyenne ± écart-type) | Qwen seul (moyenne ± écart-type) |",
        "|---|---|---|",
    ]
    for note, libelle in [("juste", "Réponses justes"), ("faux", "Chiffres faux affirmés"),
                          ("sans_chiffre", "Sans chiffre")]:
        cellules = []
        for mode in MODES:
            comptes, moyenne, ecart = resumer(resultats, mode, note)
            cellules.append(f"{moyenne:.2f} ± {ecart:.2f} sur {len(taches)} (seeds : {comptes})")
        lignes.append(f"| {libelle} | {cellules[0]} | {cellules[1]} |")

    temps = []
    for mode in MODES:
        valeurs = [r["secondes"] for r in resultats if r["mode"] == mode]
        temps.append(f"{statistics.mean(valeurs):.1f} s" if valeurs else "-")
    lignes += [f"| Temps moyen par question | {temps[0]} | {temps[1]} |", ""]

    lignes += ["## Détail par question", "", "| Tâche | Question | Système | Qwen seul |", "|---|---|---|---|"]
    for tache in taches:
        cellules = []
        for mode in MODES:
            notes = [r["note"] for r in sorted(resultats, key=lambda r: r["seed"])
                     if r["mode"] == mode and r["tache"] == tache["id"]]
            cellules.append(", ".join(notes))
        lignes.append(f"| {tache['id']} | {tache['question']} | {cellules[0]} | {cellules[1]} |")

    FICHIER_RAPPORT.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[:11]))


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--rapport", action="store_true")
    arguments = analyseur.parse_args()

    taches = json.loads(FICHIER_TACHES.read_text(encoding="utf-8"))
    if not arguments.rapport:
        lancer(taches)
    ecrire_rapport(taches, renoter(taches, lire_resultats()))


if __name__ == "__main__":
    main()
