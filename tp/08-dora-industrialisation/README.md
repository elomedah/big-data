# Projet 08 - Industrialisation du fil rouge DORA

Ce projet clôture la séquence Hadoop, Spark, Hive et HBase. Il ne s'agit plus
d'un TP guidé : les choix de conception, de traitement, de stockage et de
validation sont à produire par les étudiants.

Le projet reprend le contexte DORA des TP précédents, mais avec un volume de
données plus important, plus de référentiels, plus d'applications, plus de dates
et plus de colonnes.

## Objectif

Construire une chaîne Big Data complète permettant de :

- organiser des données volumineuses dans un Data Lake HDFS ;
- traiter et enrichir les données avec Spark ;
- exposer les résultats analytiques dans Hive ;
- proposer des accès rapides avec HBase ;
- produire des contrôles de qualité et des éléments d'audit ;
- justifier les choix techniques réalisés.

## Données fournies

Les données du projet sont fournies par l'enseignant sous forme d'une archive ou
d'un répertoire `datalake/`.

Liens des données :

| Jeu de données | Emplacement |
|---|---|
| Docker | `datalake/` |
| Cluster | `<lien_donnees_tp08_cluster>` |

Le répertoire à récupérer doit contenir au minimum :

| Répertoire | Contenu attendu |
|---|---|
| `datalake/raw/application_logs/` | logs applicatifs partitionnés par date |
| `datalake/reference/applications/` | référentiel des applications |
| `datalake/reference/teams/` | référentiel des équipes responsables |
| `datalake/reference/team_budgets/` | référentiel budgétaire par équipe |
| `datalake/reference/services/` | référentiel des services et endpoints |
| `datalake/reference/sla_contracts/` | objectifs SLA, disponibilité, RTO et RPO |
| `datalake/reference/deployments/` | versions et stratégies de déploiement |

Les logs contiennent notamment :

| Type d'information | Exemples de colonnes |
|---|---|
| Identification | `event_id`, `request_id`, `trace_id`, `session_id` |
| Temps | `event_ts`, `event_date`, `event_hour` |
| Application | `app_id`, `team_id`, `service_name`, `environment`, `region` |
| Technique | `endpoint`, `host`, `pod_name`, `dependency`, `build_version` |
| Mesures | `status_code`, `response_time_ms`, `bytes_in`, `bytes_out`, `retry_count` |
| Métier et qualité | `severity`, `error_code`, `is_sla_breach`, `message` |

Le référentiel budgétaire par équipe contient notamment :

| Type d'information | Exemples de colonnes |
|---|---|
| Identification | `team_id`, `budget_year`, `budget_domain` |
| Montants | `annual_budget`, `cloud_budget`, `run_budget`, `compliance_budget` |
| Analyse | `currency`, `run_budget_ratio` |

Le volume minimal du jeu de données est :

| Environnement | Volume minimal |
|---|---|
| Docker local | au moins 10 jours et 10 000 événements par jour |
| Cluster Hadoop | au moins 30 jours et 50 000 événements par jour |

Le jeu Docker fourni dans ce dépôt couvre actuellement :

| Période | Volume |
|---|---:|
| Décembre 2025 | 310 000 événements |
| Janvier 2026 | 310 000 événements |
| Février 2026 | 280 000 événements |

## Chargement initial attendu

Les étudiants doivent déposer le répertoire `datalake/` dans leur espace HDFS
utilisateur, en conservant l'organisation fournie.

Chemin cible attendu :

```text
/user/<identifiant>/datalake
```

Dans Docker, `<identifiant>` correspond généralement à `hadoop`. Sur le cluster,
il correspond au compte étudiant.

Le dépôt doit conserver les zones suivantes :

| Zone | Rôle |
|---|---|
| `raw` | données brutes fournies |
| `reference` | référentiels fournis |
| `processed` | résultats produits par les traitements Spark |
| `audit` | rejets, contrôles et traces d'exécution |

## Contraintes techniques

Le projet doit utiliser les composants suivants :

| Composant | Attendu |
|---|---|
| HDFS | stockage des zones `raw`, `reference`, `processed` et `audit` |
| Spark | traitements distribués, enrichissements, contrôles et agrégations |
| Hive | tables externes sur les données brutes, référentiels et résultats traités |
| HBase | accès rapides pour des recherches ciblées |

