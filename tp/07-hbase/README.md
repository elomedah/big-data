# TP 07 - HBase : accès par clé, versionnement et intégration DORA

## Objectifs

À la fin de ce TP, vous devez être capable de :

- expliquer pourquoi HBase existe dans l'écosystème Hadoop ;
- distinguer les usages de HDFS, Hive, Spark et HBase ;
- comprendre les notions de table, RowKey, famille de colonnes, qualifier, cellule et version ;
- créer des tables HBase adaptées à des accès par clé ;
- insérer, lire, scanner et filtrer des données avec `hbase shell` ;
- concevoir une RowKey pour éviter les points chauds ;
- utiliser le versionnement pour conserver l'historique d'un état ;
- proposer un modèle HBase utile au projet fil rouge DORA ;
- identifier les limites de HBase pour l'archivage et l'analyse globale.

## Pourquoi HBase ?

HBase est une base NoSQL distribuée orientée colonnes, construite au-dessus de HDFS.

HDFS est excellent pour stocker de gros fichiers, mais il n'est pas conçu pour faire des lectures et écritures aléatoires ligne par ligne. Hive permet d'interroger des fichiers avec SQL, mais il est plutôt adapté aux analyses batch. Spark permet de transformer de gros volumes, mais il n'est pas une base de données de consultation opérationnelle.

HBase répond à un autre besoin : retrouver rapidement une ligne ou un petit ensemble de lignes à partir d'une clé.

Dans une architecture DORA, HBase peut servir à :

- retrouver rapidement l'état d'un incident par identifiant ;
- consulter les événements récents d'une application ;
- maintenir un index technique vers des fichiers archivés dans HDFS ;
- exposer des indicateurs opérationnels pré-calculés ;
- conserver plusieurs versions d'un statut ou d'une preuve de contrôle.

HBase ne remplace pas le Data Lake. Les fichiers bruts et les preuves complètes restent dans HDFS. HBase sert plutôt de couche d'accès rapide et d'indexation.

## Positionnement dans le projet fil rouge

Dans le projet DORA :

- HDFS conserve les logs bruts, les archives et les preuves ;
- Spark transforme les logs et produit des indicateurs ;
- Hive expose les données traitées pour les analyses SQL ;
- HBase permet des recherches ciblées par clé, par application, par incident ou par date récente.

Un bon usage de HBase commence toujours par les questions d'accès :

- quelle clé connaît l'utilisateur au moment de la recherche ?
- faut-il lire une seule ligne, une plage de lignes ou toute une table ?
- quelle fraîcheur de donnée est attendue ?
- combien de versions d'un état faut-il garder ?
- quelles données doivent rester dans HDFS plutôt que dans HBase ?

## Prérequis

