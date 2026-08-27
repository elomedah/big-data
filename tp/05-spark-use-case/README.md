# TP 05 - Spark avancé : cas d’usage logs applicatifs

## Objectifs

À la fin de ce TP, vous devez être capable de :

- concevoir un pipeline Spark plus proche d’un cas réel ;
- lire plusieurs sources de logs déposées par différentes équipes ;
- définir un schéma explicite de lecture ;
- enrichir des données avec de nouvelles colonnes ;
- réaliser des jointures avec des référentiels ;
- distinguer les données brutes, enrichies, rejetées et auditables ;
- sauvegarder des résultats en Parquet ou ORC ;
- partitionner les sorties par date et par `app_id` ;
- expliquer les impacts du partitionnement sur la lecture, le stockage et la performance.

## Contexte

Dans le projet fil rouge, plusieurs équipes applicatives déposent leurs logs techniques dans la zone `raw` du Data Lake.

Chaque équipe est responsable d’un périmètre applicatif :

- équipe paiement ;
- équipe sécurité ;
- équipe core banking.

Les logs doivent être :

- conservés dans leur forme brute ;
- transformés en données exploitables ;
- enrichis avec des référentiels applicatifs ;
- partitionnés pour faciliter les analyses ;
- sauvegardés dans un format efficace ;
- accompagnés de traces d’audit.

## Prérequis

Pour la première partie du TP, démarrez l'environnement Docker du TP 01 sur
votre machine.

```bash
cd tp/01-big-data-hadoop
docker compose up -d
docker exec -it --user hadoop tp-hadoop bash
```

Utilisez l'utilisateur `hadoop` dans le conteneur afin que les fichiers HDFS et
les jobs YARN soient créés avec les bons droits. Dans le conteneur, vérifiez que
les commandes répondent.

```bash
export USER=$(whoami)
hdfs dfs -ls /
spark-submit --version
yarn application -list
```

Si HDFS refuse une écriture avec un message indiquant que le NameNode est en
`safe mode`, quittez le safe mode avant de relancer la commande.

```bash
hdfs dfsadmin -safemode leave
```

Interfaces locales utiles pendant cette première partie :

```text
YARN ResourceManager: http://localhost:8088
Spark History Server: http://localhost:18080
Spark Live UI:        http://localhost:4040
```

Si `4040` est déjà utilisé sur votre machine, Spark peut choisir `4041`,
`4042`, etc.

Pour une exécution sur le cluster du cours, connectez-vous au gateway Hadoop
avec votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
```

Vérifiez alors que Spark et HDFS répondent.

```bash
hdfs dfs -ls /
spark-submit --version
yarn application -list
```

Interfaces cluster utiles :

```text
YARN ResourceManager: http://<gateway_public_ip>:8088
Spark History Server: http://<gateway_public_ip>:18080
Spark Live UI:        http://<gateway_public_ip>:4040


```bash
hdfs dfs -mkdir -p /user/$USER/datalake/raw/team_payments/application_logs/year=2026/month=01/day=15
hdfs dfs -mkdir -p /user/$USER/datalake/raw/team_security/application_logs/year=2026/month=01/day=15
hdfs dfs -mkdir -p /user/$USER/datalake/raw/team_core/application_logs/year=2026/month=01/day=15
hdfs dfs -mkdir -p /user/$USER/datalake/raw/referentials
hdfs dfs -mkdir -p /user/$USER/datalake/processed/logs
hdfs dfs -mkdir -p /user/$USER/datalake/audit/spark
```

Vérifiez l’arborescence.

```bash
hdfs dfs -ls -R /user/$USER/datalake
```

Répondez aux questions suivantes.

1. Pourquoi les équipes déposent-elles leurs fichiers dans des sous-dossiers distincts de `raw` ?
2. Pourquoi conserve-t-on une organisation par année, mois et jour dès la zone brute ?

## Exercice 2 - Créer des logs applicatifs multi-équipes

Créez un fichier local pour l’équipe paiement.

