"""Les quatre fonctions de calcul que le modèle a le droit d'appeler (briques 1 et 8).

Pourquoi des fonctions fixes plutôt que du Python libre ?
Le modèle choisit seulement un outil et ses paramètres. Il ne peut donc ni exécuter
n'importe quoi sur la machine, ni écrire un calcul faux : le calcul est toujours le mien.

Chaque outil renvoie un dictionnaire de résultats. Si l'appel est invalide, il lève
ErreurOutil : la boucle agent transmet ce message au modèle, qui peut se corriger.
"""
import re
import unicodedata

import pandas as pd

from config import FICHIER_PROPRE
from stats import ecart_newcombe, intervalle_wilson

# Rappel renvoyé avec les taux, pour ne pas faire dire aux chiffres plus qu'ils ne disent.
# Ce texte ne contient volontairement aucun nombre.
LIMITES = (
    "Le fichier compte tous les trains, ce n'est pas un sondage : l'intervalle traite chaque train "
    "comme un tirage indépendant et il est trop étroit, car les retards d'une même journée sont "
    "liés. Ces données ne prouvent pas pourquoi une liaison est en retard."
)

# Nom de la colonne -> nom lisible donné au modèle.
CAUSES = {
    "cause_externe": "causes externes",
    "cause_infrastructure": "infrastructure",
    "cause_gestion_trafic": "gestion du trafic",
    "cause_materiel_roulant": "matériel roulant",
    "cause_gestion_gare": "gestion en gare",
    "cause_voyageurs": "prise en charge des voyageurs",
}


class ErreurOutil(ValueError):
    """Appel invalide. Le message est écrit pour être lu par le modèle."""


def charger(chemin=FICHIER_PROPRE):
    """Lit le fichier nettoyé. `date` reste du texte pour garder « 2025-01 » tel quel."""
    if not chemin.exists():
        raise FileNotFoundError(f"{chemin} absent : lancez d'abord python src/nettoyer.py")
    return pd.read_csv(chemin, dtype={"date": str})


def _normaliser(nom):
    """Met un nom de gare sous une forme unique pour comparer sans se tromper.

    « Saint-Étienne » et « ST ETIENNE » donnent tous les deux « ST ETIENNE ».
    """
    # NFKD sépare « É » en « E » + accent ; encode("ascii", "ignore") jette l'accent.
    sans_accent = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    # Tout ce qui n'est ni lettre ni chiffre devient un séparateur de mots.
    mots = re.sub(r"[^A-Z0-9]+", " ", sans_accent.upper()).split()
    return " ".join("ST" if mot == "SAINT" else mot for mot in mots)


def _gares_possibles(df, nom):
    """Trouve les gares qui correspondent à un nom, du plus précis au plus large.

    On s'arrête au premier essai qui trouve quelque chose. Ainsi « Lyon » s'arrête
    au « début du nom » et désigne LYON PART DIEU, pas PARIS LYON.
    """
    cible = _normaliser(nom)
    if not cible:
        raise ErreurOutil("Nom de gare vide.")
    gares = pd.concat([df["gare_depart"], df["gare_arrivee"]]).unique()
    noms = {gare: _normaliser(gare) for gare in gares}

    for essai in (
        lambda n: n == cible,                  # 1. nom exact
        lambda n: n.startswith(cible + " "),   # 2. début du nom
        lambda n: cible in n,                  # 3. morceau du nom
    ):
        trouvees = sorted(gare for gare, n in noms.items() if essai(n))
        if trouvees:
            return trouvees
    raise ErreurOutil(f"Gare inconnue : {nom!r}. Gares disponibles : {', '.join(sorted(gares))}.")


