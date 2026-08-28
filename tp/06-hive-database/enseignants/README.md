# TP 06 - Hive : bases, tables externes et partitionnement - Corrigé enseignants

Ce document reprend le TP étudiant et place les réponses indicatives directement
sous les questions concernées. Les réponses servent de guide de correction et
peuvent être adaptées selon l'environnement Docker ou cluster utilisé.

## Objectifs

À la fin de ce TP, vous devez être capable de :

- démarrer un environnement Hive local avec Docker ;
- vous connecter à Hive avec `beeline` ;
- créer une base Hive dédiée au projet fil rouge ;
- distinguer base, table interne, table externe et partition ;
- créer des tables externes sur des données stockées hors du warehouse Hive ;
- exposer dans Hive les zones `raw`, `processed` et `audit` du Data Lake ;
- charger ou détecter des partitions avec `ALTER TABLE` et `MSCK REPAIR TABLE` ;
- écrire des requêtes analytiques HiveQL sur des logs partitionnés ;
- relier les choix de modélisation Hive au contexte DORA.

## Ressource d'installation

Ce TP s'appuie sur la logique d'installation locale présentée dans :

```text
https://github.com/elomedah/iris-big-data/blob/master/TP-hive/01-install-hive-docker.md
```

Si vous travaillez sur le cluster du cours plutôt qu'en local Docker, utilisez les mêmes commandes HiveQL, mais connectez-vous depuis le gateway Hadoop.

## Contexte

Dans les TP précédents, vous avez construit progressivement une zone de stockage pour le projet fil rouge :

- `raw` : logs bruts déposés par les équipes ;
- `processed` : données enrichies ou agrégées par Spark ;
- `audit` : traces de contrôle, rejets et indicateurs d'audit.

Hive permet maintenant de donner une couche SQL à ces fichiers. L'objectif n'est pas de déplacer toutes les données dans Hive, mais de créer des métadonnées qui pointent vers les fichiers déjà présents dans le Data Lake.

Dans ce TP, les tables principales seront donc des tables externes partitionnées.

## Prérequis

### Option A - Installation locale Docker

Suivez d'abord le TP d'installation Hive Docker indiqué dans la ressource d'installation.

Vérifiez que les conteneurs sont démarrés.

```bash
docker ps
```

Connectez-vous à Hive avec `beeline`.

```bash
export HIVE_USER=$(whoami)
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -n "$HIVE_USER"
```

Si `beeline` est exécuté depuis la machine hôte, lancez-le dans le conteneur
`tp-hadoop`.

```bash
docker exec -it tp-hadoop bash -lc 'export HIVE_USER=$(whoami) && beeline -u "jdbc:hive2://localhost:10000/default;auth=noSasl" -n "$HIVE_USER"'
```

### Option B - Gateway Hadoop du cours

