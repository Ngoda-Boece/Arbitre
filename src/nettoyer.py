"""Nettoie le fichier brut SNCF et écrit le journal de chaque décision (brique 6).

Usage : python src/nettoyer.py
"""
import pandas as pd

from config import FICHIER_BRUT, FICHIER_PROPRE, JOURNAL_NETTOYAGE

COLONNES = {
    "Date": "date",
    "Service": "service",
    "Gare de départ": "gare_depart",
    "Gare d'arrivée": "gare_arrivee",
    "Durée moyenne du trajet": "duree_min",
    "Nombre de circulations prévues": "prevus",
    "Nombre de trains annulés": "annules",
    "Nombre de trains en retard à l'arrivée": "retards_arrivee",
    "Nombre trains en retard > 15min": "retards_15",
    "Prct retard pour causes externes": "cause_externe",
    "Prct retard pour cause infrastructure": "cause_infrastructure",
    "Prct retard pour cause gestion trafic": "cause_gestion_trafic",
    "Prct retard pour cause matériel roulant": "cause_materiel_roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": "cause_gestion_gare",
    "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)": "cause_voyageurs",
}
CAUSES = [nom for nom in COLONNES.values() if nom.startswith("cause_")]
COLONNE_MOYENNE_15 = "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)"
COLONNE_RETARDS_30 = "Nombre trains en retard > 30min"


def seuil_retard(duree_min):
    """Règle absente des colonnes, tirée de la description du jeu de données SNCF :
    à l'heure sous 5 min (trajet < 1h30), 10 min (1h30 à 3h), 15 min (> 3h)."""
    if pd.isna(duree_min) or duree_min <= 0:
        return None
    if duree_min < 90:
        return 5
    if duree_min <= 180:
        return 10
    return 15


def verifier_seuils(df):
    """Confronte la règle au fichier : plus le seuil est haut, plus les trains
    « en retard » doivent être aussi des trains à plus de 15 min."""
    lignes = []
    for seuil, groupe in df[df["retards_arrivee"] > 0].groupby("seuil_min"):
        part = groupe["retards_15"].sum() / groupe["retards_arrivee"].sum()
        lignes.append(f"| {int(seuil)} min | {len(groupe)} | {part:.1%} |")
    return lignes


