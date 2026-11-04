# Séance du 4 novembre 2026, avec Claude Code

**Outil :** Claude Code (Opus 5.5). Ajoute ici l'export de la conversation (`/export`).

## Déjà écrit avant cette séance
Structure du dépôt, `src/config.py`, `src/nettoyer.py`, `src/stats.py` (Wilson), garde-fous dans
`src/test.py`, téléchargement du CSV.

## Fait par l'IA
- `config.py` : import manquant ajouté, port 8080 remplacé par Ollama (11434).
- `nettoyer.py` : réécrit (le séparateur du fichier est `;` et le code lisait des virgules).
- `stats.py` : formule de Wilson gardée telle quelle, garde-fous de `test.py` intégrés, puis
  `test.py` supprimé ; ajout de `ecart_newcombe`.
- Créés : `telecharger.py`, `outils.py`, les tests, `pyproject.toml`, le début du README.
- `.gitignore` remplacé (il contenait du code collé par erreur) ; `ai log` renommé `ai_log`.
- Créés ensuite : `agent.py`, `arbitre.py`, `comparer.py`, `demo.py`, `taches/`, `preuves/`,
  `EVIDENCE.md`, `EXPLICATION.md`, le README complet.
- Les 5 décisions de nettoyage et les 12 questions ont été proposées et appliquées par l'IA.

## Corrections faites pendant la séance
- `outils.py` : dates complètes acceptées, car Qwen envoyait `2025-01-01`.
- `nettoyer.py` : décision 5 ajoutée après un 0,0 % de retard jugé suspect sur Paris → Italie.
- `comparer.py` : notation corrigée, car 3 refus citant des années étaient comptés comme faux.
- Constat : l'Arbitre n'a rien bloqué pendant les 36 exécutions réelles du système.

## À compléter par moi
- Gardé tel quel :
- Corrigé à la main (quoi ?) :
- Prompt ou pseudo-code réécrit (quelle ligne, pourquoi ?) :
- Décisions de nettoyage et questions validées ou changées :
