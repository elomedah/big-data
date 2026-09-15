# Exemple de projet Spark structuré

Cet exemple montre comment organiser une application Spark avec plusieurs fichiers Python.

## Structure

```text
example-spark-project/
├── jobs/
│   └── log_pipeline_job.py
└── src/
    └── log_pipeline/
        ├── __init__.py
        ├── io.py
        ├── metrics.py
        ├── quality.py
        ├── schemas.py
        └── transforms.py
```

## Rôle des dossiers

- `jobs/` contient les points d’entrée exécutés avec `spark-submit`.
- `src/log_pipeline/` contient le code réutilisable.
- `schemas.py` définit les schémas Spark.
- `io.py` regroupe les lectures et écritures.
- `transforms.py` contient les enrichissements.
- `quality.py` contient les règles de qualité.
- `metrics.py` contient les agrégations métier.

## Exécution

Depuis le dossier `example-spark-project`, construisez l’archive Python.

```bash
cd src
python3 -m zipfile -c ../log_pipeline.zip log_pipeline
cd ..
```

Lancez le job Spark.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  --py-files log_pipeline.zip \
  jobs/log_pipeline_job.py \
  --base-path /user/$USER/datalake \
  --process-date 2026-01-15 \
  --output-format parquet
```

Pour écrire en ORC :

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  --py-files log_pipeline.zip \
  jobs/log_pipeline_job.py \
  --base-path /user/$USER/datalake \
  --process-date 2026-01-15 \
  --output-format orc
```
