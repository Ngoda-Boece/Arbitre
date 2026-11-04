"""L'Arbitre : la règle du projet, imposée par le code (brique 3).

Règle : la réponse finale ne contient aucun nombre qui n'a pas été produit par un outil.

Pourquoi du code et pas une consigne dans le prompt ? Une consigne, le modèle peut
l'ignorer. Ce fichier, lui, s'exécute à chaque réponse.

Limite à connaître : l'Arbitre vérifie d'où vient un nombre, pas son sens. Si le modèle
recopie un bon nombre au mauvais endroit, ou appelle l'outil sur la mauvaise liaison,
l'Arbitre laisse passer. La brique 9 sert justement à mesurer ce qui reste.
"""
import re

# Espaces qui peuvent séparer les milliers : normale, insécable, fine insécable.
ESPACES = "   "

# Reconnaît un nombre : soit « 12 369 » (avec espaces), soit « 83,6 », « 83.6 » ou « 2027 ».
# (?<![\w.,]) empêche de démarrer au milieu d'un mot ou d'un nombre.
MOTIF_NOMBRE = re.compile(
    rf"(?<![\w.,])(?:\d{{1,3}}(?:[{ESPACES}]\d{{3}})+(?!\d)(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
)

# Numéro de liste en début de ligne (« 1. Paris ») : c'est de la mise en forme, pas un chiffre.
MOTIF_LISTE = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)

# Nombre écrit en lettres suivi d'une unité (« vingt pour cent ») : autre façon d'inventer.
# L'unité est exigée, sinon « les deux périodes » serait refusé à tort.
MOTIF_LETTRES = re.compile(
    r"\b(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|"
    r"seize|vingt|trente|quarante|cinquante|soixante|septante|huitante|nonante|cent|mille)\b"
    r"[\s-]*(?:pour[\s-]?cent|%|points?|trains?|minutes?|min\b)",
    re.IGNORECASE,
)


def extraire_nombres(texte):
    """Renvoie la liste des nombres d'un texte, sous forme de textes normalisés.

    On garde du texte (« 83.6 ») et non un float, pour savoir combien de décimales
    ont été écrites : c'est utile pour vérifier les arrondis.
    Le signe est ignoré : « baisse de 1,4 point » doit correspondre à l'écart -1.4.
    """
    sans_liste = MOTIF_LISTE.sub(" ", texte)
    nombres = []
    for brut in MOTIF_NOMBRE.findall(sans_liste):
        propre = brut.translate({ord(c): None for c in ESPACES}).replace(",", ".")
        nombres.append(propre)
    return nombres


def collecter_sources(valeur):
    """Parcourt un résultat d'outil, même imbriqué, et ramasse tous ses nombres.

    La fonction s'appelle elle-même pour descendre dans les listes et dictionnaires.
    Les textes sont lus aussi, car ils contiennent par exemple « 2025-01 à 2025-12 ».
    """
    if isinstance(valeur, bool) or valeur is None:
        return []  # True n'est pas un chiffre, même si Python le voit comme 1
    if isinstance(valeur, (int, float)):
        return [abs(float(valeur))]
    if isinstance(valeur, str):
        return [float(n) for n in extraire_nombres(valeur.replace("-", " "))]
    if isinstance(valeur, dict):
        valeur = list(valeur.values())
    if isinstance(valeur, (list, tuple)):
        return [n for element in valeur for n in collecter_sources(element)]
    return []


def nombre_justifie(texte_nombre, sources):
    """Le nombre écrit est-il une source, éventuellement arrondie ou écrite en proportion ?

    Si le modèle écrit 84 et que la source est 83.6 : arrondi à 0 décimale, c'est accepté.
    Si le modèle écrit 83 : aucun arrondi de 83.6 ne donne 83, c'est refusé.
    """
    valeur = float(texte_nombre)
    decimales = len(texte_nombre.split(".")[1]) if "." in texte_nombre else 0
    for source in sources:
        if abs(round(source, decimales) - valeur) < 1e-9:
            return True
        # 0,836 écrit à la place de 83,6 % : même information, autre écriture.
        if abs(round(source / 100, decimales) - valeur) < 1e-9 and valeur < 1:
            return True
    return False


def verifier(reponse, resultats_outils, question=""):
    """Juge une réponse. Renvoie {"valide": bool, "sans_source": [...], "motif": str}.

    Les nombres de la question sont autorisés : répéter « en 2025 » n'invente rien.
    """
    if not reponse or not reponse.strip():
        return {"valide": False, "sans_source": [], "motif": "réponse vide"}

    lettres = [m.group(0) for m in MOTIF_LETTRES.finditer(reponse)]
    sources = collecter_sources(resultats_outils)
    sources += [float(n) for n in extraire_nombres(question)]

    sans_source = [n for n in extraire_nombres(reponse) if not nombre_justifie(n, sources)]
    sans_source += lettres

    if sans_source:
        return {
            "valide": False,
            "sans_source": sans_source,
            "motif": "nombres sans source : " + ", ".join(sans_source),
        }
    return {"valide": True, "sans_source": [], "motif": "tous les nombres ont une source"}