```bash
cat > payments_logs.csv <<'EOF'
event_ts,app_id,env,level,status_code,response_time_ms,request_id,message
2026-01-15T08:00:00Z,payment-api,prod,INFO,200,120,req-001,payment accepted
2026-01-15T08:01:10Z,payment-api,prod,WARN,200,920,req-002,slow acquirer response
2026-01-15T08:02:15Z,payment-api,prod,ERROR,504,2100,req-003,acquirer timeout
2026-01-15T08:03:22Z,billing-api,prod,INFO,200,180,req-004,invoice generated
2026-01-15T08:04:42Z,billing-api,prod,ERROR,500,1500,req-005,invoice export failed
EOF
```

Créez un fichier local pour l’équipe sécurité.

```bash
cat > security_logs.csv <<'EOF'
event_ts,app_id,env,level,status_code,response_time_ms,request_id,message
2026-01-15T08:00:11Z,auth-service,prod,INFO,200,80,req-101,token issued
2026-01-15T08:01:28Z,auth-service,prod,ERROR,401,95,req-102,invalid credentials
2026-01-15T08:02:33Z,auth-service,prod,WARN,403,110,req-103,forbidden access
2026-01-15T08:04:18Z,fraud-detector,prod,INFO,200,340,req-104,score computed
2026-01-15T08:05:00Z,fraud-detector,prod,ERROR,500,1900,req-105,model unavailable
EOF
```

Créez un fichier local pour l’équipe core banking.

```bash
cat > core_logs.csv <<'EOF'
event_ts,app_id,env,level,status_code,response_time_ms,request_id,message
2026-01-15T08:00:05Z,core-banking,prod,INFO,200,410,req-201,batch started
2026-01-15T08:01:49Z,core-banking,prod,WARN,200,980,req-202,batch delayed
2026-01-15T08:03:19Z,account-service,prod,INFO,200,220,req-203,account read
2026-01-15T08:04:26Z,account-service,prod,ERROR,503,2400,req-204,database unavailable
2026-01-15T08:06:13Z,core-banking,prod,INFO,200,390,req-205,batch completed
EOF
```

Déposez les fichiers dans la zone `raw`.

```bash
hdfs dfs -put -f payments_logs.csv /user/$USER/datalake/raw/team_payments/application_logs/year=2026/month=01/day=15/
hdfs dfs -put -f security_logs.csv /user/$USER/datalake/raw/team_security/application_logs/year=2026/month=01/day=15/
hdfs dfs -put -f core_logs.csv /user/$USER/datalake/raw/team_core/application_logs/year=2026/month=01/day=15/
```

Vérifiez les dépôts.

```bash
hdfs dfs -ls -R /user/$USER/datalake/raw
```

Répondez aux questions suivantes.

1. Comment identifieriez-vous l’équipe source d’un fichier sans ajouter une colonne dans le CSV ?
2. Quels contrôles devriez-vous effectuer au moment du dépôt dans `raw` ?

## Exercice 3 - Créer des référentiels pour les jointures

Créez un référentiel des applications.

```bash
cat > app_reference.csv <<'EOF'
app_id,app_name,owner_team,criticality,business_domain
payment-api,Payment API,team_payments,high,payments
billing-api,Billing API,team_payments,medium,payments
auth-service,Authentication Service,team_security,high,security
fraud-detector,Fraud Detector,team_security,high,security
core-banking,Core Banking,team_core,critical,banking
account-service,Account Service,team_core,high,banking
EOF
```

Créez un référentiel des SLA.

```bash
cat > app_sla.csv <<'EOF'
app_id,max_response_time_ms,sla_level
payment-api,800,gold
billing-api,1000,silver
auth-service,300,gold
fraud-detector,700,gold
core-banking,900,platinum
account-service,600,gold
EOF
```

Déposez les référentiels dans HDFS.

```bash
hdfs dfs -put -f app_reference.csv /user/$USER/datalake/raw/referentials/
hdfs dfs -put -f app_sla.csv /user/$USER/datalake/raw/referentials/
```

Répondez aux questions suivantes.

1. Pourquoi séparer les logs et les référentiels ?
2. Que se passe-t-il si un `app_id` existe dans les logs mais pas dans le référentiel ?

## Exercice 4 - Lire les données avec un schéma explicite

Créez un script PySpark.

