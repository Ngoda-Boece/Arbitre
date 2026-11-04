def intervalle_wilson(succes, total, z=1.96):
    """
    Calcule l'intervalle de confiance de Wilson pour une proportion.

    Args:
        succes (int): Le nombre de succès observés.
        total (int): Le nombre total d'observations.
        z (float): La valeur critique pour le niveau de confiance souhaité (par défaut 1.96 pour 95%).

    Returns:
        tuple: Un tuple contenant la borne inférieure et la borne supérieure de l'intervalle de confiance.
    """
    if total <= 0:
        raise ValueError("Le nombre total d'observations doit être supérieur à zéro.")
    if not (0 <= succes <= total):
        raise ValueError("Le nombre de succès doit être compris entre 0 et le nombre total d'observations.")

    # Proportion observée, par exemple 0,836 pour 83,6 % de trains à l'heure.
    p_hat = succes / total

    # Wilson rapproche légèrement le centre de 0,5 : avec peu d'observations, un 100 %
    # observé ne doit pas donner un intervalle de largeur nulle. Avec beaucoup de trains,
    # ces corrections deviennent minuscules et on retrouve p_hat.
    denominator = 1 + (z**2 / total)
    center_adjusted_probability = p_hat + (z**2 / (2 * total))
    adjusted_standard_deviation = ((p_hat * (1 - p_hat) + (z**2 / (4 * total))) / total)**0.5

    bas = (center_adjusted_probability - z * adjusted_standard_deviation) / denominator
    haut = (center_adjusted_probability + z * adjusted_standard_deviation) / denominator

    # Protège des erreurs d'arrondi aux extrémités : une proportion reste entre 0 et 1.
    return max(0.0, bas), min(1.0, haut)


def ecart_newcombe(succes_a, total_a, succes_b, total_b, z=1.96):
    """
    Intervalle de confiance de l'écart p_b - p_a (méthode de Newcombe) :
    il combine les deux intervalles de Wilson.

    Returns:
        tuple: (écart, borne inférieure, borne supérieure)
    """
    p_a = succes_a / total_a
    p_b = succes_b / total_b
    bas_a, haut_a = intervalle_wilson(succes_a, total_a, z)
    bas_b, haut_b = intervalle_wilson(succes_b, total_b, z)

    # Chaque marge de l'écart combine une marge de B et une marge de A, comme les deux
    # côtés d'un triangle rectangle : on ne les additionne pas, car deux erreurs
    # indépendantes ont peu de chances d'aller au maximum en même temps.
    ecart = p_b - p_a
    bas = ecart - ((p_b - bas_b) ** 2 + (haut_a - p_a) ** 2) ** 0.5
    haut = ecart + ((haut_b - p_b) ** 2 + (p_a - bas_a) ** 2) ** 0.5
    return ecart, bas, haut
