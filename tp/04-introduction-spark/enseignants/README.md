# TP 04 - Introduction à Apache Spark - Corrigé enseignants

Ce document reprend le TP étudiant et place les réponses indicatives directement
sous les questions concernées. Les réponses servent de guide de correction et
peuvent être adaptées selon l'environnement Docker ou cluster utilisé.

## Objectifs

À la fin de ce TP, vous devez être capable de :

- expliquer le rôle de Spark dans une architecture Big Data ;
- distinguer Spark et MapReduce ;
- créer une `SparkSession` ;
- manipuler des `DataFrame` avec PySpark ;
- comprendre la différence entre transformation et action ;
- expliquer le principe d’évaluation paresseuse ;
- lire et écrire des données dans HDFS avec Spark ;
- soumettre une application Spark sur YARN ;
- suivre une application Spark dans YARN, Spark UI et Spark History Server.

## Ressources

Ce TP s’appuie sur les notions présentées dans :

- *Spark: The Definitive Guide*, Bill Chambers et Matei Zaharia ;
- la documentation officielle Spark Quick Start : `https://spark.apache.org/docs/3.5.7/quick-start.html` ;
- la documentation officielle `spark-submit` : `https://spark.apache.org/docs/3.5.7/submitting-applications.html` ;
- la documentation officielle Spark SQL, DataFrames and Datasets : `https://spark.apache.org/docs/3.5.7/sql-programming-guide.html`.

Les exemples interactifs du début de TP utilisent l'image Docker locale du TP
01. Les traitements soumis ensuite au cluster utilisent Spark sur YARN en mode
`cluster`.

## Contexte

Dans les TP précédents, vous avez :

- stocké des fichiers dans HDFS ;
- observé la réplication ;
- exploré YARN ;

Spark est un moteur de traitement distribué plus moderne. Il permet de traiter des données stockées dans HDFS, mais il propose une API plus expressive que MapReduce et optimise les plans d’exécution.

Dans ce TP, vous allez manipuler Spark avec des logs applicatifs simplifiés, dans le contexte du projet fil rouge DORA.

## Prérequis

Pour la première partie interactive, démarrez l'environnement Docker du TP 01
sur votre machine.

```bash
cd tp/01-big-data-hadoop
docker compose up -d
docker exec -it tp-hadoop bash
```

Dans le conteneur, vérifiez que les commandes répondent.

```bash
export USER=$(whoami)
hdfs dfs -ls /
yarn application -list
spark-submit --version
pyspark --version
```

Interfaces locales utiles pendant la première partie :

```text
YARN ResourceManager: http://localhost:8088
Spark History Server: http://localhost:18080
Spark Live UI:        http://localhost:4040
```