Connectez-vous au gateway.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Chargez les environnements Hadoop et Hive.

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/hive.sh
```

Vérifiez que HDFS et Hive répondent.

```bash
hdfs dfs -ls /
export HIVE_USER=$(whoami)
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -n "$HIVE_USER"
```

Interfaces utiles :

```text
NameNode UI:          http://<gateway_public_ip>:9870
YARN ResourceManager: http://<gateway_public_ip>:8088
HiveServer2:          jdbc:hive2://<gateway_public_ip>:10000
```

## Exercice 1 - Comprendre le rôle de Hive

Hive est une couche SQL au-dessus d'un stockage distribué. Les données peuvent rester dans HDFS, tandis que Hive conserve les métadonnées dans le metastore :

- nom des bases ;
- nom des tables ;
- colonnes et types ;
- formats de fichiers ;
- emplacements HDFS ;
- partitions ;
- propriétés des tables.

Répondez aux questions suivantes.

1. Pourquoi Hive est-il utile au-dessus de HDFS ?
   Réponse indicative : Hive ajoute une couche SQL et un catalogue de métadonnées au-dessus des fichiers HDFS. Il permet d'interroger des fichiers sans écrire directement du code MapReduce ou Spark.
2. Quelle différence faites-vous entre HDFS et Hive ?
   Réponse indicative : HDFS stocke les fichiers. Hive décrit ces fichiers sous forme de bases, tables, colonnes, formats et partitions.
3. Quel est le rôle du metastore ?
   Réponse indicative : Le metastore conserve les métadonnées Hive : noms des tables, schémas, emplacements HDFS, formats, partitions et propriétés.
4. Pourquoi Hive est-il adapté à des analyses batch plutôt qu'à des requêtes transactionnelles très fréquentes ?
   Réponse indicative : Hive est conçu pour scanner de gros volumes et lancer des traitements distribués. Il n'est pas optimisé pour des accès ligne à ligne, des mises à jour fréquentes ou une faible latence transactionnelle.
5. Dans le projet DORA, quels utilisateurs pourraient interroger les données avec Hive ?
   Réponse indicative : Des data analysts, data engineers, équipes d'exploitation, contrôleurs internes ou équipes conformité peuvent utiliser Hive pour analyser les logs et les indicateurs produits.

## Exercice 2 - Préparer les données du projet fil rouge

Ce TP part du principe que les données du TP 05 sont déjà présentes dans
`/user/$USER/datalake`. Ne créez pas de nouveau jeu de données : réutilisez les
logs bruts, les référentiels et les sorties Parquet ou ORC produits par Spark.

Vérifiez que l'arborescence attendue existe.

```bash
hdfs dfs -ls -R /user/$USER/datalake/raw
hdfs dfs -ls -R /user/$USER/datalake/processed/logs
hdfs dfs -ls -R /user/$USER/datalake/audit/spark
```

Créez uniquement le dossier d'audit Hive s'il n'existe pas encore.

```bash
hdfs dfs -mkdir -p /user/$USER/datalake/audit/hive
```

Si une des commandes de vérification échoue, revenez au TP 05 et relancez le
traitement Spark avant de continuer ce TP.


## Exercice 3 - Se connecter à Hive et inspecter l'environnement

Récupérez d'abord le nom de l'utilisateur courant, puis connectez-vous avec
`beeline` en transmettant ce nom à HiveServer2.

```bash
export HIVE_USER=$(whoami)
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -n "$HIVE_USER"
```

Dans Hive, affichez les bases existantes.

```sql
SHOW DATABASES;
```

Affichez la configuration du warehouse.

```sql
SET hive.metastore.warehouse.dir;
```

Affichez l'utilisateur courant.

```sql
SELECT current_user();
```

## Exercice 4 - Créer une base Hive pour le projet

Créez une base dédiée. Remplacez `<identifiant>` par votre identifiant si la
variable n'est pas disponible dans votre environnement Hive.

**Les caractères `<` et `>` sont volontaires : la requête échouera si vous ne
remplacez pas `<identifiant>` par votre vrai nom d'utilisateur.**

```sql
CREATE DATABASE IF NOT EXISTS dora_fil_rouge_<identifiant>
COMMENT 'Base Hive du projet fil rouge DORA'
LOCATION '/user/<identifiant>/hive/dora_fil_rouge.db';
```

Utilisez la base.

```sql
USE dora_fil_rouge_<identifiant>;
```

Vérifiez.

```sql
SHOW DATABASES LIKE 'dora*';
DESCRIBE DATABASE EXTENDED dora_fil_rouge_<identifiant>;
```

Répondez aux questions suivantes.

1. Pourquoi créer une base par étudiant ou par équipe ?
   Réponse indicative : Cela isole les tables, évite les collisions de noms et facilite les droits, le nettoyage et la correction.
2. À quoi sert la clause `LOCATION` dans `CREATE DATABASE` ?
   Réponse indicative : Elle indique le dossier HDFS où Hive stockera par défaut les données des tables internes créées dans cette base.
3. Que se passerait-il si toutes les équipes utilisaient la même base ?
   Réponse indicative : Les tables risqueraient d'être écrasées ou confondues, et les droits seraient plus difficiles à gérer.
4. Quelles conventions de nommage appliqueriez-vous pour les bases Hive d'un projet réel ?
   Réponse indicative : Des noms explicites, stables, en minuscules, sans caractères spéciaux, incluant éventuellement le projet, l'environnement et l'équipe.

## Exercice 5 - Créer une table externe sur les logs bruts

Créez une table externe partitionnée sur les logs bruts.

**Remplacez `<identifiant>` par votre nom d'utilisateur HDFS. Pour le connaître,
exécutez `whoami` dans le terminal avant d'ouvrir Hive. Dans le conteneur Docker
du TP, ce nom peut être `root` ou `hadoop` selon l'utilisateur utilisé. Sur la
gateway du cluster, utilisez votre identifiant étudiant affiché par `whoami`.
Supprimez aussi les caractères `<` et `>` lors du remplacement.**

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS raw_application_logs (
  event_ts STRING,
  app_id STRING,
  env STRING,
  level STRING,
  status_code INT,
  response_time_ms INT,
  request_id STRING,
  message STRING
)
PARTITIONED BY (
  source_team STRING,
  year STRING,
  month STRING,
  day STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/<identifiant>/datalake/raw';
```