```bash
cat > spark_advanced_logs.py <<'EOF'
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

spark = SparkSession.builder.appName("tp05-spark-advanced-logs").getOrCreate()
user = spark.sparkContext.sparkUser()

base_path = f"/user/{user}/datalake"
raw_logs_path = f"{base_path}/raw/*/application_logs/year=2026/month=01/day=15"
app_reference_path = f"{base_path}/raw/referentials/app_reference.csv"
app_sla_path = f"{base_path}/raw/referentials/app_sla.csv"

log_schema = StructType([
    StructField("event_ts", StringType(), True),
    StructField("app_id", StringType(), True),
    StructField("env", StringType(), True),
    StructField("level", StringType(), True),
    StructField("status_code", IntegerType(), True),
    StructField("response_time_ms", IntegerType(), True),
    StructField("request_id", StringType(), True),
    StructField("message", StringType(), True),
])

app_reference_schema = StructType([
    StructField("app_id", StringType(), True),
    StructField("app_name", StringType(), True),
    StructField("owner_team", StringType(), True),
    StructField("criticality", StringType(), True),
    StructField("business_domain", StringType(), True),
])

app_sla_schema = StructType([
    StructField("app_id", StringType(), True),
    StructField("max_response_time_ms", IntegerType(), True),
    StructField("sla_level", StringType(), True),
])

logs = (
    spark.read
    .option("header", True)
    .schema(log_schema)
    .csv(raw_logs_path)
    .withColumn("source_file", F.input_file_name())
    .withColumn("source_team", F.regexp_extract(F.col("source_file"), r"/raw/([^/]+)/", 1))
)

apps = (
    spark.read
    .option("header", True)
    .schema(app_reference_schema)
    .csv(app_reference_path)
)

sla = (
    spark.read
    .option("header", True)
    .schema(app_sla_schema)
    .csv(app_sla_path)
)

print("Logs bruts")
logs.show(truncate=False)

print("Référentiel applications")
apps.show(truncate=False)

print("Référentiel SLA")
sla.show(truncate=False)
EOF
```

Exécutez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  spark_advanced_logs.py
```

Répondez aux questions suivantes.

1. Pourquoi définit-on un schéma explicite au lieu d’utiliser `inferSchema` ?
2. Comment la colonne `source_team` est-elle déduite ?

## Exercice 5 - Ajouter des colonnes métiers

Complétez le script `spark_advanced_logs.py` après la lecture des référentiels.

```python
enriched_logs = (
    logs
    .withColumn("event_timestamp", F.to_timestamp("event_ts"))
    .withColumn("event_date", F.to_date("event_timestamp"))
    .withColumn("event_hour", F.hour("event_timestamp"))
    .withColumn("is_error", F.col("level") == F.lit("ERROR"))
    .withColumn("is_warning", F.col("level") == F.lit("WARN"))
    .withColumn(
        "latency_bucket",
        F.when(F.col("response_time_ms") < 300, "fast")
         .when(F.col("response_time_ms") < 1000, "medium")
         .otherwise("slow")
    )
)

print("Logs avec colonnes dérivées")
enriched_logs.show(truncate=False)
enriched_logs.printSchema()
```

Relancez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  spark_advanced_logs.py
```

Répondez aux questions suivantes.

1. Pourquoi convertir `event_ts` en timestamp ?
2. Pourquoi créer une colonne `event_date` ?
3. Quel est l’intérêt des colonnes booléennes `is_error` et `is_warning` ?

## Exercice 6 - Réaliser des jointures avec les référentiels

Ajoutez les jointures dans le script.

```python
joined = (
    enriched_logs
    .join(F.broadcast(apps), on="app_id", how="left")
    .join(F.broadcast(sla), on="app_id", how="left")
    .withColumn("sla_breached", F.col("response_time_ms") > F.col("max_response_time_ms"))
)

print("Logs enrichis avec référentiels")
joined.show(truncate=False)
```

Ajoutez une détection des applications inconnues.

```python
unknown_apps = joined.filter(F.col("app_name").isNull())

print("Applications inconnues")
unknown_apps.show(truncate=False)
```