Les données brutes doivent rester conservées dans HDFS. Les traitements Spark ne
doivent pas écraser la zone `raw`.

## Attendus Spark

Les étudiants doivent concevoir une application Spark structurée. Elle doit au
minimum couvrir :

- lecture des logs partitionnés et des référentiels ;
- typage explicite des colonnes ;
- gestion des lignes invalides ;
- enrichissement des logs avec les référentiels ;
- calcul d'indicateurs opérationnels ;
- détection d'événements ou d'incidents à investiguer ;
- écriture des résultats dans un format colonne ;
- production d'un résumé d'exécution.

Les choix suivants doivent être justifiés :

| Sujet | Décision attendue |
|---|---|
| Schémas | colonnes, types, champs obligatoires |
| Partitionnement | colonnes retenues et justification |
| Format de sortie | Parquet, ORC ou autre format compatible |
| Qualité | règles de rejet et stockage des rejets |
| Performance | gestion du nombre de fichiers et des partitions Spark |
| Audit | traces conservées pour expliquer une exécution |

## Attendus Hive

Les étudiants doivent exposer les données utiles dans Hive avec des tables
externes. Le modèle Hive doit permettre :

- d'interroger les logs bruts ;
- d'interroger les référentiels ;
- d'analyser les résultats produits par Spark ;
- de filtrer efficacement par date et, lorsque pertinent, par application ou
  équipe ;
- de démontrer que les partitions Hive correspondent bien aux dossiers HDFS.

Les requêtes Hive livrées doivent montrer au minimum :

- le volume d'événements par jour ;
- les applications les plus en erreur ;
- les dépassements de SLA ;
- les indicateurs par équipe ;
- la différence entre une requête filtrée par partition et une requête non
  filtrée.

## Attendus HBase

Les étudiants doivent proposer un modèle HBase adapté à des consultations
rapides. HBase ne doit pas contenir une copie complète de toutes les données.

Le dossier doit expliquer :

- les cas d'accès retenus ;
- les tables HBase proposées ;
- les RowKey choisies ;
- les familles de colonnes ;
- les liens éventuels vers les fichiers HDFS ou les résultats Hive/Spark ;
- les limites du modèle choisi.

Les accès rapides peuvent concerner par exemple :

- la recherche d'un incident par identifiant ;
- le dernier statut connu d'une application ;
- la consultation des événements d'une application sur une période courte ;
- la recherche d'une requête par `request_id` ;
- l'identification rapide des dépassements SLA récents.

## Livrables

Chaque groupe doit rendre :

| Livrable | Contenu |
|---|---|
| Code | application Spark, scripts Hive, scripts HBase |
| Documentation | architecture, choix de partitionnement, schémas, limites |
| Résultats | chemins HDFS, tables Hive, exemples de requêtes, exemples HBase |
| Qualité | règles de contrôle, rejets, résumé d'exécution |
| Analyse | indicateurs observés et interprétation technique |
| Présentation | présentation synthétique et démonstration live de 10 minutes |

Le rendu doit permettre à un enseignant de relancer le projet sur Docker ou sur
le cluster à partir du répertoire `datalake/` fourni.

## Critères d'évaluation

| Critère | Points d'attention |
|---|---|
| Modélisation | cohérence des zones HDFS, schémas, tables Hive et tables HBase |
| Spark | qualité du code, typage, jointures, agrégations, gestion des erreurs |
| Performance | partitionnement, nombre de fichiers, filtres, choix des formats |
| Hive | tables externes correctes, partitions réparées, requêtes pertinentes |
| HBase | RowKey adaptées aux accès, familles sobres, absence de duplication massive |
| Traçabilité | audit d'exécution, rejets, liens vers les données produites |
| Démonstration | clarté de la présentation et capacité à montrer le projet en live en 10 minutes |
| Autonomie | capacité à justifier les choix sans suivre une recette |

## Point de départ

Le seul élément fourni aux étudiants est le jeu de données `datalake/`. Le reste
du projet est à concevoir et à implémenter dans la structure de leur choix, à
condition qu'elle soit cohérente et documentée.