Pour la deuxième partie, vous devrez aussi être connecté au gateway Hadoop avec
votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
```

Interfaces cluster utiles :

```text
YARN ResourceManager: http://<gateway_public_ip>:8088
Spark History Server: http://<gateway_public_ip>:18080
YARN Tracking UI:     depuis la page de l'application YARN
```

### Modes de lancement Spark

Dans ce TP, la découverte interactive se fait dans Docker. Les traitements
soumis au cluster du cours utilisent YARN avec `--deploy-mode cluster`.

- `--master local` : Spark s'exécute localement sur une seule machine. C'est utile pour tester, mais ce n'est pas un vrai traitement distribué.
- `--master yarn --deploy-mode client` : le driver Spark reste sur la machine de lancement, tandis que les executors tournent dans YARN. Si la commande est lancée depuis le gateway, elle consomme donc les ressources de la gateway.
- `--master yarn --deploy-mode cluster` : le driver Spark est lui aussi lancé dans YARN. C'est le mode utilisé dans ce TP pour éviter de surcharger la gateway.

## Exercice 1 - Situer Spark dans l’écosystème Hadoop

Spark n’est pas un système de stockage. Il lit des données depuis HDFS ou d’autres systèmes de stockage, puis exécute des traitements distribués.

Répondez aux questions suivantes.

1. Quel problème Spark cherche-t-il à résoudre par rapport à MapReduce ?
   Réponse indicative : Spark réduit la lourdeur des jobs MapReduce en proposant un moteur plus expressif, capable d'enchaîner des transformations et de garder des données en mémoire quand c'est utile.
2. Pourquoi Spark peut-il être plus adapté que MapReduce pour des traitements interactifs ou itératifs ?
   Réponse indicative : Il évite de matérialiser chaque étape sur disque et propose des API interactives comme PySpark, ce qui accélère les itérations d'analyse.
3. Quelle différence faites-vous entre HDFS, YARN et Spark ?
   Réponse indicative : HDFS stocke les fichiers, YARN alloue les ressources du cluster, Spark exécute les traitements distribués.
4. Pourquoi Spark peut-il fonctionner avec YARN ?
   Réponse indicative : Spark peut demander à YARN des containers pour son driver et ses executors.
5. Quels types de traitements du projet DORA pourraient être écrits avec Spark ?
   Réponse indicative : Lecture de logs, nettoyage, enrichissement, calcul d'indicateurs, détection d'erreurs, préparation de tables Hive.
6. Dans quels cas MapReduce peut-il rester pertinent malgré l’existence de Spark ?
   Réponse indicative : Pour comprendre les fondements du calcul distribué, maintenir des jobs existants ou exécuter des traitements simples dans des environnements où Spark n'est pas disponible.

## Exercice 2 - Préparer des données dans HDFS local

Dans le conteneur Docker `tp-hadoop`, créez un dossier de travail HDFS.

Avant setter la variable $USER
```bash
export USER=$(whoami)
```

```bash
hdfs dfs -mkdir -p /user/$USER/tp04/input
hdfs dfs -mkdir -p /user/$USER/tp04/output
```

Créez un fichier local de logs applicatifs.

```bash
cat > logs-spark.csv <<'EOF'
timestamp,application,level,status_code,response_time_ms
2026-01-10T10:00:00Z,payment-api,INFO,200,120
2026-01-10T10:01:12Z,payment-api,WARN,200,850
2026-01-10T10:02:18Z,auth-service,ERROR,401,95
2026-01-10T10:03:44Z,core-banking,INFO,200,430
2026-01-10T10:04:02Z,payment-api,ERROR,500,1320
2026-01-10T10:05:19Z,auth-service,INFO,200,70
2026-01-10T10:06:42Z,core-banking,WARN,200,990
2026-01-10T10:07:05Z,payment-api,INFO,200,110
2026-01-10T10:08:33Z,auth-service,ERROR,403,88
2026-01-10T10:09:51Z,core-banking,ERROR,503,2100
EOF
```

Chargez le fichier dans HDFS.

```bash
hdfs dfs -put -f logs-spark.csv /user/$USER/tp04/input/
```

Vérifiez le chargement.

```bash
hdfs dfs -ls /user/$USER/tp04/input
hdfs dfs -cat /user/$USER/tp04/input/logs-spark.csv
```

Répondez aux questions suivantes.

1. Pourquoi les données d’entrée sont-elles placées dans HDFS ?
   Réponse indicative : HDFS rend les fichiers accessibles au cluster et permet aux traitements distribués de lire les données de manière parallèle.
2. Pourquoi le format CSV est-il pratique pour un premier TP ?
   Réponse indicative : Il est lisible, facile à créer et à inspecter avec des commandes simples.
3. Quelles limites voyez-vous au CSV dans une plateforme de données professionnelle ?
   Réponse indicative : Il est peu typé, verbeux, fragile sur les séparateurs et moins performant pour l'analytique.
4. Quels formats seraient plus adaptés pour des traitements analytiques à grande échelle ?
   Réponse indicative : Parquet et ORC sont plus adaptés, car ils sont typés, compressés et orientés colonnes.

## Exercice 3 - Observer une session Spark selon l'environnement

Dans cet exercice, deux options sont possibles selon votre environnement.

| Environnement | Option à utiliser | Objectif |
|---|---|---|
| Docker | Session PySpark interactive | Observer directement les objets Spark principaux. |
| Gateway ou cluster | Script soumis avec `spark-submit --deploy-mode cluster` | Observer Spark sans exécuter le driver sur la gateway. |

### Option Docker - Session PySpark interactive

Démarrez une session interactive PySpark dans le conteneur Docker. Cette session
reste locale à votre machine et ne consomme pas les ressources de la gateway du
cluster.

```bash
pyspark \
  --master yarn \
  --deploy-mode client \
  --conf spark.driver.host=localhost \
  --conf spark.driver.bindAddress=0.0.0.0