Relancez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  spark_advanced_logs.py
```

Répondez aux questions suivantes.

1. Pourquoi utilise-t-on ici une jointure `left` ?
2. Que signifie une ligne avec `app_name` à `null` ?
3. Pourquoi peut-on utiliser `broadcast` sur les référentiels ?
4. Dans quel cas le `broadcast` deviendrait-il dangereux ?

## Exercice 7 - Agréger les indicateurs par application et par date

Ajoutez les agrégations suivantes.

```python
daily_app_metrics = (
    joined
    .groupBy("event_date", "app_id", "app_name", "owner_team", "criticality", "business_domain")
    .agg(
        F.count("*").alias("event_count"),
        F.sum(F.col("is_error").cast("int")).alias("error_count"),
        F.sum(F.col("is_warning").cast("int")).alias("warning_count"),
        F.avg("response_time_ms").alias("avg_response_time_ms"),
        F.max("response_time_ms").alias("max_response_time_ms"),
        F.sum(F.col("sla_breached").cast("int")).alias("sla_breach_count")
    )
    .withColumn("error_rate", F.col("error_count") / F.col("event_count"))
)

print("Indicateurs quotidiens par application")
daily_app_metrics.show(truncate=False)
```

Ajoutez aussi une agrégation par équipe source.

```python
daily_team_metrics = (
    joined
    .groupBy("event_date", "source_team")
    .agg(
        F.count("*").alias("event_count"),
        F.countDistinct("app_id").alias("application_count"),
        F.sum(F.col("is_error").cast("int")).alias("error_count"),
        F.avg("response_time_ms").alias("avg_response_time_ms")
    )
)

print("Indicateurs quotidiens par équipe source")
daily_team_metrics.show(truncate=False)
```

Répondez aux questions suivantes.

1. Pourquoi agréger par `event_date` et `app_id` ?
2. Quelle différence faites-vous entre `owner_team` et `source_team` ?
3. Pourquoi le taux d’erreur est-il souvent plus utile que le nombre brut d’erreurs ?

## Exercice 8 - Sauvegarder en Parquet avec partitionnement

Ajoutez les chemins de sortie.

```python
processed_logs_path = f"{base_path}/processed/logs/events_parquet"
processed_metrics_path = f"{base_path}/processed/logs/daily_app_metrics_parquet"
audit_metrics_path = f"{base_path}/audit/spark/daily_team_metrics_parquet"
```

Écrivez les logs enrichis en Parquet, partitionnés par date et par application.

```python
(
    joined
    .write
    .mode("overwrite")
    .partitionBy("event_date", "app_id")
    .parquet(processed_logs_path)
)
```

Écrivez les indicateurs quotidiens.

```python
(
    daily_app_metrics
    .write
    .mode("overwrite")
    .partitionBy("event_date", "app_id")
    .parquet(processed_metrics_path)
)
```

Écrivez les indicateurs d’audit par équipe.

```python
(
    daily_team_metrics
    .write
    .mode("overwrite")
    .partitionBy("event_date")
    .parquet(audit_metrics_path)
)
```

Terminez le script.

```python
spark.stop()
```

Relancez le traitement.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  spark_advanced_logs.py
```

Vérifiez les sorties dans HDFS.

```bash
hdfs dfs -ls -R /user/$USER/datalake/processed/logs
hdfs dfs -ls -R /user/$USER/datalake/audit/spark
```

Répondez aux questions suivantes.

1. Pourquoi partitionner les logs enrichis par `event_date` ?
2. Pourquoi ajouter `app_id` dans le partitionnement ?
3. Pourquoi Parquet est-il plus adapté que CSV pour la zone `processed` ?

## Exercice 9 - Lire des données partitionnées

Créez un script de lecture.

```bash
cat > read_partitioned_logs.py <<'EOF'
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("tp05-read-partitioned-logs").getOrCreate()
user = spark.sparkContext.sparkUser()

path = f"/user/{user}/datalake/processed/logs/events_parquet"

df = spark.read.parquet(path)

print("Schéma")
df.printSchema()

print("Filtre sur une date et une application")
(
    df
    .filter((F.col("event_date") == "2026-01-15") & (F.col("app_id") == "payment-api"))
    .select("event_timestamp", "app_id", "level", "response_time_ms", "sla_breached")
    .show(truncate=False)
)

print("Plan d’exécution")
df.filter((F.col("event_date") == "2026-01-15") & (F.col("app_id") == "payment-api")).explain(True)

spark.stop()
EOF
```

