# Journal de nettoyage

- Lignes lues : **12907**, 26 colonnes.
- Colonne « Retard moyen trains en retard > 15 (si liaison concurrencée par vol) » écartée : 1952 lignes ont une moyenne sous 15 min, ce qui est impossible par définition.
- Colonne « Nombre trains en retard > 30min » écartée : 43 valeurs négatives.
- Colonnes de commentaires écartées : texte libre non utilisé par les calculs.
- Décision 1 : 73 lignes retirées car circulés = prévus - annulés est nul ou négatif.
- Décision 2 : 31 lignes retirées car les compteurs se contredisent (plus de retards que de trains, ou moins de retards que de retards > 15 min). Trains circulés perdus : 4136 sur 3423034.
- Décision 3 : 0 durées nulles vidées (ligne gardée, seuil inconnu).
- Décision 4 : causes vidées sur 88 lignes dont la somme sort de 99-101 %, et sur 118 lignes sans aucun retard.
- Décision 5 : 32 lignes retirées, car leur liaison n'a aucun retard sur une année civile d'au moins 100 trains. Ces valeurs ressemblent à des trous de mesure ; trains circulés perdus : 943.
- Règle hors colonnes : seuil de retard selon la durée (5, 10 ou 15 min). Source : description du jeu de données sur ressources.data.sncf.com.
- Vérification de la règle sur le fichier :

| Seuil | Lignes | Part des retards qui dépassent 15 min |
|---|---|---|
| 5 min | 2090 | 41.3% |
| 10 min | 5551 | 70.5% |
| 15 min | 5044 | 97.0% |

- Gardé tel quel : PARIS VAUGIRARD reste distincte de PARIS MONTPARNASSE (aucune source pour les fusionner) ; ITALIE est une destination, pas une gare ; les mois de 2020 restent.
- Lignes gardées : **12771** sur 12907.