def _periode(df, debut, fin):
    """Garde les lignes de la période, bornes incluses. Renvoie (lignes, début, fin).

    Accepte AAAA, AAAA-MM ou AAAA-MM-JJ : le modèle envoie souvent des dates complètes,
    et le fichier étant mensuel, le jour est simplement ignoré.
    """
    bornes = []
    for valeur in (debut, fin):
        if not re.fullmatch(r"\d{4}(-(0[1-9]|1[0-2])(-\d{2})?)?", str(valeur)):
            raise ErreurOutil(f"Période invalide : {valeur!r}. Format attendu : AAAA ou AAAA-MM.")
        bornes.append(str(valeur)[:7])
    debut, fin = bornes

    # Une année seule veut dire « de janvier à décembre ».
    if len(debut) == 4:
        debut += "-01"
    if len(fin) == 4:
        fin += "-12"
    if debut > fin:
        raise ErreurOutil(f"Période inversée : {debut} est après {fin}.")

    # Comparer du texte marche ici car AAAA-MM se trie dans l'ordre chronologique.
    tranche = df[df["date"].between(debut, fin)]
    if tranche.empty:
        raise ErreurOutil(
            f"Aucune donnée entre {debut} et {fin}. "
            f"Données disponibles de {df['date'].min()} à {df['date'].max()}."
        )
    return tranche, debut, fin


def _filtrer_liaison(df, depart, arrivee):
    """Garde une liaison. None veut dire « toutes » : sans gare, c'est tout le réseau."""
    tranche = df
    if depart is not None:
        tranche = tranche[tranche["gare_depart"].isin(_gares_possibles(df, depart))]
    if arrivee is not None:
        tranche = tranche[tranche["gare_arrivee"].isin(_gares_possibles(df, arrivee))]
    if tranche.empty:
        raise ErreurOutil(f"Aucune liaison trouvée pour {depart!r} vers {arrivee!r} sur cette période.")

    liaisons = sorted(set(zip(tranche["gare_depart"], tranche["gare_arrivee"])))
    # Deux gares données mais plusieurs liaisons trouvées : plutôt que de deviner, on demande.
    if depart is not None and arrivee is not None and len(liaisons) > 1:
        choix = ", ".join(f"{a} -> {b}" for a, b in liaisons)
        raise ErreurOutil(f"Plusieurs liaisons correspondent, précisez : {choix}.")
    return tranche, liaisons


def _taux(tranche):
    """Calcule le taux à partir des totaux de trains.

    On additionne les trains avant de diviser. Faire la moyenne des taux mensuels serait
    faux : un mois de 100 trains compterait autant qu'un mois de 1 000.
    Les trains annulés ne comptent pas : ils ne sont pas arrivés, ni à l'heure ni en retard.
    """
    circules = int(tranche["circules"].sum())
    en_retard = int(tranche["retards_arrivee"].sum())
    bas, haut = intervalle_wilson(circules - en_retard, circules)
    return {
        "taux_ponctualite_pct": round(100 * (circules - en_retard) / circules, 1),
        "taux_retard_pct": round(100 * en_retard / circules, 1),
        "ic95_bas_pct": round(100 * bas, 1),
        "ic95_haut_pct": round(100 * haut, 1),
        "niveau_confiance_pct": 95,
        "trains_circules": circules,
        "trains_en_retard": en_retard,
    }


def _nom_liaisons(liaisons):
    """Texte lisible : la liaison s'il n'y en a qu'une, sinon leur nombre."""
    if len(liaisons) == 1:
        return f"{liaisons[0][0]} -> {liaisons[0][1]}"
    return f"{len(liaisons)} liaisons"


def taux_ponctualite(df, debut, fin, depart=None, arrivee=None):
    """OUTIL 1 : ponctualité à l'arrivée sur une période, avec son intervalle à 95 %."""
    tranche, debut, fin = _periode(df, debut, fin)
    tranche, liaisons = _filtrer_liaison(tranche, depart, arrivee)
    return {
        "liaison": _nom_liaisons(liaisons),
        "periode": f"{debut} à {fin}",
        "mois_couverts": int(tranche["date"].nunique()),
        **_taux(tranche),  # ** recopie ici toutes les clés du dictionnaire de _taux
        "seuils_retard_min": sorted(int(s) for s in tranche["seuil_min"].dropna().unique()),
        "limites": LIMITES,
    }