Vous devez être connecté au gateway Hadoop avec votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Chargez les environnements Hadoop et HBase.

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/hbase.sh
```

Vérifiez que HDFS et HBase répondent.

```bash
hdfs dfs -ls /
hbase version
hbase shell
```

Dans `hbase shell`, testez le statut du cluster.

```ruby
status
version
whoami
exit
```

Interfaces utiles :

```text
HBase Master UI:      http://<gateway_public_ip>:16010
NameNode UI:          http://<gateway_public_ip>:9870
YARN ResourceManager: http://<gateway_public_ip>:8088
```

## Exercice 1 - Situer HBase dans l'architecture

Répondez aux questions suivantes.

1. Pourquoi HDFS n'est-il pas adapté aux lectures aléatoires ligne par ligne ?
2. Pourquoi Hive n'est-il pas le bon outil pour rechercher immédiatement un incident par identifiant ?
3. Quel besoin HBase couvre-t-il dans une plateforme Big Data ?
4. Pourquoi HBase utilise-t-il HDFS comme stockage sous-jacent ?
5. Pourquoi HBase n'est-il pas un remplacement d'une base relationnelle classique ?
6. Dans le projet DORA, quels accès rapides pourraient justifier HBase ?
7. Quelles données doivent rester dans HDFS même si un index HBase existe ?

## Exercice 2 - Comprendre le modèle de données HBase

HBase stocke les données sous forme de cellules identifiées par :

```text
RowKey + famille de colonnes + qualifier + timestamp
```

Exemple logique :

```text
RowKey:       app#payment-api#20260115#000001
Famille:      event
Qualifier:    level
Valeur:       ERROR
Timestamp:    version de la cellule
```

Les familles de colonnes sont définies à la création de la table. Les qualifiers peuvent être ajoutés librement ensuite.

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre une famille de colonnes et un qualifier ?
2. Pourquoi faut-il choisir les familles de colonnes avec soin ?
3. Pourquoi la RowKey est-elle centrale dans HBase ?
4. Pourquoi HBase trie-t-il les lignes par RowKey ?
5. Pourquoi une mauvaise RowKey peut-elle créer un point chaud ?
6. Quel lien faites-vous entre RowKey et performance de lecture ?

## Exercice 3 - Démarrer `hbase shell`

Démarrez le shell.

```bash
hbase shell
```

Listez les tables existantes.

```ruby
list
```

Créez un namespace personnel. Remplacez `identifiant` par votre identifiant.

```ruby
create_namespace 'dora_identifiant'
list_namespace
```

Répondez aux questions suivantes.

1. À quoi sert un namespace HBase ?
2. Pourquoi chaque étudiant doit-il utiliser son propre namespace ?
3. Quel problème apparaîtrait si tout le monde créait les mêmes tables dans le namespace `default` ?

## Exercice 4 - Créer une table d'événements applicatifs

Créez une table pour indexer des événements applicatifs utiles au projet DORA.

```ruby
create 'dora_identifiant:application_events',
  { NAME => 'event', VERSIONS => 1 },
  { NAME => 'tech', VERSIONS => 1 },
  { NAME => 'audit', VERSIONS => 3 }
```

Vérifiez la table.

```ruby
list
describe 'dora_identifiant:application_events'
```

Familles proposées :

- `event` : données fonctionnelles de l'événement ;
- `tech` : métadonnées techniques de collecte ;
- `audit` : informations utiles pour la preuve et le contrôle.

Répondez aux questions suivantes.

1. Pourquoi séparer les colonnes en familles ?
2. Pourquoi la famille `audit` garde-t-elle plusieurs versions ?
3. Pourquoi ne pas créer une famille de colonnes pour chaque champ ?
4. Quels champs placeriez-vous dans `event`, `tech` et `audit` ?

## Exercice 5 - Insérer des événements

Insérez quelques événements. La RowKey suit le format :

```text
app_id#date#reverse_timestamp#request_id
```

Cette forme regroupe les événements par application et par date. Le timestamp inversé permet de lire plus facilement les événements récents en premier dans certains modèles.

```ruby
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'event:level', 'INFO'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'event:status_code', '200'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'event:response_time_ms', '120'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'tech:source_team', 'team_payments'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'tech:hdfs_path', '/user/identifiant/datalake/raw/team_payments/application_logs/year=2026/month=01/day=15/payments_logs.csv'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001', 'audit:ingestion_status', 'ACCEPTED'

put 'dora_identifiant:application_events', 'payment-api#20260115#9999999988#req-002', 'event:level', 'WARN'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999988#req-002', 'event:status_code', '200'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999988#req-002', 'event:response_time_ms', '920'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999988#req-002', 'tech:source_team', 'team_payments'
put 'dora_identifiant:application_events', 'payment-api#20260115#9999999988#req-002', 'audit:ingestion_status', 'ACCEPTED'