Ajoutez explicitement une partition.

```sql
ALTER TABLE raw_application_logs ADD IF NOT EXISTS
PARTITION (
  source_team='team_payments',
  year='2026',
  month='01',
  day='15'
)
LOCATION '/user/<identifiant>/datalake/raw/team_payments/application_logs/year=2026/month=01/day=15';
```

Listez les partitions.

```sql
SHOW PARTITIONS raw_application_logs;
```

Interrogez les données.

```sql
SELECT app_id, level, status_code, response_time_ms, source_team, year, month, day
FROM raw_application_logs
WHERE year = '2026'
  AND month = '01'
  AND day = '15'
LIMIT 20;
```

Répondez aux questions suivantes.

1. Pourquoi la table est-elle externe ?
   Réponse indicative : Les fichiers existent déjà dans le Data Lake. Hive ne doit pas les posséder ni les supprimer si la table est supprimée.
2. Que signifie la clause `LOCATION` au niveau de la table ?
   Réponse indicative : Elle définit le dossier racine dans HDFS où Hive cherche les fichiers ou les partitions de la table.
3. Que signifie la clause `LOCATION` au niveau de la partition ?
   Réponse indicative : Elle associe une partition Hive précise à un dossier HDFS précis.
4. Pourquoi `source_team`, `year`, `month` et `day` ne sont-ils pas dans les colonnes du CSV ?
   Réponse indicative : Ces valeurs sont portées par l'arborescence HDFS et déclarées comme colonnes de partition.
5. Quel problème voyez-vous avec l'en-tête CSV dans une table Hive simple ?
   Réponse indicative : Sans configuration particulière, Hive peut lire la ligne d'en-tête comme une ligne de données.

## Exercice 6 - Corriger la lecture de l'en-tête CSV

Ajoutez une propriété pour ignorer la première ligne des fichiers CSV.

```sql
ALTER TABLE raw_application_logs
SET TBLPROPERTIES ('skip.header.line.count'='1');
```

Relancez une requête de contrôle.

```sql
SELECT app_id, COUNT(*) AS event_count
FROM raw_application_logs
WHERE year = '2026'
  AND month = '01'
  AND day = '15'
GROUP BY app_id
ORDER BY event_count DESC;
```

Répondez aux questions suivantes.

1. Pourquoi l'en-tête CSV peut-il poser problème ?
   Réponse indicative : Il contient les noms de colonnes, pas des données. Si Hive le lit comme une ligne normale, les agrégations et conversions de type peuvent être faussées.
2. Pourquoi cette solution reste-t-elle fragile sur des fichiers CSV complexes ?
   Réponse indicative : CSV gère mal les séparateurs dans les champs, les guillemets, les retours ligne intégrés et les évolutions de schéma.
3. Quels formats sont plus adaptés pour la zone `processed` ?
   Réponse indicative : Parquet et ORC sont plus adaptés car ils sont typés, compressés, colonnes et efficaces pour les lectures analytiques.
4. Pourquoi Spark a-t-il écrit en Parquet ou ORC dans le TP 05 ?
   Réponse indicative : Spark produit des données nettoyées et structurées. Un format colonne rend ces sorties plus rapides et plus fiables à relire par Hive ou Spark.

## Exercice 7 - Créer une table externe sur les indicateurs traités

Créez une table externe sur la sortie Parquet produite dans le TP 05.

