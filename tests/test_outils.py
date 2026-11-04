import pytest

from outils import (
    ErreurOutil,
    causes_retard,
    classement_liaisons,
    comparer_periodes,
    taux_ponctualite,
)


def test_taux_a_la_main(petit):
    # Janvier + février 2024 : 200 circulés, 20 en retard, soit 90 %.
    r = taux_ponctualite(petit, "2024-01", "2024-02", "Lyon", "Paris")
    assert r["liaison"] == "LYON PART DIEU -> PARIS LYON"
    assert r["taux_ponctualite_pct"] == 90.0
    assert r["trains_circules"] == 200
    assert r["mois_couverts"] == 2
    assert r["ic95_bas_pct"] < 90 < r["ic95_haut_pct"]
    assert r["seuils_retard_min"] == [10]


def test_annee_seule_couvre_toute_l_annee(petit):
    r = taux_ponctualite(petit, "2024", "2024", "Lyon Part-Dieu", "Paris Lyon")
    assert r["periode"] == "2024-01 à 2024-12"
    assert r["trains_circules"] == 200


def test_date_complete_garde_le_premier_mois(petit):
    # Qwen envoie des dates complètes : janvier ne doit pas disparaître de la période.
    r = taux_ponctualite(petit, "2024-01-01", "2024-02-29", "Lyon", "Paris")
    assert r["periode"] == "2024-01 à 2024-02"
    assert r["trains_circules"] == 200


def test_tout_le_reseau_sans_gare(petit):
    # 2024 : 350 circulés, 95 en retard.
    r = taux_ponctualite(petit, "2024", "2024")
    assert r["liaison"] == "3 liaisons"
    assert r["trains_en_retard"] == 95


def test_noms_avec_accents_et_saint(petit):
    r = taux_ponctualite(petit, "2024", "2024", "Paris Lyon", "Saint-Étienne")
    assert r["liaison"] == "PARIS LYON -> SAINT ETIENNE CHATEAUCREUX"


def test_gare_inconnue_donne_la_liste(petit):
    with pytest.raises(ErreurOutil, match="BREST"):
        taux_ponctualite(petit, "2024", "2024", "Poudlard")


@pytest.mark.parametrize("nom", ["", "   ", "---"])
def test_nom_vide_refuse(petit, nom):
    with pytest.raises(ErreurOutil):
        taux_ponctualite(petit, "2024", "2024", nom)


def test_liaison_inexistante(petit):
    with pytest.raises(ErreurOutil, match="Aucune liaison"):
        taux_ponctualite(petit, "2024", "2024", "Brest", "Lyon")


@pytest.mark.parametrize("debut, fin", [("janvier", "2024"), ("2024-13", "2024-14"), ("2024-1", "2024")])
def test_periode_invalide(petit, debut, fin):
    with pytest.raises(ErreurOutil, match="Période invalide"):
        taux_ponctualite(petit, debut, fin)


def test_periode_inversee(petit):
    with pytest.raises(ErreurOutil, match="inversée"):
        taux_ponctualite(petit, "2025", "2024")


def test_periode_sans_donnees_donne_les_bornes(petit):
    with pytest.raises(ErreurOutil, match="2024-01 à 2025-01"):
        taux_ponctualite(petit, "2030", "2030")


def test_classement_utilise_le_critere_commun(petit):
    # Parts > 15 min en 2024 : Paris-Brest 50 %, Paris-St Étienne 30 %, Lyon-Paris 5 %.
    r = classement_liaisons(petit, "2024", "2024", n=2, trains_min=10)
    assert [l["retard_plus_15_min_pct"] for l in r["classement"]] == [50.0, 30.0]
    assert r["classement"][0]["liaison"] == "PARIS MONTPARNASSE -> BREST"
    assert r["liaisons_comparees"] == 3


def test_classement_meilleures(petit):
    r = classement_liaisons(petit, "2024", "2024", n=1, ordre="meilleures", trains_min=10)
    assert r["classement"][0]["liaison"] == "LYON PART DIEU -> PARIS LYON"


def test_classement_ecarte_les_petites_liaisons(petit):
    r = classement_liaisons(petit, "2024", "2024", n=5, trains_min=100)
    assert all("BREST" not in l["liaison"] for l in r["classement"])


def test_classement_trop_exigeant(petit):
    with pytest.raises(ErreurOutil, match="au moins"):
        classement_liaisons(petit, "2024", "2024", trains_min=100000)


def test_causes_ponderees(petit):
    # 9 retards à 100 % externe, 11 à 100 % infrastructure : 45 % et 55 %.
    r = causes_retard(petit, "2024-01", "2024-02", "Lyon", "Paris")
    assert r["causes_pct"]["causes externes"] == 45.0
    assert r["causes_pct"]["infrastructure"] == 55.0
    assert list(r["causes_pct"])[0] == "infrastructure"


def test_comparaison_a_la_main(petit):
    # 2024 : 90 %. 2025 : 160/200 = 80 %. Écart de -10 points.
    r = comparer_periodes(petit, "2024", "2024", "2025", "2025", "Lyon", "Paris")
    assert r["a"]["taux_ponctualite_pct"] == 90.0
    assert r["b"]["taux_ponctualite_pct"] == 80.0
    assert r["ecart_points"] == -10.0
    assert r["ecart_ic95_haut"] < 0
    assert r["ecart_net"] is True


def test_reel_bordeaux_paris_2025(reel):
    # Additions faites à la main sur les 12 lignes du fichier brut :
    # 12 419 prévus - 50 annulés = 12 369 circulés, dont 2 027 en retard.
    r = taux_ponctualite(reel, "2025", "2025", "Bordeaux", "Paris")
    assert r["liaison"] == "BORDEAUX ST JEAN -> PARIS MONTPARNASSE"
    assert r["trains_circules"] == 12369
    assert r["trains_en_retard"] == 2027
    assert r["taux_ponctualite_pct"] == 83.6
    assert r["mois_couverts"] == 12
    assert r["seuils_retard_min"] == [10]


def test_reel_ambiguite_vaugirard_2018(reel):
    with pytest.raises(ErreurOutil, match="VAUGIRARD"):
        taux_ponctualite(reel, "2018", "2018", "Bordeaux", "Paris")
