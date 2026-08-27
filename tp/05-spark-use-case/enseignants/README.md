# TP 05 - Spark avancé : cas d'usage logs applicatifs - Corrigé enseignants

Ce document reprend les questions du TP étudiant et propose des réponses
indicatives pour guider la correction. Les réponses peuvent varier selon les
choix d'architecture discutés en classe.

## Exercice 1 - Préparer les zones du Data Lake

1. Les sous-dossiers par équipe isolent les responsabilités, les droits, les
   volumes et les conventions de dépôt. Ils évitent aussi les collisions de noms.
2. L'organisation par date dans `raw` facilite la recherche, le retraitement et
   la lecture partielle des données dès leur arrivée.

## Exercice 2 - Créer des logs applicatifs multi-équipes

1. L'équipe source peut être déduite du chemin HDFS, par exemple avec
   `/raw/team_payments/...`, ou avec `input_file_name()` côté Spark.
2. Les contrôles attendus portent sur la présence du fichier, le format, l'en-tête,
   les colonnes obligatoires, les types de base, la date de dépôt et la taille.

## Exercice 3 - Créer des référentiels pour les jointures

1. Les logs sont des événements, les référentiels décrivent les applications.
   Les séparer évite de dupliquer des informations stables dans chaque ligne.
2. Si un `app_id` est absent du référentiel, la jointure produit des colonnes
   enrichies à `null`. La ligne doit être conservée mais signalée.

## Exercice 4 - Lire les données avec un schéma explicite

1. Un schéma explicite rend la lecture reproductible, évite les inférences
   coûteuses ou instables et force les types attendus.
2. `source_team` est extrait du chemin du fichier source avec une expression
   régulière appliquée à `input_file_name()`.

## Exercice 5 - Ajouter des colonnes métiers

1. Convertir `event_ts` en timestamp permet les tris, filtres, agrégations
   temporelles et contrôles de validité.
2. `event_date` sert aux agrégations quotidiennes et au partitionnement.
3. `is_error` et `is_warning` simplifient les agrégations avec `sum` et rendent
   les indicateurs plus lisibles.

## Exercice 6 - Réaliser des jointures avec les référentiels

1. La jointure `left` conserve tous les logs, même quand le référentiel est
   incomplet.
2. Une ligne avec `app_name` à `null` indique une application inconnue dans le
   référentiel.
3. Le `broadcast` est adapté ici car les référentiels sont petits et peuvent être
   envoyés à chaque executor.
4. Il devient dangereux si le référentiel est volumineux, car il peut saturer la
   mémoire des executors ou du driver.

## Exercice 7 - Agréger les indicateurs par application et par date

1. L'agrégation par `event_date` et `app_id` produit un grain quotidien par
   application, exploitable pour le suivi opérationnel.
2. `owner_team` vient du référentiel et désigne l'équipe responsable de
   l'application. `source_team` vient du chemin de dépôt et désigne le producteur
   du fichier.
3. Le taux d'erreur est comparable entre applications de volumes différents,
   contrairement au nombre brut d'erreurs.

## Exercice 8 - Sauvegarder en Parquet avec partitionnement

1. Partitionner par `event_date` permet de lire seulement les jours utiles.
2. Ajouter `app_id` accélère les requêtes ciblées sur une application, si la
   cardinalité reste raisonnable.
3. Parquet est colonne, typé et compressé. Il est plus efficace que CSV pour les
   lectures analytiques et conserve le schéma.

## Exercice 9 - Lire des données partitionnées

1. Les colonnes de partition apparaissent dans le schéma lu par Spark, même si
   elles sont encodées dans les dossiers HDFS.
2. Spark peut éviter certaines partitions grâce au partition pruning lorsque le
   filtre porte sur `event_date` ou `app_id`.

## Exercice 10 - Sauvegarder en ORC

1. Un format ligne stocke les colonnes d'une ligne ensemble. Un format colonne
   stocke les valeurs d'une même colonne ensemble.
2. Parquet et ORC sont adaptés à l'analytique car ils lisent seulement les
   colonnes nécessaires, compressent bien et stockent des métadonnées de schéma.

## Exercice 11 - Gérer les lignes rejetées

1. Supprimer les lignes invalides ferait perdre de la traçabilité et empêcherait
   l'analyse de la qualité des producteurs.
2. On peut ajouter `rejection_reason`, `rejection_ts`, `source_file`,
   `source_team`, `process_date` et `pipeline_run_id`.

## Exercice 12 - Repartition, coalesce et nombre de fichiers

1. `repartition` peut augmenter ou diminuer le nombre de partitions et déclenche
   un shuffle. `coalesce` réduit surtout le nombre de partitions avec moins de
   mouvement de données.
2. `coalesce(1)` force une seule sortie et peut créer un goulot d'étranglement
   mémoire, CPU et I/O sur de gros volumes.
3. Trop de petits fichiers surchargent le NameNode, ralentissent la planification
   des tâches et dégradent les lectures.

## Exercice 13 - Suivre et analyser le traitement

1. Le nombre de jobs dépend des actions exécutées : `show`, `count`, `write`,
   etc. Chaque action peut déclencher un ou plusieurs jobs.
2. Les actions déclenchent l'exécution car les transformations Spark sont
   évaluées paresseusement.
3. Les stages sont visibles dans Spark UI ou Spark History Server, onglet
   `Stages`.
4. Un shuffle apparaît souvent lors des jointures et agrégations. Dans l'UI, on
   le repère avec des stages séparés, des métriques `shuffle read/write` et
   parfois des stages marqués `skipped`.

### Note sur les skipped stages

`Skipped Stages` n'est pas une erreur. Spark indique qu'il a réutilisé un résultat
déjà disponible, par exemple un shuffle matérialisé par une action précédente.
Dans ce TP, c'est normal si plusieurs actions successives partagent le même
début de plan d'exécution.

## Exercice 14 - Réflexion d'architecture

1. Organiser `raw` par producteur, type de données et date :
   `/raw/<team>/<dataset>/year=YYYY/month=MM/day=DD/`.
2. Éviter les écrasements avec des droits HDFS, des noms uniques, des zones de
   dépôt par équipe et une politique d'append-only.
3. Gérer les logs tardifs par retraitement ciblé de partitions, date de
   traitement séparée et indicateurs recalculables.
4. La date d'événement vient du log. La date de traitement décrit l'exécution du
   pipeline.
5. Les métadonnées utiles sont `pipeline_run_id`, date de traitement, version du
   code, chemins lus, nombre de lignes lues, valides, rejetées et écrites.
6. La reproductibilité repose sur l'immutabilité de `raw`, la version du code,
   les paramètres d'exécution, les référentiels versionnés et les sorties
   historisées.
7. Les compromis portent sur le nombre de partitions, le coût de stockage, la
   facilité de lecture humaine, la performance et le niveau de détail d'audit.

## Exercice 15 - Structurer un projet Spark avec plusieurs fichiers Python

1. Séparer le code améliore la lisibilité, les tests, la maintenance et le
   travail en équipe.
2. `--py-files` distribue l'archive Python aux executors Spark pour rendre le
   package `log_pipeline` importable pendant le job.
3. Pour industrialiser le projet, ajouter tests, packaging, configuration par
   environnement, logs applicatifs, contrôle qualité, CI/CD, gestion des secrets
   et monitoring.