put 'dora_identifiant:application_events', 'auth-service#20260115#9999999982#req-101', 'event:level', 'ERROR'
put 'dora_identifiant:application_events', 'auth-service#20260115#9999999982#req-101', 'event:status_code', '401'
put 'dora_identifiant:application_events', 'auth-service#20260115#9999999982#req-101', 'event:response_time_ms', '95'
put 'dora_identifiant:application_events', 'auth-service#20260115#9999999982#req-101', 'tech:source_team', 'team_security'
put 'dora_identifiant:application_events', 'auth-service#20260115#9999999982#req-101', 'audit:ingestion_status', 'REVIEW_REQUIRED'
```

Répondez aux questions suivantes.

1. Quelles informations sont encodées dans la RowKey ?
2. Pourquoi la RowKey ne doit-elle pas être choisie au hasard ?
3. Quels avantages et limites voyez-vous dans cette RowKey ?
4. Pourquoi stocker le chemin HDFS du fichier source dans HBase ?
5. Pourquoi ne stockerait-on pas forcément le message complet du log dans HBase ?

## Exercice 6 - Lire par clé

Lisez une ligne complète.

```ruby
get 'dora_identifiant:application_events', 'payment-api#20260115#9999999991#req-001'
```

Lisez une seule famille.

```ruby
get 'dora_identifiant:application_events',
  'payment-api#20260115#9999999991#req-001',
  { COLUMN => 'event' }
```

Lisez une seule cellule.

```ruby
get 'dora_identifiant:application_events',
  'payment-api#20260115#9999999991#req-001',
  { COLUMN => 'event:level' }
```

Répondez aux questions suivantes.

1. Pourquoi `get` est-il efficace dans HBase ?
2. Quelle information faut-il connaître pour utiliser `get` ?
3. Pourquoi HBase est-il adapté à la consultation d'un incident connu ?
4. Pourquoi ce mode d'accès est-il différent d'une requête Hive ?

## Exercice 7 - Scanner une plage de lignes

Scannez les événements d'une application pour une date.

```ruby
scan 'dora_identifiant:application_events',
  {
    STARTROW => 'payment-api#20260115#',
    STOPROW => 'payment-api#20260116#'
  }
```

Limitez les colonnes lues.

```ruby
scan 'dora_identifiant:application_events',
  {
    STARTROW => 'payment-api#20260115#',
    STOPROW => 'payment-api#20260116#',
    COLUMNS => ['event:level', 'event:status_code', 'event:response_time_ms']
  }
```

Répondez aux questions suivantes.

1. Pourquoi le scan utilise-t-il `STARTROW` et `STOPROW` ?
2. Pourquoi cette requête fonctionne-t-elle bien avec la RowKey choisie ?
3. Que se passerait-il si la RowKey commençait par `request_id` ?
4. Pourquoi limiter les colonnes peut-il améliorer la lecture ?
5. Pourquoi faut-il éviter les scans complets sur de très grandes tables HBase ?

## Exercice 8 - Filtrer les événements

Utilisez un filtre sur la valeur du niveau.

```ruby
scan 'dora_identifiant:application_events',
  {
    COLUMNS => ['event:level', 'event:status_code'],
    FILTER => "SingleColumnValueFilter('event','level',=,'binary:ERROR')"
  }
```

Utilisez un filtre sur le préfixe de RowKey.

```ruby
scan 'dora_identifiant:application_events',
  {
    FILTER => "PrefixFilter('auth-service#20260115#')"
  }
```

Répondez aux questions suivantes.

1. Quelle différence faites-vous entre filtrer par RowKey et filtrer par valeur ?
2. Pourquoi un filtre par valeur peut-il rester coûteux ?
3. Pourquoi la RowKey doit-elle refléter les requêtes principales ?
4. Dans quel cas créeriez-vous une deuxième table HBase servant d'index ?

## Exercice 9 - Créer une table d'incidents

Les incidents sont de bons candidats pour HBase, car on veut souvent les retrouver rapidement par identifiant.

Créez une table dédiée.

```ruby
create 'dora_identifiant:incidents',
  { NAME => 'identity', VERSIONS => 1 },
  { NAME => 'state', VERSIONS => 5 },
  { NAME => 'links', VERSIONS => 1 },
  { NAME => 'audit', VERSIONS => 5 }
