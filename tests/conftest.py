import pandas as pd
import pytest

from config import FICHIER_BRUT
from nettoyer import nettoyer


@pytest.fixture(scope="session")
def reel():
    """Le vrai fichier du dépôt, nettoyé en mémoire."""
    return nettoyer(pd.read_csv(FICHIER_BRUT, sep=";", encoding="utf-8-sig"))[0]


@pytest.fixture
def petit():
    """Petit tableau dont tous les résultats se calculent à la main."""
    lignes = [
        ("2024-01", "LYON PART DIEU", "PARIS LYON", 120, 10, 90, 9, 5),
        ("2024-02", "LYON PART DIEU", "PARIS LYON", 120, 10, 110, 11, 5),
        ("2025-01", "LYON PART DIEU", "PARIS LYON", 120, 10, 200, 40, 10),
        ("2024-01", "PARIS LYON", "SAINT ETIENNE CHATEAUCREUX", 170, 10, 100, 50, 30),
        ("2024-01", "PARIS MONTPARNASSE", "BREST", 220, 15, 50, 25, 25),
    ]
    df = pd.DataFrame(
        lignes,
        columns=["date", "gare_depart", "gare_arrivee", "duree_min", "seuil_min",
                 "circules", "retards_arrivee", "retards_15"],
    )
    causes = ["cause_externe", "cause_infrastructure", "cause_gestion_trafic",
              "cause_materiel_roulant", "cause_gestion_gare", "cause_voyageurs"]
    for colonne in causes:
        df[colonne] = 0.0
    df["cause_externe"] = [100.0, 0.0, 50.0, 50.0, 50.0]
    df["cause_infrastructure"] = [0.0, 100.0, 50.0, 50.0, 50.0]
    return df