Dans l'image Docker du cours, utilisez Parquet pour cette table. Certaines
combinaisons Hive/ORC peuvent échouer à la lecture de fichiers ORC écrits par
Spark avec une erreur de compatibilité ORC/protobuf.

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS processed_daily_app_metrics (
  app_name STRING,
  owner_team STRING,
  criticality STRING,
  business_domain STRING,
  event_count BIGINT,
  error_count BIGINT,
  warning_count BIGINT,
  avg_response_time_ms DOUBLE,
  max_response_time_ms INT,
  sla_breach_count BIGINT,
  error_rate DOUBLE
)
PARTITIONED BY (
  event_date STRING,
  app_id STRING
)
STORED AS PARQUET
LOCATION '/user/<identifiant>/datalake/processed/logs/daily_app_metrics_parquet';
```

Demandez à Hive de découvrir les partitions existantes.

```sql
MSCK REPAIR TABLE processed_daily_app_metrics;
SHOW PARTITIONS processed_daily_app_metrics;
```

Interrogez les indicateurs.

```sql
SELECT event_date, app_id, event_count, error_count, error_rate, sla_breach_count
FROM processed_daily_app_metrics
WHERE event_date = '2026-01-15'
ORDER BY error_rate DESC;
```

Si votre environnement Hive lit correctement les fichiers ORC produits par
Spark, vous pouvez utiliser `STORED AS ORC` et pointer vers
`/user/<identifiant>/datalake/processed/logs/daily_app_metrics_orc`.

Répondez aux questions suivantes.

1. Pourquoi la zone `processed` est-elle plus adaptée à Hive que la zone `raw` ?
   Réponse indicative : Elle contient des données déjà structurées, typées, enrichies et souvent écrites dans un format optimisé.
2. Pourquoi les formats colonnes accélèrent-ils certaines requêtes analytiques ?
   Réponse indicative : Hive peut lire seulement les colonnes nécessaires et bénéficier de la compression et des métadonnées du format.
3. À quoi sert `MSCK REPAIR TABLE` ?
   Réponse indicative : Cette commande parcourt l'arborescence HDFS de la table et ajoute au metastore les partitions déjà présentes sur disque.
4. Dans quel cas préféreriez-vous `ALTER TABLE ADD PARTITION` à `MSCK REPAIR TABLE` ?
   Réponse indicative : Quand on connaît exactement les partitions à ajouter, ou quand on veut éviter un scan coûteux de toute l'arborescence.

## Exercice 8 - Créer une table d'audit Hive

Créez une table externe pour historiser des contrôles Hive.

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS audit_hive_checks (
  check_ts STRING,
  check_name STRING,
  table_name STRING,
  partition_filter STRING,
  row_count BIGINT,
  status STRING,
  comment STRING
)
PARTITIONED BY (
  check_date STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/<identifiant>/datalake/audit/hive/checks';
```

Créez un fichier local de contrôle.

```bash
cat > hive_audit_check.csv <<'EOF'
2026-01-15T09:00:00Z,row_count_raw,raw_application_logs,year=2026/month=01/day=15,5,OK,raw partition readable
EOF
```

Déposez-le dans HDFS.

```bash
hdfs dfs -mkdir -p /user/$USER/datalake/audit/hive/checks/check_date=2026-01-15
hdfs dfs -put -f hive_audit_check.csv /user/$USER/datalake/audit/hive/checks/check_date=2026-01-15/
```

Dans Hive, réparez la table et interrogez l'audit.

```sql
MSCK REPAIR TABLE audit_hive_checks;

SELECT *
FROM audit_hive_checks
WHERE check_date = '2026-01-15';
```

## Exercice 9 - Requêtes analytiques sur le projet fil rouge

Comptez les événements par application et par niveau.

```sql
SELECT app_id, level, COUNT(*) AS event_count
FROM raw_application_logs
WHERE year = '2026'
  AND month = '01'
  AND day = '15'
GROUP BY app_id, level
ORDER BY app_id, level;
```

Identifiez les applications avec des erreurs.

```sql
SELECT app_id, COUNT(*) AS error_count
FROM raw_application_logs
WHERE year = '2026'
  AND month = '01'
  AND day = '15'
  AND level = 'ERROR'
GROUP BY app_id
ORDER BY error_count DESC;
```

Analysez les indicateurs traités si la table `processed_daily_app_metrics` est disponible.

```sql
SELECT
  event_date,
  app_id,
  owner_team,
  event_count,
  error_count,
  ROUND(error_rate * 100, 2) AS error_rate_percent,
  sla_breach_count
FROM processed_daily_app_metrics
WHERE event_date = '2026-01-15'
ORDER BY error_rate DESC, sla_breach_count DESC;
```

Répondez aux questions suivantes.

1. Pourquoi filtrer sur les colonnes de partition ?
   Réponse indicative : Le filtre permet à Hive d'éliminer des dossiers entiers avant la lecture. C'est le partition pruning.
2. Que se passerait-il sur plusieurs années de logs sans filtre de partition ?
   Réponse indicative : Hive pourrait scanner un très grand nombre de dossiers et de fichiers, ce qui augmenterait fortement le temps de traitement et la charge du cluster.