```

Insérez un incident.

```ruby
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'identity:app_id', 'payment-api'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'identity:criticality', 'high'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'state:status', 'OPEN'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'state:owner_team', 'team_payments'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'links:first_event_rowkey', 'payment-api#20260115#9999999988#req-002'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'links:hdfs_evidence_path', '/user/identifiant/datalake/audit/spark/daily_team_metrics_parquet/event_date=2026-01-15'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'audit:last_update_reason', 'incident detected from slow response'
```

Lisez l'incident.

```ruby
get 'dora_identifiant:incidents', 'incident#20260115#INC-0001'
```

Répondez aux questions suivantes.

1. Pourquoi une table `incidents` est-elle pertinente pour DORA ?
2. Pourquoi stocker des liens vers HDFS plutôt que toutes les preuves dans HBase ?
3. Quelle différence faites-vous entre `identity`, `state`, `links` et `audit` ?
4. Quels autres champs ajouteriez-vous pour suivre un incident réglementaire ?

## Exercice 10 - Utiliser le versionnement

Mettez à jour le statut de l'incident plusieurs fois.

```ruby
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'state:status', 'INVESTIGATING'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'audit:last_update_reason', 'analysis started'

put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'state:status', 'RESOLVED'
put 'dora_identifiant:incidents', 'incident#20260115#INC-0001', 'audit:last_update_reason', 'service recovered'
```

Lisez la dernière version.

```ruby
get 'dora_identifiant:incidents',
  'incident#20260115#INC-0001',
  { COLUMN => 'state:status' }
```

Lisez plusieurs versions.

```ruby
get 'dora_identifiant:incidents',
  'incident#20260115#INC-0001',
  { COLUMN => 'state:status', VERSIONS => 5 }
```

Répondez aux questions suivantes.

1. Pourquoi le versionnement est-il utile pour suivre le cycle de vie d'un incident ?
2. Quelle différence faites-vous entre une version HBase et une ligne d'historique métier explicite ?
3. Pourquoi faut-il limiter le nombre de versions conservées ?
4. Dans quel cas préféreriez-vous écrire chaque changement comme une nouvelle ligne ?

## Exercice 11 - Concevoir une table d'index d'audit

Créez une table qui sert d'index vers les preuves stockées dans HDFS.

```ruby
create 'dora_identifiant:audit_index',
  { NAME => 'proof', VERSIONS => 1 },
  { NAME => 'quality', VERSIONS => 3 },
  { NAME => 'lineage', VERSIONS => 1 }
```

Proposition de RowKey :

```text
control_date#control_name#application#run_id
```

Insérez une preuve d'audit.

```ruby
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'proof:hdfs_path', '/user/identifiant/datalake/processed/logs/daily_app_metrics_orc/event_date=2026-01-15/app_id=payment-api'
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'proof:format', 'ORC'
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'quality:row_count', '1'
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'quality:status', 'OK'
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'lineage:spark_application_id', 'application_0000000000000_0001'
put 'dora_identifiant:audit_index', '20260115#daily_app_metrics#payment-api#run-0001', 'lineage:source_path', '/user/identifiant/datalake/raw/team_payments/application_logs/year=2026/month=01/day=15'
```

Recherchez les preuves d'une date.

```ruby
scan 'dora_identifiant:audit_index',
  {
    STARTROW => '20260115#',
    STOPROW => '20260116#'
  }
