import pandas as pd

from nettoyer import CAUSES, COLONNES, nettoyer, seuil_retard


def brut(**valeurs):
    ligne = {nom: 0 for nom in COLONNES}
    ligne.update({"Date": "2024-01", "Service": "National", "Gare de départ": " LILLE ",
                  "Gare d'arrivée": "PARIS NORD", "Durée moyenne du trajet": 60,
                  "Nombre de circulations prévues": 100,
                  "Nombre de trains en retard à l'arrivée": 5,
                  "Prct retard pour causes externes": 100})
    ligne.update(valeurs)
    return pd.DataFrame([ligne])


def test_seuils_aux_bornes():
    assert seuil_retard(89) == 5
    assert seuil_retard(90) == 10
    assert seuil_retard(180) == 10
    assert seuil_retard(181) == 15
    assert seuil_retard(0) is None


def test_ligne_saine_gardee_et_espaces_retires():
    propre, _ = nettoyer(brut())
    assert len(propre) == 1
    assert propre.loc[0, "gare_depart"] == "LILLE"
    assert propre.loc[0, "circules"] == 100
    assert propre.loc[0, "seuil_min"] == 5


def test_aucun_train_circule_retire():
    assert nettoyer(brut(**{"Nombre de trains annulés": 100}))[0].empty
    assert nettoyer(brut(**{"Nombre de circulations prévues": 0}))[0].empty


def test_plus_de_retards_que_de_trains_retire():
    ligne = brut(**{"Nombre de trains en retard à l'arrivée": 101})
    assert nettoyer(ligne)[0].empty


def test_moins_de_retards_que_de_retards_15_retire():
    ligne = brut(**{"Nombre de trains en retard à l'arrivée": 3, "Nombre trains en retard > 15min": 4})
    assert nettoyer(ligne)[0].empty


def test_duree_nulle_videe_mais_ligne_gardee():
    propre, _ = nettoyer(brut(**{"Durée moyenne du trajet": 0}))
    assert len(propre) == 1
    assert pd.isna(propre.loc[0, "duree_min"]) and pd.isna(propre.loc[0, "seuil_min"])


def test_causes_fausses_videes():
    ligne = brut(**{"Nombre de trains en retard à l'arrivée": 5,
                    "Prct retard pour causes externes": 50})
    assert nettoyer(ligne)[0][CAUSES].isna().all(axis=None)


def test_causes_valides_gardees():
    ligne = brut(**{"Nombre de trains en retard à l'arrivée": 5})
    assert nettoyer(ligne)[0].loc[0, "cause_externe"] == 100


def test_annee_sans_aucun_retard_retiree():
    ligne = brut(**{"Nombre de trains en retard à l'arrivée": 0,
                    "Prct retard pour causes externes": 0})
    assert nettoyer(ligne)[0].empty  # 100 trains, 0 retard sur l'année


def test_petite_liaison_sans_retard_gardee():
    ligne = brut(**{"Nombre de circulations prévues": 99,
                    "Nombre de trains en retard à l'arrivée": 0,
                    "Prct retard pour causes externes": 0})
    assert len(nettoyer(ligne)[0]) == 1


def test_brut_non_modifie():
    ligne = brut()
    copie = ligne.copy()
    nettoyer(ligne)
    pd.testing.assert_frame_equal(ligne, copie)


def test_fichier_reel_dates_et_compteurs(reel):
    assert reel["date"].str.fullmatch(r"\d{4}-\d{2}").all()
    assert (reel["circules"] > 0).all()
    assert (reel["retards_arrivee"] >= reel["retards_15"]).all()
    assert (reel["retards_arrivee"] <= reel["circules"]).all()