```

Dans le shell PySpark, vérifiez la `SparkSession`.

```python
spark
sc
```

Affichez quelques informations.

```python
spark.version
spark.sparkContext.appName
spark.sparkContext.master
```

Ouvrez la Spark Live UI locale pendant que PySpark est lancé.

```text
http://localhost:4040
```

Si `4040` est déjà utilisé sur votre machine, Spark peut choisir `4041`,
`4042`, etc. Vous pouvez afficher l'URL depuis PySpark :

```python
sc.uiWebUrl
```

### Option gateway ou cluster - Script en mode cluster

Ne lancez pas une session `pyspark` interactive longue depuis la gateway. En
mode interactif, le driver reste sur la machine de lancement et peut consommer
les ressources de la gateway.

Pour observer Spark sans saturer la gateway, créez un petit script et
soumettez-le avec `spark-submit --deploy-mode cluster`.

```bash
cat > observe_spark_session.py <<'EOF'
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("tp04-observe-spark-session")
    .getOrCreate()
)

sc = spark.sparkContext

print("Spark version:", spark.version)
print("Application name:", sc.appName)
print("Master:", sc.master)
print("Deploy mode:", sc.getConf().get("spark.submit.deployMode", "unknown"))
print("Spark user:", sc.sparkUser())

spark.stop()
EOF
```

Soumettez le script depuis la gateway en mode cluster.

```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --queue students \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.executor.instances=1 \
  --conf spark.executor.cores=1 \
  --conf spark.executor.memory=512m \
  --conf spark.yarn.am.cores=1 \
  --conf spark.yarn.am.memory=512m \
  observe_spark_session.py
```

Dans ce mode, le driver est lancé dans YARN. La gateway sert seulement à
soumettre l'application.

Répondez aux questions suivantes.

1. À quoi sert la `SparkSession` ?
   Réponse indicative : Elle est le point d'entrée principal de Spark SQL et des DataFrames.
2. À quoi sert le `SparkContext` ?
   Réponse indicative : Il représente la connexion bas niveau au cluster Spark et porte la configuration d'exécution.
3. Pourquoi fait-on cette partie interactive dans Docker plutôt que sur la gateway ?
   Réponse indicative : Docker offre un environnement local maîtrisé pour expérimenter sans dépendre des règles du cluster partagé.
4. Pourquoi la Spark Live UI n’existe-t-elle que pendant que l’application tourne ?
   Réponse indicative : Elle est servie par l'application Spark active. Une fois l'application arrêtée, il faut consulter l'historique via le History Server.
5. Que voyez-vous dans YARN lorsqu’une session PySpark est ouverte ?
   Réponse indicative : Une application Spark avec son driver, ses containers et son état d'exécution.
6. Pourquoi utilise-t-on `spark-submit --deploy-mode cluster` depuis la gateway ?
   Réponse indicative : En mode cluster, le driver est lancé dans YARN au lieu de rester sur la gateway. Cela évite de consommer durablement CPU et mémoire sur la machine d'accès.

Pour la suite du TP, choisissez le mode adapté à votre environnement.

| Environnement | Manière de travailler |
|---|---|
| Docker | Vous pouvez saisir les blocs des exercices 4 à 8 directement dans la session PySpark interactive. |
| Gateway ou cluster | Ajoutez les blocs des exercices 4 à 8 progressivement dans un fichier Python, puis relancez ce fichier avec `spark-submit --deploy-mode cluster`. |

Sur gateway, ne recopiez pas les blocs dans une session PySpark interactive. Le
code doit être ajouté pas à pas dans le même fichier, avant `spark.stop()`.

Créez le fichier de travail.

```bash
cat > tp04_step_by_step.py <<'EOF'
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = (
    SparkSession.builder
    .appName("tp04-step-by-step")
    .getOrCreate()
)

# Ajoutez ici les blocs des exercices 4 à 8.

spark.stop()
EOF
```

À chaque étape, complétez le fichier puis relancez-le.

```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --queue students \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.executor.instances=1 \
  --conf spark.executor.cores=1 \
  --conf spark.executor.memory=512m \
  --conf spark.yarn.am.cores=1 \
  --conf spark.yarn.am.memory=512m \
  tp04_step_by_step.py