Exécutez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  read_partitioned_logs.py
```

Répondez aux questions suivantes.

1. Où voyez-vous les colonnes de partition dans le schéma ?
2. Pourquoi Spark peut-il éviter de lire certaines partitions ?

## Exercice 10 - Sauvegarder en ORC

Le format ORC est un autre format colonne souvent utilisé dans les environnements Hadoop et Hive.

Ajoutez une écriture ORC dans `spark_advanced_logs.py`.

```python
processed_metrics_orc_path = f"{base_path}/processed/logs/daily_app_metrics_orc"

(
    daily_app_metrics
    .write
    .mode("overwrite")
    .partitionBy("event_date", "app_id")
    .orc(processed_metrics_orc_path)
)
```

Relancez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode client \
  spark_advanced_logs.py
```

Vérifiez la sortie ORC.

```bash
hdfs dfs -ls -R /user/$USER/datalake/processed/logs/daily_app_metrics_orc
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre un format ligne et un format colonne ?
2. Pourquoi Parquet et ORC sont-ils adaptés aux traitements analytiques ?

## Exercice 11 - Gérer les lignes rejetées

Ajoutez une règle simple de qualité.

```python
valid_logs = joined.filter(
    F.col("event_timestamp").isNotNull()
    & F.col("app_id").isNotNull()
    & F.col("status_code").isNotNull()
    & F.col("response_time_ms").isNotNull()
)

rejected_logs = joined.filter(
    F.col("event_timestamp").isNull()
    | F.col("app_id").isNull()
    | F.col("status_code").isNull()
    | F.col("response_time_ms").isNull()
)
```

Écrivez les rejets dans la zone `audit`.

```python
rejected_logs_path = f"{base_path}/audit/spark/rejected_logs"

(
    rejected_logs
    .write
    .mode("overwrite")
    .partitionBy("source_team")
    .parquet(rejected_logs_path)
)
```

Répondez aux questions suivantes.

1. Pourquoi ne faut-il pas simplement supprimer les lignes invalides ?
2. Quelles colonnes ajouteriez-vous pour expliquer la raison du rejet ?

## Exercice 12 - Repartition, coalesce et nombre de fichiers

Avant l’écriture, testez différentes stratégies.

```python
(
    daily_app_metrics
    .repartition("event_date", "app_id")
    .write
    .mode("overwrite")
    .partitionBy("event_date", "app_id")
    .parquet(f"{base_path}/processed/logs/repartitioned_metrics")
)

(
    daily_app_metrics
    .coalesce(1)
    .write
    .mode("overwrite")
    .parquet(f"{base_path}/processed/logs/coalesced_metrics")
)
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre `repartition` et `coalesce` ?
2. Pourquoi `coalesce(1)` peut-il être dangereux sur de gros volumes ?
3. Pourquoi un trop grand nombre de petits fichiers pose-t-il problème dans HDFS ?

## Exercice 13 - Suivre et analyser le traitement

Après chaque exécution, ouvrez :

```text
YARN ResourceManager: http://localhost:8088
Spark History Server: http://localhost:18080
```

Sur le cluster du cours, remplacez `localhost` par l'adresse publique du
gateway.

Listez les applications.

```bash
yarn application -list -appStates ALL
```

Consultez les logs d’une application.

```bash
yarn logs -applicationId <application_id>
```

Répondez aux questions suivantes.

1. Combien de jobs Spark votre application exécute-t-elle ?
2. Quelles actions déclenchent ces jobs ?
3. Où voyez-vous les stages ?
4. Quels indices indiquent qu’une jointure ou une agrégation provoque un shuffle ?

## Exercice 14 - Réflexion d’architecture

Répondez aux questions suivantes.

1. Comment organiseriez-vous la zone `raw` si dix équipes déposent chaque jour des logs ?
2. Comment éviteriez-vous qu’une équipe écrase les fichiers d’une autre équipe ?
3. Comment géreriez-vous l’arrivée tardive de logs pour une date déjà traitée ?
4. Comment distingueriez-vous la date d’événement et la date de traitement ?
5. Quelles métadonnées écririez-vous pour chaque exécution Spark ?
6. Comment garantiriez-vous qu’un indicateur produit est reproductible ?
7. Quels compromis voyez-vous entre performance, coût de stockage, lisibilité et auditabilité ?

