# TP 04 - Introduction à Apache Spark

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

Les exemples du TP sont adaptés à l’environnement du cours et utilisent PySpark sur YARN.

## Contexte

Dans les TP précédents, vous avez :

- stocké des fichiers dans HDFS ;
- observé la réplication ;
- exploré YARN ;
- lancé un premier traitement MapReduce.

Spark est un moteur de traitement distribué plus moderne. Il permet de traiter des données stockées dans HDFS, mais il propose une API plus expressive que MapReduce et optimise les plans d’exécution.

Dans ce TP, vous allez manipuler Spark avec des logs applicatifs simplifiés, dans le contexte du projet fil rouge DORA.

## Prérequis

Vous devez être connecté au gateway Hadoop avec votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Chargez les environnements Hadoop et Spark.

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
```

Vérifiez que les commandes répondent.

```bash
hdfs dfs -ls /
yarn application -list
spark-submit --version
pyspark --version
```

Interfaces utiles :

```text
YARN ResourceManager: http://<gateway_public_ip>:8088
Spark History Server: http://<gateway_public_ip>:18080
Spark Live UI:        http://<gateway_public_ip>:4040
```

La Spark Live UI est disponible uniquement pendant l’exécution d’une application Spark. Si plusieurs applications Spark tournent en même temps, Spark peut utiliser `4041`, `4042`, etc.

## Exercice 1 - Situer Spark dans l’écosystème Hadoop

Spark n’est pas un système de stockage. Il lit des données depuis HDFS ou d’autres systèmes de stockage, puis exécute des traitements distribués.

Répondez aux questions suivantes.

1. Quel problème Spark cherche-t-il à résoudre par rapport à MapReduce ?
2. Pourquoi Spark peut-il être plus adapté que MapReduce pour des traitements interactifs ou itératifs ?
3. Quelle différence faites-vous entre HDFS, YARN et Spark ?
4. Pourquoi Spark peut-il fonctionner avec YARN ?
5. Quels types de traitements du projet DORA pourraient être écrits avec Spark ?
6. Dans quels cas MapReduce peut-il rester pertinent malgré l’existence de Spark ?

## Exercice 2 - Préparer des données dans HDFS

Créez un dossier de travail.

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
2. Pourquoi le format CSV est-il pratique pour un premier TP ?
3. Quelles limites voyez-vous au CSV dans une plateforme de données professionnelle ?
4. Quels formats seraient plus adaptés pour des traitements analytiques à grande échelle ?

## Exercice 3 - Démarrer PySpark

Démarrez une session interactive PySpark sur YARN.

```bash
pyspark \
  --master yarn \
  --deploy-mode client \
  --conf spark.ui.port=4040
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

Ouvrez la Spark Live UI pendant que PySpark est lancé.

```text
http://<gateway_public_ip>:4040
```

Répondez aux questions suivantes.

1. À quoi sert la `SparkSession` ?
2. À quoi sert le `SparkContext` ?
3. Pourquoi utilise-t-on le mode `client` depuis le gateway ?
4. Pourquoi la Spark Live UI n’existe-t-elle que pendant que l’application tourne ?
5. Que voyez-vous dans YARN lorsqu’une session PySpark est ouverte ?

## Exercice 4 - Lire un fichier HDFS avec Spark

Dans PySpark, lisez le fichier CSV depuis HDFS.

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
2. Quel est le rôle de l’option `inferSchema` ?
3. Quels types Spark a-t-il détectés ?
4. Pourquoi l’inférence de schéma peut-elle être dangereuse sur des fichiers très volumineux ou hétérogènes ?
5. Quelle commande déclenche réellement un calcul distribué ?

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
2. Pourquoi Spark utilise-t-il l’évaluation paresseuse ?
3. Quels avantages Spark peut-il tirer du fait de connaître plusieurs transformations avant l’exécution ?
4. Pourquoi `filter` ne produit-il pas immédiatement un résultat affiché ?

## Exercice 6 - Agréger les logs avec l’API DataFrame

Importez les fonctions Spark SQL.

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
2. Pourquoi une agrégation distribuée peut-elle provoquer un shuffle ?
3. Quelle application semble la plus lente ?
4. Quelle application semble produire le plus d’erreurs ?
5. Quels indicateurs seraient utiles pour une équipe d’exploitation ?

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
2. Que signifie le fait qu’un plan puisse contenir plusieurs étapes ?
3. Où voyez-vous une opération liée au tri ou à l’agrégation ?
4. Pourquoi le plan logique peut-il être différent du plan physique ?
5. Pourquoi l’optimisation automatique est-elle importante pour un moteur comme Spark ?

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

Quittez PySpark.

```python
exit()
```

Vérifiez depuis le shell Linux.

```bash
hdfs dfs -ls -R /user/$USER/tp04/output/events_by_app_parquet
```

Répondez aux questions suivantes.

1. Pourquoi Spark écrit-il souvent plusieurs fichiers de sortie ?
2. Que représente un fichier `part-*` ?
3. Pourquoi Parquet est-il souvent préférable à CSV pour l’analyse ?
4. Pourquoi ne faut-il pas supposer qu’un traitement distribué produit un seul fichier ?
5. Comment organiseriez-vous les sorties Spark dans la zone `/datalake/processed` ?

## Exercice 9 - Créer une application PySpark

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
  --deploy-mode client \
  spark_log_analysis.py
```

Vérifiez la sortie.

```bash
hdfs dfs -ls -R /user/$USER/tp04/output/log_analysis
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre PySpark interactif et `spark-submit` ?
2. Pourquoi une application Spark doit-elle appeler `spark.stop()` ?
3. Quel est le nom de l’application visible dans YARN ?
4. Où retrouvez-vous l’application dans le Spark History Server ?
5. Pourquoi `spark-submit` est-il plus adapté qu’un shell interactif pour un traitement récurrent ?

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
2. Quelles informations Spark History Server apporte-t-il en plus ?
3. Où voyez-vous les jobs, les stages et les tasks ?
4. Pourquoi un job Spark peut-il contenir plusieurs stages ?
5. Quelles informations utiliseriez-vous pour diagnostiquer un traitement lent ?

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
  --deploy-mode client \
  spark_wordcount.py
```

Répondez aux questions suivantes.

1. Quelle version vous semble la plus lisible : MapReduce ou Spark ?
2. Comment Spark exprime-t-il le découpage `map`, `shuffle`, `reduce` ?
3. Pourquoi l’API DataFrame est-elle plus déclarative ?
4. Quels avantages apporte Spark pour construire des pipelines de traitement plus complexes ?
5. Quelles limites ou précautions faut-il garder en tête avec Spark ?

## Exercice 12 - Lien avec le projet fil rouge

Dans le projet DORA, Spark pourra servir à produire des indicateurs d’audit à partir de logs techniques.

Répondez aux questions suivantes.

1. Quels indicateurs Spark pourrait-il produire quotidiennement ?
2. Quels traitements devraient écrire dans `/datalake/processed` ?
3. Quels éléments devraient être écrits dans `/datalake/audit` ?
4. Pourquoi faut-il historiser les résultats des traitements Spark ?
5. Comment structureriez-vous les sorties par date de traitement et par date d’événement ?
6. Quels contrôles qualité ajouteriez-vous avant d’écrire un résultat dans la zone `processed` ?
7. Quelles métadonnées conserveriez-vous pour rendre un traitement Spark auditable ?

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