```

## Exercice 4 - Lire un fichier HDFS avec Spark

Dans PySpark ou dans `tp04_step_by_step.py`, lisez le fichier CSV depuis HDFS.

```python
path = f"/user/{spark.sparkContext.sparkUser()}/tp04/input/logs-spark.csv"

df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(path)
)
```

Affichez le schéma.

```python
df.printSchema()
```

Affichez les premières lignes.

```python
df.show(5, truncate=False)
```

Comptez les lignes.

```python
df.count()
```

Répondez aux questions suivantes.

1. Quel est le rôle de l’option `header` ?
   Réponse indicative : Elle indique que la première ligne contient les noms de colonnes.
2. Quel est le rôle de l’option `inferSchema` ?
   Réponse indicative : Elle demande à Spark de déduire les types à partir des données.
3. Quels types Spark a-t-il détectés ?
   Réponse indicative : Selon les données, Spark détecte généralement des chaînes, entiers, doubles ou timestamps. Vérifier avec `printSchema()`.
4. Pourquoi l’inférence de schéma peut-elle être dangereuse sur des fichiers très volumineux ou hétérogènes ?
   Réponse indicative : Elle peut coûter cher, varier selon l'échantillon lu et produire des types incohérents entre fichiers.
5. Quelle commande déclenche réellement un calcul distribué ?
   Réponse indicative : Une action comme `show()`, `count()`, `collect()` ou `write` déclenche le calcul.

## Exercice 5 - Transformations et actions

Dans Spark, une transformation décrit un nouveau jeu de données. Une action déclenche réellement le calcul.

Créez un DataFrame filtré.

```python
errors = df.filter(df.level == "ERROR")
```

À ce stade, Spark n’a pas encore nécessairement exécuté le filtre.

Déclenchez une action.

```python
errors.show(truncate=False)
errors.count()
```

Créez d’autres transformations.

```python
slow = df.filter(df.response_time_ms > 800)

selected = df.select(
    "timestamp",
    "application",
    "level",
    "response_time_ms"
)
```

Déclenchez les actions.

```python
slow.show(truncate=False)
selected.show(truncate=False)
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre transformation et action ?
   Réponse indicative : Une transformation décrit un nouveau DataFrame. Une action déclenche réellement l'exécution.
2. Pourquoi Spark utilise-t-il l’évaluation paresseuse ?
   Réponse indicative : Pour optimiser l'ensemble du plan avant exécution.
3. Quels avantages Spark peut-il tirer du fait de connaître plusieurs transformations avant l’exécution ?
   Réponse indicative : Il peut fusionner des étapes, pousser des filtres, choisir un plan physique et limiter les lectures inutiles.
4. Pourquoi `filter` ne produit-il pas immédiatement un résultat affiché ?
   Réponse indicative : `filter` est une transformation paresseuse. Il faut une action pour obtenir un résultat.

## Exercice 6 - Agréger les logs avec l’API DataFrame

Importez les fonctions Spark SQL si elles ne sont pas déjà présentes dans votre
fichier.

```python
from pyspark.sql import functions as F
```

Comptez les événements par application.

```python
events_by_app = (
    df.groupBy("application")
    .count()
    .orderBy(F.desc("count"))
)

events_by_app.show()
```

Comptez les événements par niveau de log.

```python
events_by_level = (
    df.groupBy("level")
    .count()
    .orderBy(F.desc("count"))
)

events_by_level.show()
```

Calculez le temps de réponse moyen par application.

```python
avg_response = (
    df.groupBy("application")
    .agg(
        F.count("*").alias("event_count"),
        F.avg("response_time_ms").alias("avg_response_time_ms"),
        F.max("response_time_ms").alias("max_response_time_ms")
    )
    .orderBy(F.desc("avg_response_time_ms"))
)

avg_response.show(truncate=False)
```

Répondez aux questions suivantes.

1. Quel est l’équivalent logique d’un `groupBy` dans une requête SQL ?
   Réponse indicative : C'est la clause `GROUP BY`.
2. Pourquoi une agrégation distribuée peut-elle provoquer un shuffle ?
   Réponse indicative : Les lignes d'une même clé doivent être regroupées sur les mêmes partitions pour calculer l'agrégat.
