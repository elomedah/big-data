# Scripts enseignants

Ce dossier contient des scripts utilisés pour préparer l'environnement ou les
données distribuées aux étudiants.

## Projet 08

Le script `generate_dora_datalake.py` génère le répertoire `datalake/` du
projet 08, avec les logs applicatifs et les référentiels, dont le budget par
équipe.

Exemple d'utilisation côté enseignant :

```bash
python3 infra-hadoop/bin/generate_dora_datalake.py \
  --output datalake \
  --start-date 2026-01-01 \
  --days 31 \
  --events-per-day 50000
```

Le répertoire `datalake/` généré peut ensuite être compressé et partagé aux
étudiants via le lien indiqué dans l'énoncé du projet.
