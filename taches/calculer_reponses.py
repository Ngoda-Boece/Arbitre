"""Calcule les réponses connues des 12 questions de la brique 9 et écrit taches.json.

Ce script n'importe volontairement ni outils.py ni pandas. Il refait les calculs avec de
simples boucles sur le fichier nettoyé. Si les réponses venaient de outils.py, le test
comparerait mon code à lui-même et ne prouverait rien.

Usage : python taches/calculer_reponses.py   (après python src/nettoyer.py)
"""
import csv
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER_PROPRE = RACINE / "data" / "clean" / "regularite_propre.csv"
SORTIE = RACINE / "taches" / "taches.json"

CAUSES = {
    "cause_externe": "causes externes",
    "cause_infrastructure": "infrastructure",
    "cause_gestion_trafic": "gestion du trafic",
    "cause_materiel_roulant": "matériel roulant",
    "cause_gestion_gare": "gestion en gare",
    "cause_voyageurs": "prise en charge des voyageurs",
}


def lire():
    with open(FICHIER_PROPRE, encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier))


def filtrer(lignes, prefixe_date, depart=None, arrivee=None):
    """prefixe_date vaut « 2025 » pour une année ou « 2025-07 » pour un mois."""
    return [
        ligne for ligne in lignes
        if ligne["date"].startswith(prefixe_date)
        and (depart is None or ligne["gare_depart"] == depart)
        and (arrivee is None or ligne["gare_arrivee"] == arrivee)
    ]


def totaux(lignes):
    """Renvoie (trains circulés, trains en retard)."""
    circules = sum(int(ligne["circules"]) for ligne in lignes)
    retards = sum(int(ligne["retards_arrivee"]) for ligne in lignes)
    return circules, retards


def ponctualite(lignes):
    circules, retards = totaux(lignes)
    return 100 * (circules - retards) / circules


def part_retard_15(lignes, annee, meilleure):
    """Trouve la liaison extrême sur la part de trains à plus de 15 min (100 trains au moins)."""
    cumul = {}
    for ligne in filtrer(lignes, annee):
        cle = (ligne["gare_depart"], ligne["gare_arrivee"])
        circules, retards = cumul.get(cle, (0, 0))
        cumul[cle] = (circules + int(ligne["circules"]), retards + int(ligne["retards_15"]))
    parts = {cle: 100 * r / c for cle, (c, r) in cumul.items() if c >= 100}
    choix = min if meilleure else max
    cle = choix(parts, key=parts.get)
    return cle, parts[cle]


def cause_principale(lignes):
    """Cause la plus fréquente, chaque mois pesant selon son nombre de retards."""
    valides = [ligne for ligne in lignes if ligne["cause_externe"] != ""]
    poids_total = sum(int(ligne["retards_arrivee"]) for ligne in valides)
    parts = {
        libelle: sum(float(l[colonne]) * int(l["retards_arrivee"]) for l in valides) / poids_total
        for colonne, libelle in CAUSES.items()
    }
    libelle = max(parts, key=parts.get)
    return libelle, parts[libelle]


