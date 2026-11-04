"""La boucle agent (brique 1) : le modèle, ses outils et le contrôle de l'Arbitre.

Un agent, c'est un modèle qui utilise des outils en boucle :
  1. on envoie la conversation au modèle ;
  2. s'il demande un outil, le code l'exécute et ajoute le résultat à la conversation ;
  3. on recommence jusqu'à ce qu'il écrive sa réponse finale ;
  4. l'Arbitre contrôle cette réponse avant qu'elle soit montrée.

Usage :
  python src/agent.py "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"
  python src/agent.py --seul "La même question"     (le modèle sans outils ni Arbitre)
"""
import argparse
import json
import time
from datetime import datetime

import requests

import outils
from arbitre import verifier
from config import DOSSIER_TRACES, reglages_llm

MAX_TOURS = 6        # garde-fou : le modèle ne peut pas boucler indéfiniment
MAX_REPRISES = 1     # une seule seconde chance après un rejet de l'Arbitre

REFUS = "Je préfère ne pas répondre : je n'ai pas pu appuyer ces chiffres sur un calcul vérifié."

SYSTEME = """Tu réponds en français sur la ponctualité des TGV en France.
Règles :
- Tu ne connais aucun chiffre par cœur. Appelle toujours un outil avant de citer un nombre.
- Si la question cite des villes, remplis toujours depart et arrivee.
- Pour une année, utilise debut et fin au format AAAA.
- Recopie les nombres exactement comme l'outil les donne.
- Si l'outil renvoie une erreur, corrige ton appel ou dis que tu ne peux pas répondre.
- Réponds en deux phrases au maximum."""

SYSTEME_SEUL = "Tu réponds en français sur la ponctualité des TGV en France, en deux phrases au maximum."

# Paramètres communs aux outils. Le texte de « description » est lu par le modèle :
# c'est ainsi qu'il sait quoi remplir.
_DEPART = {"type": "string", "description": "Ville de départ, à remplir dès que la question en cite une"}
_ARRIVEE = {"type": "string", "description": "Ville d'arrivée, à remplir dès que la question en cite une"}
_DATE = {"type": "string", "description": "AAAA ou AAAA-MM"}


def _outil(nom, description, proprietes, obligatoires):
    """Écrit la fiche d'un outil au format attendu par Ollama."""
    return {
        "type": "function",
        "function": {
            "name": nom,
            "description": description,
            "parameters": {"type": "object", "properties": proprietes, "required": obligatoires},
        },
    }


OUTILS = [
    _outil(
        "taux_ponctualite",
        "Taux de ponctualité et nombre de trains en retard sur une période, pour une liaison ou tout le réseau.",
        {"debut": _DATE, "fin": _DATE, "depart": _DEPART, "arrivee": _ARRIVEE},
        ["debut", "fin"],
    ),
    _outil(
        "classement_liaisons",
        "Classe les liaisons sur la part de trains à plus de 15 minutes de retard.",
        {
            "debut": _DATE,
            "fin": _DATE,
            "n": {"type": "integer", "description": "Nombre de liaisons à renvoyer"},
            "ordre": {"type": "string", "enum": ["pires", "meilleures"]},
        },
        ["debut", "fin"],
    ),
    _outil(
        "causes_retard",
        "Répartition des causes de retard sur une période.",
        {"debut": _DATE, "fin": _DATE, "depart": _DEPART, "arrivee": _ARRIVEE},
        ["debut", "fin"],
    ),
    _outil(
        "comparer_periodes",
        "Compare la ponctualité de deux périodes A et B. L'écart vaut B moins A.",
        {
            "debut_a": _DATE, "fin_a": _DATE, "debut_b": _DATE, "fin_b": _DATE,
            "depart": _DEPART, "arrivee": _ARRIVEE,
        },
        ["debut_a", "fin_a", "debut_b", "fin_b"],
    ),
]

# Liste blanche : seul un nom présent ici peut être exécuté.
FONCTIONS = {
    "taux_ponctualite": outils.taux_ponctualite,
    "classement_liaisons": outils.classement_liaisons,
    "causes_retard": outils.causes_retard,
    "comparer_periodes": outils.comparer_periodes,
}


def appeler_ollama(messages, liste_outils, seed):
    """Envoie la conversation à Ollama et renvoie le message du modèle.

    Le modèle est passé en paramètre de repondre() : les tests peuvent ainsi le
    remplacer par une fausse fonction, sans avoir besoin d'Ollama.
    """
    reglages = reglages_llm()
    # On retire /v1 : l'API native d'Ollama est la seule à accepter think et options.
    adresse = reglages["base_url"].removesuffix("/v1") + "/api/chat"
    corps = {
        "model": reglages["model"],
        "messages": messages,
        "stream": False,
        "think": False,  # sans cela, le modèle réfléchit très longtemps sur ce PC
        "options": {"num_ctx": 8192, "seed": seed, "temperature": 0.2, "num_predict": 300},
    }
    if liste_outils:
        corps["tools"] = liste_outils
    reponse = requests.post(adresse, json=corps, timeout=600)
    reponse.raise_for_status()
    return reponse.json()["message"]