3. Quelle application semble la plus lente ?
   Réponse indicative : Celle avec la latence moyenne ou maximale la plus élevée dans le résultat obtenu.
4. Quelle application semble produire le plus d’erreurs ?
   Réponse indicative : Celle avec le plus grand nombre ou le plus fort taux de lignes en erreur.
5. Quels indicateurs seraient utiles pour une équipe d’exploitation ?
   Réponse indicative : Volume, taux d'erreur, latence moyenne, latence p95, nombre d'avertissements, disponibilité et évolution par date.

## Exercice 7 - Comprendre le plan d’exécution

Affichez le plan d’exécution.

```python
avg_response.explain()
```

Affichez un plan plus détaillé.

```python
avg_response.explain(True)
```

Répondez aux questions suivantes.

1. Pourquoi Spark construit-il un plan d’exécution ?
   Réponse indicative : Pour transformer les opérations déclarées en étapes exécutables et optimisées.
2. Que signifie le fait qu’un plan puisse contenir plusieurs étapes ?
   Réponse indicative : Certaines opérations nécessitent des séparations physiques, par exemple un shuffle ou une agrégation.
3. Où voyez-vous une opération liée au tri ou à l’agrégation ?
   Réponse indicative : Dans le plan affiché par `explain`, avec des opérateurs comme `Sort`, `HashAggregate` ou `Exchange`.
4. Pourquoi le plan logique peut-il être différent du plan physique ?
   Réponse indicative : Le plan logique décrit l'intention, le plan physique décrit comment Spark va l'exécuter concrètement.
5. Pourquoi l’optimisation automatique est-elle importante pour un moteur comme Spark ?
   Réponse indicative : Elle améliore les performances sans demander à l'utilisateur de contrôler manuellement chaque étape distribuée.

## Exercice 8 - Écrire les résultats dans HDFS

Écrivez les résultats en Parquet.

```python
output_path = f"/user/{spark.sparkContext.sparkUser()}/tp04/output/events_by_app_parquet"

events_by_app.write.mode("overwrite").parquet(output_path)
```

Vérifiez depuis PySpark.

```python
spark.read.parquet(output_path).show()
```

Quittez PySpark si vous travaillez en mode interactif Docker.

```python
exit()
```

Vérifiez depuis le shell Linux.

```bash
hdfs dfs -ls -R /user/$USER/tp04/output/events_by_app_parquet
```

Répondez aux questions suivantes.

1. Pourquoi Spark écrit-il souvent plusieurs fichiers de sortie ?
   Réponse indicative : Chaque partition Spark peut écrire son propre fichier `part-*`.
2. Que représente un fichier `part-*` ?
   Réponse indicative : Une partie du résultat produite par une tâche ou une partition.
3. Pourquoi Parquet est-il souvent préférable à CSV pour l’analyse ?
   Réponse indicative : Parquet est typé, compressé et orienté colonnes, ce qui accélère les lectures analytiques.
4. Pourquoi ne faut-il pas supposer qu’un traitement distribué produit un seul fichier ?
   Réponse indicative : Un traitement distribué travaille en parallèle ; produire un seul fichier oblige souvent à réduire artificiellement le parallélisme.
5. Comment organiseriez-vous les sorties Spark dans la zone `/datalake/processed` ?
   Réponse indicative : Par domaine, dataset et partitions de date, par exemple `/datalake/processed/logs/daily_metrics/event_date=YYYY-MM-DD/`.

## Exercice 9 - Créer une application PySpark

À partir de cet exercice, travaillez sur le gateway Hadoop du cluster.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
```

Préparez les données d'entrée dans le HDFS du cluster.

```bash
hdfs dfs -mkdir -p /user/$USER/tp04/input
hdfs dfs -mkdir -p /user/$USER/tp04/output