def nettoyer(brut):
    """Renvoie (tableau propre, journal). Le tableau brut n'est pas modifié."""
    journal = [f"- Lignes lues : **{len(brut)}**, {brut.shape[1]} colonnes."]
    df = brut[list(COLONNES)].rename(columns=COLONNES).copy()

    # Anomalies constatées dans des colonnes qu'aucun outil n'utilise.
    if COLONNE_MOYENNE_15 in brut:
        impossible = (brut[COLONNE_MOYENNE_15] < 15) & (brut["Nombre trains en retard > 15min"] > 0)
        journal.append(
            f"- Colonne « {COLONNE_MOYENNE_15} » écartée : {impossible.sum()} lignes ont une "
            "moyenne sous 15 min, ce qui est impossible par définition."
        )
    if COLONNE_RETARDS_30 in brut:
        journal.append(
            f"- Colonne « {COLONNE_RETARDS_30} » écartée : "
            f"{(brut[COLONNE_RETARDS_30] < 0).sum()} valeurs négatives."
        )
    journal.append("- Colonnes de commentaires écartées : texte libre non utilisé par les calculs.")

    for colonne in ("service", "gare_depart", "gare_arrivee"):
        df[colonne] = df[colonne].str.strip()

    # Décision 1 : sans train circulé, un taux n'a pas de sens.
    df["circules"] = df["prevus"] - df["annules"]
    sans_train = df["circules"] <= 0
    journal.append(
        f"- Décision 1 : {sans_train.sum()} lignes retirées car circulés = prévus - annulés est "
        "nul ou négatif."
    )
    df = df[~sans_train]

    # Décision 2 : compteurs contradictoires, impossible de savoir lequel est faux.
    incoherent = (df["retards_arrivee"] > df["circules"]) | (df["retards_arrivee"] < df["retards_15"])
    journal.append(
        f"- Décision 2 : {incoherent.sum()} lignes retirées car les compteurs se contredisent "
        "(plus de retards que de trains, ou moins de retards que de retards > 15 min). "
        f"Trains circulés perdus : {df.loc[incoherent, 'circules'].sum()} sur {df['circules'].sum()}."
    )
    df = df[~incoherent].copy()

    # Décision 3 : une durée nulle n'est pas une durée.
    duree_nulle = df["duree_min"] <= 0
    journal.append(
        f"- Décision 3 : {duree_nulle.sum()} durées nulles vidées (ligne gardée, seuil inconnu)."
    )
    df["duree_min"] = df["duree_min"].astype("float64").mask(duree_nulle)

    # Décision 4 : causes inutilisables si leur somme n'est pas proche de 100 %.
    somme = df[CAUSES].sum(axis=1)
    causes_fausses = (df["retards_arrivee"] > 0) & ((somme < 99) | (somme > 101))
    sans_retard = df["retards_arrivee"] == 0
    journal.append(
        f"- Décision 4 : causes vidées sur {causes_fausses.sum()} lignes dont la somme sort de "
        f"99-101 %, et sur {sans_retard.sum()} lignes sans aucun retard."
    )
    df[CAUSES] = df[CAUSES].astype("float64").mask(causes_fausses | sans_retard)

    # Décision 5 : une année entière sans aucun retard n'est pas crédible.
    # Exemple qui a motivé la règle : Paris -> Italie affiche 0 retard pendant 14 mois de suite,
    # avec des trains en retard au départ et une durée figée. La cause n'est pas dans le fichier.
    annee = df["date"].str[:4]
    cumul = df.groupby(["gare_depart", "gare_arrivee", annee])[
        ["circules", "retards_arrivee"]
    ].transform("sum")
    annee_suspecte = (cumul["retards_arrivee"] == 0) & (cumul["circules"] >= 100)
    journal.append(
        f"- Décision 5 : {annee_suspecte.sum()} lignes retirées, car leur liaison n'a aucun retard "
        "sur une année civile d'au moins 100 trains. Ces valeurs ressemblent à des trous de "
        f"mesure ; trains circulés perdus : {df.loc[annee_suspecte, 'circules'].sum()}."
    )
    df = df[~annee_suspecte].copy()

    # Règle du document, appliquée puis vérifiée sur les chiffres.
    df["seuil_min"] = df["duree_min"].map(seuil_retard).astype("float64")
    journal.append(
        "- Règle hors colonnes : seuil de retard selon la durée (5, 10 ou 15 min). Source : "
        "description du jeu de données sur ressources.data.sncf.com."
    )
    journal.append("- Vérification de la règle sur le fichier :\n")
    journal.append("| Seuil | Lignes | Part des retards qui dépassent 15 min |")
    journal.append("|---|---|---|")
    journal.extend(verifier_seuils(df))
    journal.append("")

    journal.append(
        "- Gardé tel quel : PARIS VAUGIRARD reste distincte de PARIS MONTPARNASSE (aucune source "
        "pour les fusionner) ; ITALIE est une destination, pas une gare ; les mois de 2020 restent."
    )
    journal.append(f"- Lignes gardées : **{len(df)}** sur {len(brut)}.")
    return df.reset_index(drop=True), journal


def main():
    brut = pd.read_csv(FICHIER_BRUT, sep=";", encoding="utf-8-sig")
    propre, journal = nettoyer(brut)

    FICHIER_PROPRE.parent.mkdir(parents=True, exist_ok=True)
    propre.to_csv(FICHIER_PROPRE, index=False, encoding="utf-8")
    JOURNAL_NETTOYAGE.write_text(
        "# Journal de nettoyage\n\n" + "\n".join(journal) + "\n", encoding="utf-8"
    )
    print("\n".join(journal))


if __name__ == "__main__":
    main()
