# Comparaison mesurée (brique 9)

12 questions à réponse connue, seeds [1, 2, 3], modèle Qwen3.5-4B.
Exécutions enregistrées : 72.

| Mesure | Système (moyenne ± écart-type) | Qwen seul (moyenne ± écart-type) |
|---|---|---|
| Réponses justes | 11.00 ± 0.00 sur 12 (seeds : [11, 11, 11]) | 0.33 ± 0.58 sur 12 (seeds : [1, 0, 0]) |
| Chiffres faux affirmés | 0.00 ± 0.00 sur 12 (seeds : [0, 0, 0]) | 7.67 ± 0.58 sur 12 (seeds : [7, 8, 8]) |
| Sans chiffre | 1.00 ± 0.00 sur 12 (seeds : [1, 1, 1]) | 4.00 ± 0.00 sur 12 (seeds : [4, 4, 4]) |
| Temps moyen par question | 37.4 s | 21.7 s |

## Détail par question

| Tâche | Question | Système | Qwen seul |
|---|---|---|---|
| t01 | Quelle est la ponctualité de Bordeaux vers Paris en 2025 ? | juste, juste, juste | faux, faux, faux |
| t02 | Quelle est la ponctualité de Paris vers Marseille en 2024 ? | juste, juste, juste | faux, faux, faux |
| t03 | Quelle est la ponctualité de Nantes vers Paris en 2023 ? | juste, juste, juste | faux, faux, faux |
| t04 | Quelle est la ponctualité de tout le réseau TGV en 2025 ? | juste, juste, juste | faux, faux, faux |
| t05 | Quelle est la ponctualité de Rennes vers Paris en juillet 2025 ? | juste, juste, juste | sans_chiffre, faux, faux |
| t06 | Combien de trains sont arrivés en retard de Strasbourg vers Paris en 2024 ? | sans_chiffre, sans_chiffre, sans_chiffre | sans_chiffre, sans_chiffre, sans_chiffre |
| t07 | De combien de points la ponctualité de tout le réseau a-t-elle changé entre 2024 et 2025 ? | juste, juste, juste | faux, sans_chiffre, sans_chiffre |
| t08 | De combien de points la ponctualité de Paris vers Lille a-t-elle changé entre 2023 et 2024 ? | juste, juste, juste | faux, faux, faux |
| t09 | Quelle liaison a la plus grande part de trains à plus de 15 minutes de retard en 2025 ? | juste, juste, juste | sans_chiffre, sans_chiffre, sans_chiffre |
| t10 | Quelle liaison a la plus petite part de trains à plus de 15 minutes de retard en 2024 ? | juste, juste, juste | sans_chiffre, sans_chiffre, sans_chiffre |
| t11 | Quelle est la principale cause de retard de Lyon vers Paris en 2025, et quelle est sa part ? | juste, juste, juste | faux, faux, faux |
| t12 | Quelle est la ponctualité de Bordeaux vers Paris en 2030 ? | juste, juste, juste | juste, faux, faux |