## Exercice 15 - Structurer un projet Spark avec plusieurs fichiers Python

Les exercices 1 à 14 peuvent être réalisés dans le conteneur Docker
`tp-hadoop`. Cet exercice utilise le projet exemple fourni dans le dépôt ; vous
pouvez le lancer depuis le dépôt local si celui-ci est accessible dans votre
environnement, ou depuis le gateway du cluster si le dossier y a été copié.

Jusqu’ici, les exemples Spark ont été écrits dans un seul fichier. Cette approche est pratique pour apprendre, mais elle devient difficile à maintenir dès que le traitement grandit.

Dans un projet réel, on sépare généralement :

- le point d’entrée du job ;
- les schémas ;
- les fonctions de lecture et d’écriture ;
- les transformations ;
- les règles de qualité ;
- les agrégations métier ;
- les tests éventuels.

Un exemple de projet est fourni dans ce dossier :

```text
tp/05-spark-use-case/example-spark-project
```

Si vous travaillez avec Docker et que le dépôt est sur votre machine hôte,
copiez le projet dans le conteneur.

```bash
docker cp tp/05-spark-use-case/example-spark-project tp-hadoop:/home/hadoop/example-spark-project
docker exec tp-hadoop chown -R hadoop:hadoop /home/hadoop/example-spark-project
docker exec -it --user hadoop tp-hadoop bash
cd /home/hadoop/example-spark-project
```

Si vous travaillez sur le cluster du cours, copiez le projet vers le gateway.

```bash
scp -r -i ~/.ssh/m2-hadoop-student \
  tp/05-spark-use-case/example-spark-project \
  identifiant@<gateway_public_ip>:~/

ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
cd ~/example-spark-project
```

Structure proposée :

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

Rôle des fichiers :

- `jobs/log_pipeline_job.py` : point d’entrée exécuté avec `spark-submit` ;
- `schemas.py` : schémas explicites des logs et référentiels ;
- `io.py` : fonctions de lecture et d’écriture ;
- `transforms.py` : enrichissement des logs et jointures ;
- `quality.py` : séparation des lignes valides et rejetées ;
- `metrics.py` : calcul des indicateurs.

Si le dépôt est directement accessible depuis l’environnement d’exécution,
placez-vous dans le dossier de l’exemple.

```bash
cd tp/05-spark-use-case/example-spark-project
```

Construisez une archive Python contenant le package `log_pipeline`.

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

Pour écrire les sorties en ORC :

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

Vérifiez les sorties.

```bash
hdfs dfs -ls -R /user/$USER/datalake/processed/logs
hdfs dfs -ls -R /user/$USER/datalake/audit/spark
```

Répondez aux questions suivantes.

1. Pourquoi est-il préférable de ne pas mettre tout le code Spark dans un seul fichier ?
2. À quoi sert l’option `--py-files` de `spark-submit` ?
3. Que faudrait-il ajouter pour transformer cet exemple en projet industrialisable ?

## Nettoyage (Optionnel : le TP-06 aura besoin des données)

Supprimez les fichiers locaux créés pendant le TP.

```bash
rm -f payments_logs.csv security_logs.csv core_logs.csv
rm -f app_reference.csv app_sla.csv
rm -f spark_advanced_logs.py read_partitioned_logs.py
rm -f tp/05-spark-use-case/example-spark-project/log_pipeline.zip
```

Supprimez les dossiers de test HDFS si l’enseignant le demande.

```bash
hdfs dfs -rm -r -f /user/$USER/datalake/processed/logs
hdfs dfs -rm -r -f /user/$USER/datalake/audit/spark
```

Ne supprimez pas la zone `raw` sans consigne explicite.

## À retenir

Ce TP introduit des concepts importants pour construire des pipelines Spark plus proches d’un environnement professionnel :

- lecture multi-sources ;
- schéma explicite ;
- enrichissement avec `withColumn` ;
- extraction de métadonnées depuis le chemin source ;
- jointures avec référentiels ;
- `broadcast join` ;
- indicateurs par date, application et équipe ;
- écriture Parquet et ORC ;
- partitionnement par `event_date` et `app_id` ;
- gestion des rejets ;
- auditabilité ;
- structuration d’un projet Spark multi-fichiers ;
- observation avec YARN et Spark History Server.
