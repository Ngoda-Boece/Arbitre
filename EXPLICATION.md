# Comprendre le projet, pas à pas

Ce guide explique le projet à quelqu'un qui débute, et prépare la soutenance.

## 1. Le problème

Pose à Qwen seul : « Quelle est la ponctualité de Bordeaux vers Paris en 2025 ? » Lors d'un essai,
il a répondu « environ 95 % » et a parlé de travaux de modernisation. Le ton est sûr, mais le vrai
chiffre calculé sur les données est **83,6 %**.

Un modèle de langage prédit du texte plausible. Il ne consulte aucune base de données. Un chiffre
peut donc avoir l'air vrai sans l'être.

## 2. La solution en une image

```text
Question
   │
   ▼
Modèle Qwen ──demande un calcul──► Outil Python ──lit──► Données SNCF nettoyées
   ▲                                    │
   └────────────résultat────────────────┘
   │
   ▼ réponse rédigée
Arbitre : chaque nombre vient-il d'un outil ?
   ├── oui ──► la réponse est montrée
   └── non ──► rejet, une seule nouvelle chance, puis refus de répondre
```

Le modèle rédige, le code calcule, et l'Arbitre contrôle.

## 3. Les mots à connaître

| Mot | Sens simple |
|---|---|
| Modèle de langage | Programme qui prédit la suite d'un texte. Ici, Qwen3.5-4B. |
| Ollama | Logiciel qui fait tourner le modèle sur ton PC. |
| Outil | Fonction Python que le modèle peut demander d'exécuter. |
| Agent | Modèle qui utilise des outils en boucle pour atteindre un but. |
| Trace | Journal d'une exécution : appels, résultats, réponse, temps. |
| Seed | Point de départ du hasard du modèle. Changer de seed change la réponse possible. |
| Intervalle de confiance | Fourchette autour d'un taux, qui exprime son incertitude. |
| Test automatique | Petit programme qui vérifie un résultat connu d'avance. |

## 4. Le chemin d'une question

1. `agent.py` envoie à Qwen la question, les consignes et la fiche des 4 outils.
2. Qwen répond par une demande : `taux_ponctualite`, avec `Bordeaux`, `Paris` et `2025`.
3. `executer_outil` vérifie que cet outil est autorisé, puis l'exécute.
4. `outils.py` trouve la liaison, additionne les trains et calcule 83,6 %.
5. Le résultat est ajouté à la conversation et Qwen rédige sa phrase.
6. `arbitre.py` extrait chaque nombre et le compare aux résultats des outils.
7. Si tout a une source, la réponse sort. Sinon, le modèle a une seule nouvelle chance.

## 5. Le rôle de chaque fichier

| Fichier | Rôle | Brique |
|---|---|---|
| `src/config.py` | Chemins et réglages du modèle | - |
| `src/telecharger.py` | Récupère le CSV SNCF | 6 |
| `src/nettoyer.py` | Nettoie les données et écrit le journal | 6 |
| `src/stats.py` | Intervalles de Wilson et de Newcombe | 8 |
| `src/outils.py` | Les 4 calculs que le modèle peut demander | 1, 8 |
| `src/agent.py` | La boucle entre le modèle et les outils | 1 |
| `src/arbitre.py` | Bloque les nombres sans source | 3 |
| `src/comparer.py` | Compare le système et le modèle seul | 9 |
| `src/demo.py` | Démonstration en trois actes | - |
| `taches/calculer_reponses.py` | Calcule les réponses connues, sans `outils.py` | 9 |
| `tests/` | Vérifie le code sans avoir besoin du modèle | R2 |

## 6. Les données, et pourquoi les nettoyer

Le fichier compte 12 907 lignes : une liaison, un mois. Il a l'air propre, mais il contient des
incohérences que seul un contrôle révèle. Le détail chiffré est dans `data/journal_nettoyage.md`.

- **Lignes sans train circulé :** impossible de calculer un taux.
- **Compteurs contradictoires :** par exemple moins de retards que de retards à plus de 15 min.
- **Causes dont la somme n'atteint pas 100 % :** elles sont vidées, la ligne reste.
- **Années entières sans aucun retard :** Paris → Italie affiche zéro retard pendant 14 mois de suite,
  alors que des trains partent en retard. Sans cette règle, elle sortait « meilleure liaison ».

**La règle absente des colonnes.** Un train n'est « en retard » qu'au-delà d'un seuil qui dépend du
trajet : 5 min sous 1h30, 10 min de 1h30 à 3h, 15 min au-delà. Conséquence : deux liaisons ne se
comparent pas directement avec le taux officiel. Le classement utilise donc la part de trains à
plus de 15 min, le même critère pour toutes.

## 7. L'incertitude, simplement

Le système ne dit pas seulement « 83,6 % », mais « 83,6 %, intervalle à 95 % de 82,9 à 84,3 ».

Sur ce fichier, cet intervalle a une limite qu'il faut savoir dire : le fichier compte tous les
trains, ce n'est pas un sondage. Le calcul traite chaque train comme un tirage indépendant. Or un
incident retarde plusieurs trains le même jour, donc l'intervalle est trop étroit. Ces données ne
disent pas non plus pourquoi une liaison est en retard.

## 8. Ce que l'Arbitre ne fait pas

L'Arbitre vérifie d'où vient un nombre, pas ce qu'il veut dire. Si le modèle appelle l'outil sur la
mauvaise liaison, ou recopie un bon nombre au mauvais endroit, la réponse passe. C'est la limite
principale du projet. Dans la mesure, le système n'a donné aucun chiffre faux, mais la mesure ne
couvre que 12 questions simples.

## 9. Questions probables en soutenance

**Pourquoi ne pas simplement écrire « n'invente pas » dans le prompt ?**
Le modèle peut ignorer une consigne. Le code de l'Arbitre s'exécute à chaque réponse.

**Pourquoi additionner les trains au lieu de faire la moyenne des taux ?**
Un mois de 100 trains compterait autant qu'un mois de 1 000.

**Pourquoi les tests n'ont-ils pas besoin du modèle ?**
Le modèle est un paramètre de `repondre()`. Les tests le remplacent par une fonction qui récite
des réponses prévues. Ils sont ainsi rapides et donnent toujours le même résultat.

**Pourquoi un script séparé pour les réponses connues ?**
Sinon, le test comparerait `outils.py` à lui-même. Deux calculs écrits séparément qui s'accordent
sont une vraie preuve.

**Si la source vaut 83,6, le modèle peut-il écrire 84 ?**
Oui, c'est l'arrondi correct. Il ne peut pas écrire 83 : aucun arrondi de 83,6 ne le donne.

**L'Arbitre a-t-il servi pendant la mesure ?**
Non : il n'a rien bloqué sur les 36 exécutions réelles du système. Le résultat vient surtout des
outils, et il n'y a pas eu de mesure du système sans Arbitre. Son blocage est prouvé par les tests
et par un modèle simulé : c'est une assurance, qui n'a pas eu à servir ici.

**Que se passe-t-il si Qwen boucle sans fin ?**
`MAX_TOURS` arrête la boucle à 6 tours et le système refuse de répondre.

**Pourquoi Qwen ne peut-il pas lancer n'importe quel code ?**
`FONCTIONS` est une liste blanche. Un nom absent de cette liste n'est jamais exécuté.

## 10. Lancer la démonstration

```bash
uv run python src/demo.py
```

Acte 1 : Qwen seul répond. Acte 2 : le système répond avec un vrai calcul. Acte 3 : un chiffre
inventé est injecté et bloqué. Si le modèle est trop lent, `--sans-modele` lance l'acte 3 seul.