def executer_outil(nom, arguments, df):
    """Exécute un appel demandé par le modèle. Renvoie toujours un dictionnaire.

    Une erreur devient un résultat lisible et non un plantage : le modèle peut se corriger.
    """
    if nom not in FONCTIONS:
        return {"erreur": f"Outil inconnu : {nom}. Outils disponibles : {', '.join(FONCTIONS)}."}
    # Certains modèles renvoient les arguments sous forme de texte JSON.
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return {"erreur": "Arguments illisibles : envoie un objet JSON."}
    # Le modèle envoie parfois une chaîne vide au lieu de ne rien envoyer.
    arguments = {cle: valeur for cle, valeur in (arguments or {}).items() if valeur not in ("", None)}
    try:
        return FONCTIONS[nom](df, **arguments)
    except outils.ErreurOutil as erreur:
        return {"erreur": str(erreur)}
    except TypeError as erreur:  # paramètre manquant ou inconnu
        return {"erreur": f"Paramètres invalides pour {nom} : {erreur}."}


def repondre(question, df, modele=appeler_ollama, seed=1):
    """Fait tourner la boucle et renvoie la trace complète de l'exécution.

    Le champ "statut" vaut "validee" (l'Arbitre accepte) ou "refusee" (réponse bloquée).
    """
    debut = time.perf_counter()
    messages = [{"role": "system", "content": SYSTEME}, {"role": "user", "content": question}]
    trace = {"question": question, "seed": seed, "appels": [], "rejets": []}
    resultats = []  # tout ce que les outils ont produit : ce sont les sources de l'Arbitre
    reprises = 0

    for _ in range(MAX_TOURS):
        message = modele(messages, OUTILS, seed)
        messages.append(message)
        appels = message.get("tool_calls") or []

        # Cas 1 : le modèle demande des outils. On les exécute et on repart pour un tour.
        if appels:
            for appel in appels:
                nom = appel["function"]["name"]
                arguments = appel["function"].get("arguments", {})
                resultat = executer_outil(nom, arguments, df)
                resultats.append(resultat)
                trace["appels"].append({"outil": nom, "arguments": arguments, "resultat": resultat})
                messages.append({
                    "role": "tool",
                    "tool_name": nom,
                    "content": json.dumps(resultat, ensure_ascii=False),
                })
            continue

        # Cas 2 : le modèle a écrit sa réponse. L'Arbitre décide si elle sort.
        texte = message.get("content", "")
        verdict = verifier(texte, resultats, question)
        if verdict["valide"]:
            trace.update(statut="validee", reponse=texte)
            break

        trace["rejets"].append({"reponse": texte, "motif": verdict["motif"]})
        if reprises >= MAX_REPRISES:
            trace.update(statut="refusee", reponse=REFUS)
            break
        reprises += 1
        messages.append({
            "role": "user",
            "content": f"Réponse rejetée, {verdict['motif']}. Appelle un outil, puis réécris "
                       "ta réponse en citant uniquement les nombres renvoyés par l'outil.",
        })
    else:
        # Le « else » d'un for s'exécute si la boucle finit sans break : tours épuisés.
        trace.update(statut="refusee", reponse=REFUS)

    trace["secondes"] = round(time.perf_counter() - debut, 1)
    return trace


def repondre_seul(question, modele=appeler_ollama, seed=1):
    """Le modèle sans outils ni Arbitre : la référence de la comparaison (brique 9)."""
    debut = time.perf_counter()
    messages = [{"role": "system", "content": SYSTEME_SEUL}, {"role": "user", "content": question}]
    message = modele(messages, None, seed)
    return {
        "question": question,
        "seed": seed,
        "statut": "seul",
        "reponse": message.get("content", ""),
        "secondes": round(time.perf_counter() - debut, 1),
    }


def ecrire_trace(trace):
    """Enregistre une exécution dans traces/, en JSON lisible."""
    DOSSIER_TRACES.mkdir(exist_ok=True)
    nom = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json"
    chemin = DOSSIER_TRACES / nom
    chemin.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return chemin


def main():
    analyseur = argparse.ArgumentParser(description="Pose une question à l'Arbitre des trains.")
    analyseur.add_argument("question")
    analyseur.add_argument("--seul", action="store_true", help="modèle seul, sans outils ni Arbitre")
    analyseur.add_argument("--seed", type=int, default=1)
    arguments = analyseur.parse_args()

    if arguments.seul:
        trace = repondre_seul(arguments.question, seed=arguments.seed)
    else:
        trace = repondre(arguments.question, outils.charger(), seed=arguments.seed)
    print(trace["reponse"])
    print(f"\n[{trace['statut']}, {trace['secondes']} s, trace : {ecrire_trace(trace)}]")


if __name__ == "__main__":
    main()