cat > logs-spark.csv <<'EOF'
timestamp,application,level,status_code,response_time_ms
2026-01-10T10:00:00Z,payment-api,INFO,200,120
2026-01-10T10:01:12Z,payment-api,WARN,200,850
2026-01-10T10:02:18Z,auth-service,ERROR,401,95
2026-01-10T10:03:44Z,core-banking,INFO,200,430
2026-01-10T10:04:02Z,payment-api,ERROR,500,1320
2026-01-10T10:05:19Z,auth-service,INFO,200,70
2026-01-10T10:06:42Z,core-banking,WARN,200,990
2026-01-10T10:07:05Z,payment-api,INFO,200,110
2026-01-10T10:08:33Z,auth-service,ERROR,403,88
2026-01-10T10:09:51Z,core-banking,ERROR,503,2100
EOF

hdfs dfs -put -f logs-spark.csv /user/$USER/tp04/input/
```

Créez un fichier Python.

```bash
cat > spark_log_analysis.py <<'EOF'
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("tp04-spark-log-analysis").getOrCreate()
user = spark.sparkContext.sparkUser()

input_path = f"/user/{user}/tp04/input/logs-spark.csv"
output_path = f"/user/{user}/tp04/output/log_analysis"

df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(input_path)
)

result = (
    df.groupBy("application", "level")
    .agg(
        F.count("*").alias("event_count"),
        F.avg("response_time_ms").alias("avg_response_time_ms")
    )
    .orderBy("application", "level")
)

result.write.mode("overwrite").parquet(output_path)
result.show(truncate=False)

spark.stop()
EOF
```

Soumettez l’application sur YARN.

```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --queue students \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.executor.instances=1 \
  --conf spark.executor.cores=1 \
  --conf spark.yarn.am.cores=1 \
  spark_log_analysis.py
```

Vérifiez la sortie.

```bash
hdfs dfs -ls -R /user/$USER/tp04/output/log_analysis
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre PySpark interactif et `spark-submit` ?
   Réponse indicative : PySpark interactif sert à explorer. `spark-submit` exécute une application reproductible.
2. Pourquoi une application Spark doit-elle appeler `spark.stop()` ?
   Réponse indicative : Pour libérer proprement les ressources Spark.
3. Quel est le nom de l’application visible dans YARN ?
   Réponse indicative : Le nom défini dans `appName`, ou un nom Spark par défaut si aucun nom n'a été donné.
4. Où retrouvez-vous l’application dans le Spark History Server ?
   Réponse indicative : Dans la liste des applications terminées, si les event logs Spark sont activés.
5. Pourquoi `spark-submit` est-il plus adapté qu’un shell interactif pour un traitement récurrent ?
   Réponse indicative : Il permet de versionner, paramétrer, relancer et automatiser l'exécution.

## Exercice 10 - Suivre Spark dans YARN et Spark History Server

Listez les applications YARN.

```bash
yarn application -list -appStates ALL
```

Consultez les logs de votre application.

```bash
yarn logs -applicationId <application_id>
```

Ouvrez les interfaces.

```text
YARN ResourceManager: http://<gateway_public_ip>:8088
Spark History Server: http://<gateway_public_ip>:18080
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre YARN ResourceManager et Spark History Server ?
   Réponse indicative : YARN suit les ressources et applications du cluster. Spark History Server détaille les jobs Spark terminés.
2. Quelles informations Spark History Server apporte-t-il en plus ?
   Réponse indicative : Jobs, stages, tasks, SQL plans, durée, shuffle, lectures, écritures et erreurs Spark.
3. Où voyez-vous les jobs, les stages et les tasks ?
   Réponse indicative : Dans les onglets `Jobs`, `Stages` et les détails de stages du Spark UI ou History Server.
4. Pourquoi un job Spark peut-il contenir plusieurs stages ?
   Réponse indicative : Les shuffles découpent le job en plusieurs étapes physiques.
5. Quelles informations utiliseriez-vous pour diagnostiquer un traitement lent ?
   Réponse indicative : Durée des stages, nombre de tasks, skew, shuffle read/write, spill disque/mémoire et erreurs executor.

## Exercice 11 - Comparer MapReduce et Spark

Reprenez le WordCount du TP 03 et comparez-le à cette version Spark.

Créez un script Spark WordCount.

```bash
cat > spark_wordcount.py <<'EOF'
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("tp04-spark-wordcount").getOrCreate()
user = spark.sparkContext.sparkUser()

input_path = f"/user/{user}/tp03/input/logs-mapreduce-large.txt"
output_path = f"/user/{user}/tp04/output/spark_wordcount"