```

Répondez aux questions suivantes.

1. Pourquoi une table d'index peut-elle accélérer un contrôle ?
2. Pourquoi la preuve complète reste-t-elle dans HDFS ?
3. Quelles métadonnées de lineage sont indispensables ?
4. Comment adapteriez-vous la RowKey pour rechercher d'abord par application ?
5. Faut-il une seule table d'index ou plusieurs tables selon les accès ? Justifiez.

## Exercice 12 - Éviter les mauvaises RowKey

Comparez ces RowKey possibles pour des événements :

```text
20260115#payment-api#req-001
payment-api#20260115#req-001
req-001
ERROR#20260115#payment-api#req-001
salt03#payment-api#20260115#req-001
```

Répondez aux questions suivantes.

1. Quelle RowKey est adaptée pour lire les événements d'une application sur une date ?
2. Quelle RowKey est adaptée pour retrouver un événement par `request_id` ?
3. Quelle RowKey risque de créer un point chaud si toutes les écritures arrivent sur la même date ?
4. Pourquoi préfixer par le niveau `ERROR` peut-il être dangereux ?
5. À quoi sert un préfixe de salage comme `salt03` ?
6. Quel compromis le salage introduit-il pour les scans ?
7. Quelle RowKey proposeriez-vous pour le projet DORA et pourquoi ?

## Exercice 13 - Comparer HBase, Hive et HDFS

Complétez le tableau suivant dans votre compte rendu.

```text
Besoin                                      | Outil recommandé | Justification
--------------------------------------------|------------------|--------------
Conserver les logs bruts pendant plusieurs années
Calculer des indicateurs quotidiens
Faire des requêtes SQL analytiques
Retrouver rapidement un incident par identifiant
Retrouver le chemin HDFS d'une preuve d'audit
Scanner tous les logs d'une année
Consulter le dernier statut d'un incident
Conserver les fichiers originaux immuables
```

Répondez aux questions suivantes.

1. Pourquoi HBase n'est-il pas l'outil principal pour scanner tous les logs d'une année ?
2. Pourquoi Hive est plus naturel pour les agrégations SQL ?
3. Pourquoi HDFS reste la source de vérité pour les fichiers archivés ?
4. Pourquoi HBase peut-il améliorer l'expérience de consultation opérationnelle ?

## Exercice 14 - Livrable projet HBase

Préparez un court livrable avec :

- trois cas d'usage DORA où HBase est pertinent ;
- deux cas où HBase n'est pas pertinent ;
- le schéma de vos tables HBase ;
- les familles de colonnes choisies ;
- les RowKey choisies ;
- les accès optimisés par chaque RowKey ;
- les limites du modèle proposé ;
- les données qui restent dans HDFS ;
- les requêtes `get` et `scan` principales ;
- une stratégie de versionnement pour les incidents.

Commandes utiles :

```ruby
list
describe 'dora_identifiant:application_events'
describe 'dora_identifiant:incidents'
describe 'dora_identifiant:audit_index'
scan 'dora_identifiant:audit_index', { LIMIT => 10 }
```

## Nettoyage

Ne supprimez les tables que si l'enseignant le demande.

```ruby
disable 'dora_identifiant:application_events'
drop 'dora_identifiant:application_events'

disable 'dora_identifiant:incidents'
drop 'dora_identifiant:incidents'

disable 'dora_identifiant:audit_index'
drop 'dora_identifiant:audit_index'
```

Si vous voulez supprimer le namespace, il doit être vide.

```ruby
drop_namespace 'dora_identifiant'
```

## À retenir

HBase est utile quand l'accès principal se fait par clé ou par plage de clés.

Les points importants de cette séance sont :

- HBase complète HDFS, Spark et Hive, mais ne les remplace pas ;
- la RowKey détermine fortement les performances ;
- les familles de colonnes doivent rester peu nombreuses et stables ;
- HBase trie les lignes par RowKey ;
- `get` est adapté à une recherche directe ;
- `scan` est adapté à une plage bien conçue ;
- les filtres ne compensent pas une mauvaise RowKey ;
- le versionnement peut aider à suivre l'évolution d'un état ;
- dans DORA, HBase est pertinent pour les incidents, index de preuves et consultations rapides ;
- les preuves complètes et les archives restent dans HDFS.
