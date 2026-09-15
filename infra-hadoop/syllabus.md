# Module : Hadoop, HDFS, YARN, MapReduce, Hive & HBase

## Syllabus - Master 2 Big Data / Data Engineering

**Volume horaire :** 28 h

-   **7 séances de Cours / Travaux Pratiques (3h30 chacune)**
-   **1 séance finale de Projet (3h30)**

------------------------------------------------------------------------

# Projet fil rouge

## Contexte

Le projet est basé sur le **Digital Operational Resilience Act (DORA) --
Règlement (UE) 2022/2554**.

-   Adoption : **14 décembre 2022**
-   Entrée en application : **17 janvier 2025**

Le module porte sur la conception d'une **plateforme de stockage à froid
(Cold Storage)** destinée à archiver plusieurs années de journaux
techniques d'une institution financière.

Les plateformes de monitoring temps réel (ex. Elasticsearch) sont
considérées comme **hors périmètre** du projet. Elles servent uniquement
à contextualiser l'architecture globale.

------------------------------------------------------------------------

# Organisation du module

## Séance 1 - Introduction au Big Data et découverte de Hadoop

### Cours

-   Les 5V du Big Data
-   Scale Up vs Scale Out
-   Architectures distribuées
-   Présentation de Hadoop
-   HDFS, YARN, MapReduce, Hive et HBase
-   Cas d'usage industriels
-   Présentation du règlement DORA
-   Présentation du projet fil rouge

### Démonstration

-   Découverte de la machine virtuelle Cloudera
-   Présentation des interfaces Web
-   Découverte des services Hadoop
-   Navigation dans HDFS

### TP

-   Prise en main de l'environnement
-   Démarrage du cluster
-   Vérification des services

### Projet

-   Présentation du cahier des charges
-   Découverte des jeux de données

------------------------------------------------------------------------

## Séance 2 - HDFS

### Cours

-   Architecture HDFS
-   NameNode
-   DataNode
-   Secondary NameNode
-   Blocs
-   Réplication
-   Pipeline d'écriture
-   Tolérance aux pannes

### TP

-   Chargement des données
-   Administration HDFS
-   Gestion de la réplication

### Projet

-   Organisation du Data Lake
-   Zones Raw / Archive / Processed / Audit

------------------------------------------------------------------------

## Séance 3 - YARN

### Cours

-   Architecture YARN
-   ResourceManager
-   NodeManager
-   ApplicationMaster
-   Containers
-   Scheduling
-   Allocation CPU/Mémoire

### TP

-   Exécution de jobs
-   Monitoring
-   Analyse des ressources

### Projet

-   Dimensionnement du cluster

------------------------------------------------------------------------

## Séance 4 - Traitement distribué :  MapReduce  et Introduction à Spark

### Cours

-   Paradigme MapReduce (Mapper, Reducer, Shuffle, Sort, Combiner, Partitioner, Driver)
-   Limites de MapReduce
-   Pourquoi MapReduce est aujourd'hui principalement étudié pour comprendre les fondements du calcul distribué
-   Nouveaux framework de traitement de données : Spark

### TP

-   WordCount et Comptage de fréquences
-   Somme et Moyenne
-   Configuration Spark

### Projet

-   Premiers traitements distribués

------------------------------------------------------------------------

## Séance 5 - Spark : Cas d'usage DORA

### Cours

-   Traitements distribués
-   DataFrame vs DataSet
-   Transformation vs Action 
-   Analyse des logs et performances


### TP

-   Nombre d'incidents par jour
-   Top erreurs
-   Statistiques par application
-   Agrégations

### Projet

-   Production des indicateurs d'audit

------------------------------------------------------------------------

## Séance 6 - Hive

### Cours

-   HiveQL
-   Metastore
-   Tables internes / externes
-   Partitions
-   Bucketing
-   ORC
-   Parquet

### TP

-   Création des tables
-   Chargement des données
-   Requêtes analytiques
-   Optimisation

### Projet

-   Construction du Data Warehouse

------------------------------------------------------------------------

## Séance 7 - HBase et intégration

### Cours

-   Architecture HBase
-   RowKey
-   Familles de colonnes
-   Versionnement

### TP

-   Création des tables
-   Lecture
-   Scan
-   Filtres

### Projet

-   Intégration HDFS, MapReduce, Hive, HBase
-   Validation fonctionnelle
-   Préparation de la soutenance

------------------------------------------------------------------------

## Séance 8 - Projet final

Chaque équipe présente :

-   l'architecture proposée ;
-   l'organisation du stockage à froid ;
-   les traitements Spark ;
-   les analyses Hive ;
-   le modèle HBase ;
-   les choix techniques ;
-   les limites et perspectives.

------------------------------------------------------------------------

# Livrables

-   Architecture technique
-   Scripts HDFS
-   Code MapReduce
-   Scripts Hive
-   Modèle HBase
-   Rapport technique
-   Soutenance

------------------------------------------------------------------------

# Compétences visées

À l'issue du module, l'étudiant sera capable de :

-   Concevoir une architecture Hadoop.
-   Mettre en œuvre un Data Lake de stockage à froid.
-   Administrer HDFS et YARN.
-   Développer des traitements MapReduce.
-   Construire un Data Warehouse avec Hive.
-   Concevoir un modèle HBase.
-   Justifier une architecture répondant à un contexte réglementaire tel
    que DORA.
