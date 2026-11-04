# L'Arbitre des trains

Répond à des questions sur la régularité des TGV et refuse tout chiffre qui n'a pas été calculé
par du code. Le modèle Qwen3.5-4B rédige, des fonctions Python calculent sur les données SNCF, et
un Arbitre contrôle chaque nombre avant de montrer la réponse.

Projet final du cours Coding for AI & Data Science.

## Installation

Il faut [Ollama](https://ollama.com), [uv](https://docs.astral.sh/uv/) et 8 Go de RAM.

```bash
ollama pull qwen3.5:4b-q4_K_M
uv sync
uv run pytest
uv run python src/nettoyer.py
```

Les tests ne demandent pas le modèle. `nettoyer.py` crée le fichier de données utilisé par l'agent.

## Utilisation

```bash
uv run python src/agent.py "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"
uv run python src/agent.py --seul "Quelle est la ponctualité de Bordeaux vers Paris en 2025 ?"
uv run python src/demo.py
uv run python src/demo.py --sans-modele
uv run python src/comparer.py
```

`demo.py` montre Qwen seul, le système complet, puis le blocage d'un chiffre inventé. `--sans-modele`
ne lance que cette dernière partie. `comparer.py` relance les exécutions manquantes ; sur un PC sans
carte graphique adaptée, les 72 exécutions prennent environ 35 minutes.

Pour utiliser llama-server ou Cerebras, définir `LLM_BASE_URL`, `LLM_MODEL` et `LLM_API_KEY`.
`src/agent.py` appelle l'API native d'Ollama : un autre serveur demande d'adapter `appeler_ollama`.

## Données

« Régularité mensuelle TGV par liaisons » (AQST), SNCF,
[ressources.data.sncf.com](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/),
sous licence Open Database License (ODbL). Une copie datée du 4 novembre 2026 se trouve dans
`data/raw/`, pour que les résultats restent reproductibles. `src/telecharger.py` la récupère, et
`data/journal_nettoyage.md` détaille chaque décision de nettoyage.

## Limites

L'Arbitre contrôle l'origine d'un nombre, pas son sens : un nombre correctement recopié mais mal
interprété passe. Les nombres écrits en lettres ne sont détectés que suivis d'une unité. La
comparaison porte sur 12 questions simples.