def classement_liaisons(df, debut, fin, n=5, ordre="pires", trains_min=100):
    """OUTIL 2 : classe les liaisons sur la part de trains à plus de 15 min de retard.

    Ce critère est le même pour toutes, contrairement au taux officiel dont le seuil
    change avec la durée du trajet : c'est lui qui rend la comparaison équitable.
    trains_min écarte les petites liaisons, où quelques trains suffisent à tout changer.
    """
    if ordre not in ("pires", "meilleures"):
        raise ErreurOutil("ordre doit valoir 'pires' ou 'meilleures'.")
    if not isinstance(n, int) or n < 1:
        raise ErreurOutil("n doit être un entier positif.")
    tranche, debut, fin = _periode(df, debut, fin)

    # Une ligne par liaison, avec les totaux de la période.
    groupes = tranche.groupby(["gare_depart", "gare_arrivee"], as_index=False)[
        ["circules", "retards_15"]
    ].sum()
    groupes = groupes[groupes["circules"] >= trains_min]
    if groupes.empty:
        raise ErreurOutil(f"Aucune liaison n'a au moins {trains_min} trains sur cette période.")

    groupes["part"] = groupes["retards_15"] / groupes["circules"]
    # Les noms de gares servent à départager les ex æquo : le résultat ne varie jamais.
    groupes = groupes.sort_values(
        ["part", "gare_depart", "gare_arrivee"], ascending=[ordre == "meilleures", True, True]
    )
    return {
        "periode": f"{debut} à {fin}",
        "critere": "part des trains circulés arrivés avec plus de 15 min de retard",
        "liaisons_comparees": len(groupes),
        "classement": [
            {
                "rang": rang,
                "liaison": f"{ligne.gare_depart} -> {ligne.gare_arrivee}",
                "retard_plus_15_min_pct": round(100 * ligne.part, 1),
                "trains_circules": int(ligne.circules),
            }
            for rang, ligne in enumerate(groupes.head(n).itertuples(), start=1)
        ],
    }


def causes_retard(df, debut, fin, depart=None, arrivee=None):
    """OUTIL 3 : répartition des causes de retard.

    Chaque mois pèse selon son nombre de trains en retard : un mois avec 200 retards
    doit compter plus qu'un mois avec 2 retards.
    """
    tranche, debut, fin = _periode(df, debut, fin)
    tranche, liaisons = _filtrer_liaison(tranche, depart, arrivee)
    valides = tranche.dropna(subset=list(CAUSES))  # lignes dont les causes sont exploitables
    if valides.empty:
        raise ErreurOutil("Aucune ligne avec des causes exploitables sur cette période.")

    poids = valides["retards_arrivee"]
    parts = {
        libelle: round(float((valides[colonne] * poids).sum() / poids.sum()), 1)
        for colonne, libelle in CAUSES.items()
    }
    return {
        "liaison": _nom_liaisons(liaisons),
        "periode": f"{debut} à {fin}",
        "trains_en_retard_pris_en_compte": int(poids.sum()),
        # Trié de la cause la plus fréquente à la moins fréquente.
        "causes_pct": dict(sorted(parts.items(), key=lambda paire: -paire[1])),
    }


def comparer_periodes(df, debut_a, fin_a, debut_b, fin_b, depart=None, arrivee=None):
    """OUTIL 4 : compare deux périodes. L'écart vaut B moins A, donc négatif si B est pire."""
    tranche_a, debut_a, fin_a = _periode(df, debut_a, fin_a)
    tranche_b, debut_b, fin_b = _periode(df, debut_b, fin_b)
    tranche_a, liaisons_a = _filtrer_liaison(tranche_a, depart, arrivee)
    tranche_b, liaisons_b = _filtrer_liaison(tranche_b, depart, arrivee)

    taux_a, taux_b = _taux(tranche_a), _taux(tranche_b)
    ecart, bas, haut = ecart_newcombe(
        taux_a["trains_circules"] - taux_a["trains_en_retard"],  # trains à l'heure en A
        taux_a["trains_circules"],
        taux_b["trains_circules"] - taux_b["trains_en_retard"],  # trains à l'heure en B
        taux_b["trains_circules"],
    )
    return {
        "liaison_a": _nom_liaisons(liaisons_a),
        "liaison_b": _nom_liaisons(liaisons_b),
        "periode_a": f"{debut_a} à {fin_a}",
        "periode_b": f"{debut_b} à {fin_b}",
        "a": taux_a,
        "b": taux_b,
        "ecart_points": round(100 * ecart, 1),
        "ecart_ic95_bas": round(100 * bas, 1),
        "ecart_ic95_haut": round(100 * haut, 1),
        # L'écart est net si tout l'intervalle est du même côté de zéro.
        "ecart_net": bool(bas > 0 or haut < 0),
        "limites": LIMITES,
    }