lines = spark.read.text(input_path)

words = lines.select(
    F.explode(F.split(F.col("value"), r"\s+")).alias("word")
).filter(F.col("word") != "")

counts = words.groupBy("word").count().orderBy(F.desc("count"))

counts.write.mode("overwrite").parquet(output_path)
counts.show(50, truncate=False)

spark.stop()
EOF
```

Lancez le script.

```bash
spark-submit \
  --master yarn \
  --deploy-mode cluster \
  --queue students \
  --conf spark.dynamicAllocation.enabled=false \
  --conf spark.executor.instances=1 \
  --conf spark.executor.cores=1 \
  --conf spark.yarn.am.cores=1 \
  spark_wordcount.py
```

Répondez aux questions suivantes.

1. Quelle version vous semble la plus lisible : MapReduce ou Spark ?
   Réponse indicative : Spark est généralement plus lisible grâce aux DataFrames et aux opérations déclaratives.
2. Comment Spark exprime-t-il le découpage `map`, `shuffle`, `reduce` ?
   Réponse indicative : Les transformations, jointures et agrégations sont traduites en stages, avec des `Exchange` lors des shuffles.
3. Pourquoi l’API DataFrame est-elle plus déclarative ?
   Réponse indicative : On décrit le résultat attendu plutôt que chaque étape bas niveau de lecture, tri et réduction.
4. Quels avantages apporte Spark pour construire des pipelines de traitement plus complexes ?
   Réponse indicative : API haut niveau, SQL, optimiseur, jointures, formats colonnes, orchestration plus simple et intégration avec Hive.
5. Quelles limites ou précautions faut-il garder en tête avec Spark ?
   Réponse indicative : Gérer les volumes, le partitionnement, les shuffles, les petits fichiers, la mémoire et la reproductibilité.

## Exercice 12 - Lien avec le projet fil rouge

Dans le projet DORA, Spark pourra servir à produire des indicateurs d’audit à partir de logs techniques.

Répondez aux questions suivantes.

1. Quels indicateurs Spark pourrait-il produire quotidiennement ?
   Réponse indicative : Volumes, erreurs, taux d'erreur, latence moyenne, p95, incidents, rejets et disponibilité estimée.
2. Quels traitements devraient écrire dans `/datalake/processed` ?
   Réponse indicative : Les données nettoyées, enrichies et agrégées destinées à l'analyse.
3. Quels éléments devraient être écrits dans `/datalake/audit` ?
   Réponse indicative : Rejets, contrôles qualité, statistiques d'exécution, chemins lus et résumé du run.
4. Pourquoi faut-il historiser les résultats des traitements Spark ?
   Réponse indicative : Pour comparer les exécutions, expliquer les résultats et permettre un audit ou un retraitement.
5. Comment structureriez-vous les sorties par date de traitement et par date d’événement ?
   Réponse indicative : Utiliser `event_date` pour le contenu métier et `process_date` ou `run_date` pour l'exécution.
6. Quels contrôles qualité ajouteriez-vous avant d’écrire un résultat dans la zone `processed` ?
   Réponse indicative : Présence des colonnes obligatoires, types, dates valides, clés non nulles, valeurs attendues et taux de rejet.
7. Quelles métadonnées conserveriez-vous pour rendre un traitement Spark auditable ?
   Réponse indicative : Run id, version du code, paramètres, dates traitées, chemins d'entrée/sortie, nombres de lignes et statut.

## Nettoyage

Supprimez les fichiers locaux créés pendant le TP.

```bash
rm -f logs-spark.csv spark_log_analysis.py spark_wordcount.py
```

Supprimez les dossiers de test HDFS si l’enseignant le demande.

```bash
hdfs dfs -rm -r -f /user/$USER/tp04
```

## À retenir

Spark est un moteur de traitement distribué. Il ne remplace pas HDFS ni YARN :

- HDFS stocke les données ;
- YARN alloue les ressources ;
- Spark exécute les traitements.

Les notions essentielles de cette séance sont :

- `SparkSession` ;
- `DataFrame` ;
- transformations ;
- actions ;
- évaluation paresseuse ;
- plan d’exécution ;
- shuffle ;
- écriture distribuée ;
- `spark-submit` ;
- Spark UI et Spark History Server.
