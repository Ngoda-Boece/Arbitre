"""Tests de la boucle agent, avec un modèle simulé : Ollama n'est pas nécessaire."""
import json

from agent import FONCTIONS, OUTILS, REFUS, executer_outil, repondre, repondre_seul


def appel_outil(nom="taux_ponctualite", **arguments):
    arguments = arguments or {"debut": "2024", "fin": "2024", "depart": "Lyon", "arrivee": "Paris"}
    return {"role": "assistant", "content": "",
            "tool_calls": [{"function": {"name": nom, "arguments": arguments}}]}


def texte(contenu):
    return {"role": "assistant", "content": contenu}


def modele_scripte(*reponses):
    """Faux modèle : renvoie les réponses prévues, l'une après l'autre."""
    file = list(reponses)

    def modele(messages, liste_outils, seed):
        modele.vus.append([dict(m) for m in messages])
        return file.pop(0)

    modele.vus = []
    return modele


def test_chaque_outil_declare_existe():
    declares = {outil["function"]["name"] for outil in OUTILS}
    assert declares == set(FONCTIONS)


def test_parcours_nominal(petit):
    # Lyon -> Paris en 2024 : 200 circulés, 20 en retard, soit 90 %.
    modele = modele_scripte(appel_outil(), texte("La ponctualité est de 90 %."))
    trace = repondre("Ponctualité ?", petit, modele=modele)
    assert trace["statut"] == "validee"
    assert trace["reponse"] == "La ponctualité est de 90 %."
    assert trace["appels"][0]["resultat"]["trains_circules"] == 200


def test_resultat_renvoye_au_modele(petit):
    modele = modele_scripte(appel_outil(), texte("90 %."))
    repondre("Ponctualité ?", petit, modele=modele)
    message_outil = modele.vus[1][-1]
    assert message_outil["role"] == "tool"
    assert json.loads(message_outil["content"])["taux_ponctualite_pct"] == 90.0


def test_chiffre_invente_puis_corrige(petit):
    modele = modele_scripte(appel_outil(), texte("Environ 97 %."), texte("Exactement 90 %."))
    trace = repondre("Ponctualité ?", petit, modele=modele)
    assert trace["statut"] == "validee"
    assert trace["reponse"] == "Exactement 90 %."
    assert len(trace["rejets"]) == 1
    assert "97" in modele.vus[2][-1]["content"]  # le modèle a reçu le motif du rejet


def test_deux_inventions_donnent_un_refus(petit):
    modele = modele_scripte(texte("Environ 97 %."), texte("Disons 98 %."))
    trace = repondre("Ponctualité ?", petit, modele=modele)
    assert trace["statut"] == "refusee"
    assert trace["reponse"] == REFUS
    assert "97" not in trace["reponse"]


def test_boucle_infinie_stoppee(petit):
    modele = modele_scripte(*[appel_outil() for _ in range(20)])
    trace = repondre("Ponctualité ?", petit, modele=modele)
    assert trace["statut"] == "refusee"
    assert len(trace["appels"]) == 6


def test_erreur_d_outil_transmise_au_modele(petit):
    modele = modele_scripte(
        appel_outil(debut="2030", fin="2030"),
        texte("Je n'ai pas de données pour cette période."),
    )
    trace = repondre("Et en 2030 ?", petit, modele=modele)
    assert trace["statut"] == "validee"
    assert "erreur" in trace["appels"][0]["resultat"]


def test_outil_inconnu_refuse_sans_rien_executer(petit):
    assert "Outil inconnu" in executer_outil("os.system", {"commande": "rm"}, petit)["erreur"]


def test_parametre_inconnu_ne_plante_pas(petit):
    assert "Paramètres invalides" in executer_outil("taux_ponctualite", {"debut": "2024", "x": 1}, petit)["erreur"]


def test_arguments_en_texte_json(petit):
    arguments = json.dumps({"debut": "2024", "fin": "2024"})
    assert executer_outil("taux_ponctualite", arguments, petit)["trains_circules"] == 350


def test_arguments_illisibles(petit):
    assert "illisibles" in executer_outil("taux_ponctualite", "{pas du json", petit)["erreur"]


def test_chaine_vide_traitee_comme_absente(petit):
    resultat = executer_outil("taux_ponctualite", {"debut": "2024", "fin": "2024", "depart": ""}, petit)
    assert resultat["liaison"] == "3 liaisons"


def test_modele_seul_sans_outils():
    modele = modele_scripte(texte("Environ 95 %."))
    trace = repondre_seul("Ponctualité ?", modele=modele)
    assert trace["reponse"] == "Environ 95 %."
    assert trace["statut"] == "seul"
