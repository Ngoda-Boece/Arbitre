import pytest

from stats import ecart_newcombe, intervalle_wilson


def test_wilson_reference_publiee():
    # Newcombe (1998) : 81 succès sur 263 donnent 0,2553 à 0,3662.
    bas, haut = intervalle_wilson(81, 263)
    assert bas == pytest.approx(0.2553, abs=0.0002)
    assert haut == pytest.approx(0.3662, abs=0.0002)


def test_wilson_a_la_main():
    # p = 0,5 et n = 100 : centre 0,5, marge 1,96 × 0,05 / 1,0192 ≈ 0,0962.
    bas, haut = intervalle_wilson(50, 100, z=1.96)
    assert bas == pytest.approx(0.4038, abs=0.0002)
    assert haut == pytest.approx(0.5962, abs=0.0002)


@pytest.mark.parametrize("succes, total", [(0, 10), (10, 10), (0, 1), (1, 1)])
def test_wilson_reste_entre_0_et_1(succes, total):
    bas, haut = intervalle_wilson(succes, total)
    assert 0 <= bas <= succes / total <= haut <= 1


@pytest.mark.parametrize("succes, total", [(0, 0), (1, 0), (-1, 10), (11, 10), (1, -5)])
def test_wilson_refuse_les_valeurs_impossibles(succes, total):
    with pytest.raises(ValueError):
        intervalle_wilson(succes, total)


def test_newcombe_reference_publiee():
    # Newcombe (1998), méthode 10 : 56/70 contre 48/80 donnent 0,0524 à 0,3339.
    ecart, bas, haut = ecart_newcombe(48, 80, 56, 70)
    assert ecart == pytest.approx(0.2)
    assert bas == pytest.approx(0.0524, abs=0.0005)
    assert haut == pytest.approx(0.3339, abs=0.0005)


def test_newcombe_ecart_nul():
    ecart, bas, haut = ecart_newcombe(50, 100, 50, 100)
    assert ecart == 0
    assert bas < 0 < haut