## Exercice 10 - Observer le plan d'exécution

Activez l'affichage du plan.

```sql
EXPLAIN
SELECT app_id, COUNT(*) AS error_count
FROM raw_application_logs
WHERE year = '2026'
  AND month = '01'
  AND day = '15'
  AND level = 'ERROR'
GROUP BY app_id;
```

Comparez avec une requête sans filtre de partition.

```sql
EXPLAIN
SELECT app_id, COUNT(*) AS error_count
FROM raw_application_logs
WHERE level = 'ERROR'
GROUP BY app_id;
```

Répondez aux questions suivantes.

1. Où voyez-vous l'effet du filtre de partition ?
   Réponse indicative : Dans le plan `EXPLAIN`, Hive indique les partitions ou chemins retenus. Avec un filtre sur `year`, `month` et `day`, moins de partitions sont lues.
2. Pourquoi le partition pruning est-il important ?
   Réponse indicative : Il réduit le volume de données lues, le nombre de fichiers ouverts et le nombre de tâches nécessaires.
3. Pourquoi une table très partitionnée peut-elle aussi devenir difficile à gérer ?
   Réponse indicative : Trop de partitions augmente la taille du metastore, ralentit les réparations et peut produire beaucoup de petits dossiers ou petits fichiers.
4. Comment choisiriez-vous les colonnes de partition dans un Data Warehouse Hive ?
   Réponse indicative : Il faut choisir des colonnes très utilisées dans les filtres, de cardinalité raisonnable, stables et cohérentes avec les usages de lecture.

## Exercice 11 - Tables internes et externes

Créez une petite table interne de démonstration.

```sql
CREATE TABLE IF NOT EXISTS demo_internal_table (
  id INT,
  label STRING
);

INSERT INTO demo_internal_table VALUES
(1, 'created by hive'),
(2, 'managed table');
```

Comparez les métadonnées.

```sql
DESCRIBE FORMATTED demo_internal_table;
DESCRIBE FORMATTED raw_application_logs;
```

Dans un terminal, observez les fichiers HDFS créés pour la table interne.

```bash
hdfs dfs -ls -R /user/$USER/hive/dora_fil_rouge.db/demo_internal_table
```
```bash
hdfs dfs -cat /user/$USER/hive/dora_fil_rouge.db/demo_internal_table/*
```

Dans Hive, supprimez la table interne.

```sql
DROP TABLE demo_internal_table;
```

Dans le terminal, relancez la vérification HDFS.

```bash
hdfs dfs -ls -R /user/$USER/hive/dora_fil_rouge.db/demo_internal_table
```

La commande doit indiquer que le chemin n'existe plus : Hive a supprimé les
fichiers car `demo_internal_table` est une table interne.

Répondez aux questions suivantes.

1. Quelle différence voyez-vous dans le type de table ?
   Réponse indicative : `demo_internal_table` est une table interne ou managed table. `raw_application_logs` est une table externe.
2. Où sont stockées les données de la table interne ?
   Réponse indicative : Elles sont stockées dans le warehouse Hive de la base, ici sous le dossier de la base `dora_fil_rouge.db`.
3. Pourquoi une suppression de table interne peut-elle être plus dangereuse ?
   Réponse indicative : Supprimer une table interne supprime aussi ses fichiers HDFS. On peut donc perdre les données, pas seulement les métadonnées.
4. Pourquoi les tables externes sont-elles préférées pour exposer les zones du Data Lake ?
   Réponse indicative : Elles permettent à Hive de référencer des données gérées par le Data Lake sans en devenir propriétaire.

## À retenir

Hive transforme des fichiers HDFS en tables SQL grâce au metastore.

Les points importants de cette séance sont :

- une base Hive organise les tables d'un projet ou d'une équipe ;
- une table externe référence des données existantes sans les posséder ;
- une partition Hive correspond souvent à un sous-dossier HDFS ;
- `ALTER TABLE ADD PARTITION` ajoute une partition précise ;
- `MSCK REPAIR TABLE` découvre les partitions déjà présentes dans l'arborescence ;
- les formats ORC et Parquet sont adaptés aux analyses SQL ;
- filtrer sur les colonnes de partition réduit les données lues ;
- les zones `raw`, `processed` et `audit` n'ont pas le même rôle dans le projet fil rouge.