def construire(lignes):
    """Chaque tâche contient la question, les nombres et le texte attendus, et l'appel
    d'outil équivalent : tests/test_taches.py s'en sert pour croiser les deux calculs."""
    taches = []

    def ajouter(identifiant, question, attendu, appel, texte=None):
        taches.append({
            "id": identifiant, "question": question,
            "attendu": [round(valeur, 1) for valeur in attendu],
            "texte": texte, "appel": appel,
        })

    def taux(identifiant, question, annee, depart=None, arrivee=None, fin=None):
        arguments = {"debut": annee, "fin": fin or annee}
        if depart:
            arguments.update(depart=depart, arrivee=arrivee)
        ajouter(identifiant, question, [ponctualite(filtrer(lignes, annee, depart, arrivee))],
                {"outil": "taux_ponctualite", "arguments": arguments})

    bordeaux, marseille = "BORDEAUX ST JEAN", "MARSEILLE ST CHARLES"
    taux("t01", "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?", "2025",
         bordeaux, "PARIS MONTPARNASSE")
    taux("t02", "Quelle est la ponctualité de Paris vers Marseille en 2024 ?", "2024",
         "PARIS LYON", marseille)
    taux("t03", "Quelle est la ponctualité de Nantes vers Paris en 2023 ?", "2023",
         "NANTES", "PARIS MONTPARNASSE")
    taux("t04", "Quelle est la ponctualité de tout le réseau TGV en 2025 ?", "2025")
    taux("t05", "Quelle est la ponctualité de Rennes vers Paris en juillet 2025 ?", "2025-07",
         "RENNES", "PARIS MONTPARNASSE")

    # t06 : un nombre de trains, pas un pourcentage.
    _, retards = totaux(filtrer(lignes, "2024", "STRASBOURG", "PARIS EST"))
    ajouter("t06", "Combien de trains sont arrivés en retard de Strasbourg vers Paris en 2024 ?",
            [retards], {"outil": "taux_ponctualite", "arguments": {
                "debut": "2024", "fin": "2024", "depart": "STRASBOURG", "arrivee": "PARIS EST"}})

    # t07 et t08 : l'écart se calcule sur les taux non arrondis.
    ecart = ponctualite(filtrer(lignes, "2025")) - ponctualite(filtrer(lignes, "2024"))
    ajouter("t07", "De combien de points la ponctualité de tout le réseau a-t-elle changé entre 2024 et 2025 ?",
            [abs(ecart)], {"outil": "comparer_periodes", "arguments": {
                "debut_a": "2024", "fin_a": "2024", "debut_b": "2025", "fin_b": "2025"}})
    ecart = (ponctualite(filtrer(lignes, "2024", "PARIS NORD", "LILLE"))
             - ponctualite(filtrer(lignes, "2023", "PARIS NORD", "LILLE")))
    ajouter("t08", "De combien de points la ponctualité de Paris vers Lille a-t-elle changé entre 2023 et 2024 ?",
            [abs(ecart)], {"outil": "comparer_periodes", "arguments": {
                "debut_a": "2023", "fin_a": "2023", "debut_b": "2024", "fin_b": "2024",
                "depart": "PARIS NORD", "arrivee": "LILLE"}})

    (depart, arrivee), part = part_retard_15(lignes, "2025", meilleure=False)
    ajouter("t09", "Quelle liaison a la plus grande part de trains à plus de 15 minutes de retard en 2025 ?",
            [part], {"outil": "classement_liaisons", "arguments": {"debut": "2025", "fin": "2025", "n": 1}},
            texte=arrivee)
    (depart, arrivee), part = part_retard_15(lignes, "2024", meilleure=True)
    ajouter("t10", "Quelle liaison a la plus petite part de trains à plus de 15 minutes de retard en 2024 ?",
            [part], {"outil": "classement_liaisons", "arguments": {
                "debut": "2024", "fin": "2024", "n": 1, "ordre": "meilleures"}},
            texte=arrivee)

    libelle, part = cause_principale(filtrer(lignes, "2025", "LYON PART DIEU", "PARIS LYON"))
    ajouter("t11", "Quelle est la principale cause de retard de Lyon vers Paris en 2025, et quelle est sa part ?",
            [part], {"outil": "causes_retard", "arguments": {
                "debut": "2025", "fin": "2025", "depart": "LYON PART DIEU", "arrivee": "PARIS LYON"}},
            texte=libelle)

    # t12 : question piège. La bonne réponse est de ne donner aucun chiffre.
    premier, dernier = min(l["date"] for l in lignes), max(l["date"] for l in lignes)
    autorises = sorted({int(n) for date in (premier, dernier) for n in date.split("-")})
    taches.append({
        "id": "t12", "question": "Quelle est la ponctualité de Bordeaux vers Paris en 2030 ?",
        "attendu": [], "texte": None, "piege": True, "autorises": autorises,
        "appel": {"outil": "taux_ponctualite", "arguments": {
            "debut": "2030", "fin": "2030", "depart": "Bordeaux", "arrivee": "Paris"}},
    })
    return taches


if __name__ == "__main__":
    taches = construire(lire())
    SORTIE.write_text(json.dumps(taches, ensure_ascii=False, indent=2), encoding="utf-8")
    for tache in taches:
        print(tache["id"], tache["attendu"], tache.get("texte") or "")
