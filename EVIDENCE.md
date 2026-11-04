```bash
uv run python src/agent.py "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"
```


# Preuves par brique

Modèle utilisé : `qwen3.5:4b-q4_K_M`, en local avec Ollama, sur un processeur i7-1355U.
Briques choisies : 1, 3, 6, 8 et 9.

## Brique 1 : mon propre outil

**Ce que je montre.** Le modèle appelle `taux_ponctualite`, une fonction que j'ai écrite, dans une
boucle que j'ai écrite. Dans la trace, l'appel renvoie 83,6 % pour Bordeaux → Paris en 2025.

**Fichiers.** `src/outils.py`, `src/agent.py`, `preuves/trace_appel_outil_t01.json`.

**Reproduire.**

```bash
uv run python src/agent.py "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"
```

## Brique 3 : une règle imposée par le code

**La règle.** Aucun nombre de la réponse finale ne sort sans venir d'un outil, de la question, ou
d'un message d'erreur produit par le code. Après deux tentatives rejetées, le système refuse.

**Le test qui essaie de l'enfreindre.** `test_chiffre_invente_bloque` et
`test_deux_inventions_donnent_un_refus` soumettent des chiffres inventés, qui sont bloqués. La
démonstration fait de même avec un modèle simulé qui appelle le vrai outil, puis invente 97,5 %.

**Résultat à connaître.** L'Arbitre n'a rien bloqué pendant les 36 exécutions réelles du système.
Le blocage est donc prouvé par les tests et le modèle simulé, pas sur une invention réelle de Qwen.
Le système sans Arbitre n'a pas été mesuré : je ne peux pas chiffrer son apport.

**Fichiers.** `src/arbitre.py`, `tests/test_arbitre.py`, `tests/test_agent.py`, `preuves/demo.txt`.

**Reproduire.**

```bash
uv run pytest tests/test_arbitre.py tests/test_agent.py
uv run python src/demo.py --sans-modele
```

## Brique 6 : données sales, décisions écrites

**Ce que je montre.** De vraies données SNCF (12 907 lignes, de janvier 2018 à septembre 2026), dont
12 771 sont gardées. Chaque décision est écrite avec son nombre de lignes dans le journal.

**Règle absente des colonnes.** Le seuil de retard dépend de la durée du trajet : 5 min sous 1h30,
10 min de 1h30 à 3h, 15 min au-delà. **Source :** la description du jeu de données publiée par la
SNCF. Vérification sur le fichier : la part des retards qui dépassent 15 min vaut 41,3 %, 70,5 %,
puis 97 % selon le seuil.

**Décision marquante.** Paris → Italie affiche 0 retard à l'arrivée pendant 14 mois de suite, avec
des trains en retard au départ et une durée figée. La règle « aucun retard sur une année d'au moins
100 trains » retire 32 lignes. Sans elle, cette liaison sortait meilleure liaison de 2024. La vraie
cause de ces zéros n'est pas dans le fichier : c'est une décision de ma part, pas un fait établi.

**Fichiers.** `src/nettoyer.py`, `src/telecharger.py`, `data/journal_nettoyage.md`,
`tests/test_nettoyer.py`.

**Reproduire.**

```bash
uv run python src/nettoyer.py
```

## Brique 8 : des chiffres avec leur incertitude

**Ce que je montre.** Bordeaux → Paris en 2025 : 83,6 % de ponctualité, intervalle de Wilson à 95 %
de 82,9 à 84,3. `comparer_periodes` donne aussi l'intervalle de Newcombe d'un écart entre deux
périodes. Les deux calculs sont vérifiés sur des valeurs publiées par Newcombe (1998).

**Ce que les données ne permettent pas de conclure.** Le fichier compte tous les trains, ce n'est
pas un sondage. L'intervalle traite chaque train comme un tirage indépendant : il est trop étroit,
car un incident retarde plusieurs trains le même jour. Ces données ne prouvent pas non plus pourquoi
une liaison est en retard, et je n'ai pas confirmé que le mode de calcul du taux est celui de la SNCF.

**Fichiers.** `src/stats.py`, `src/outils.py`, `tests/test_stats.py`, `preuves/demo.txt`.

**Reproduire.**

```bash
uv run pytest tests/test_stats.py
uv run python src/agent.py "La ponctualité du réseau a-t-elle changé entre 2024 et 2025 ?"
```

## Brique 9 : une comparaison mesurée

**Protocole.** 12 questions à réponse connue, mon système face à Qwen seul, 3 seeds chacun, soit
72 exécutions. Les réponses connues sont calculées par `taches/calculer_reponses.py`, sans
`outils.py`, puis croisées avec les outils par un test.

| Mesure, sur 12 questions | Système      | Qwen seul    |
| ------------------------ | ------------- | ------------ |
| Réponses justes         | 11,00 ± 0,00 | 0,33 ± 0,58 |
| Chiffres faux affirmés  | 0,00 ± 0,00  | 7,67 ± 0,58 |
| Sans chiffre             | 1,00 ± 0,00  | 4,00 ± 0,00 |
| Temps moyen par question | 37,4 s        | 21,7 s       |

Valeurs : moyenne et écart-type sur les 3 seeds. Le système répond plus juste, mais il est 1,7 fois
plus lent, et l'écart-type nul indique seulement que ses 3 lancements ont donné le même score.

**Un échec expliqué par sa trace : la tâche t06.** Le système échoue 3 fois sur 3 à « Combien de
trains sont arrivés en retard de Strasbourg vers Paris en 2024 ? ». La trace
`preuves/trace_echec_t06.json` montre `appels: []` : Qwen n'appelle aucun outil et répond que ses
outils « ne fournissent que des taux ». C'est faux, car `taux_ponctualite` renvoie `trains_en_retard`.
Le nom de l'outil a probablement pesé plus que sa description. L'Arbitre laisse passer, à raison :
la réponse n'affirme aucun chiffre. Le refus est sans danger, mais il est inutile. Renommer ou
scinder l'outil serait la prochaine correction ; elle n'a pas été mesurée ici.

**Ce qui nuance la mesure.** Sur 72 exécutions :

- La notation par extraction de nombres est simple. Je l'ai corrigée après coup, car 3 refus de Qwen
  seul citant uniquement des années étaient comptés comme faux. Les notes ont été recalculées sans
  relancer le modèle.
- Le système répond parfois sans appeler d'outil sur le piège t12 (2 fois sur 3). Il est noté juste
  car il ne donne aucun chiffre, mais la justification du lancement 2 parle à tort d'un problème de
  format.
- Les 12 questions ont été choisies pour ce projet et ne couvrent pas les questions ambiguës.

**Fichiers.** `src/comparer.py`, `taches/taches.json`, `taches/calculer_reponses.py`,
`tests/test_comparer.py`, `preuves/comparaison.md`, `preuves/resultats.jsonl`.

**Reproduire.**

```bash
uv run python src/comparer.py --rapport
rm preuves/resultats.jsonl
uv run python src/comparer.py
```

La première commande recalcule le rapport sans le modèle. Les deux suivantes relancent tout.
