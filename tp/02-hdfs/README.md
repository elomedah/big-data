# TP 02 - HDFS : chargement des données, administration et réplication

## Objectifs

À la fin de ce TP, vous devez être capable de :

- comprendre le rôle de HDFS dans une architecture Hadoop ;
- charger des données dans HDFS ;
- organiser des répertoires dans un Data Lake ;
- consulter les métadonnées HDFS ;
- analyser la répartition et la réplication des blocs ;
- modifier le facteur de réplication d’un fichier ;
- expliquer les choix d’organisation des zones `raw`, `archive`, `processed` et `audit`.

## Contexte

Le projet fil rouge porte sur une plateforme de stockage à froid destinée à conserver plusieurs années de logs techniques dans un contexte inspiré du règlement DORA.

Dans ce TP, vous allez utiliser HDFS pour simuler les premières étapes d’un Data Lake :

- réception de données brutes ;
- structuration des répertoires ;
- chargement de fichiers ;
- vérification de la réplication ;
- première réflexion sur la gouvernance des zones.

## Prérequis

Vous devez être connecté au gateway Hadoop avec votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Chargez l’environnement Hadoop.

```bash
source /etc/profile.d/hadoop.sh
```

Vérifiez que HDFS répond.

```bash
hdfs dfs -ls /
hdfs dfsadmin -report
```

## Session d’onboarding HDFS - Commandes usuelles

Cette session reprend les commandes HDFS les plus courantes. Elle sert de prise en main avant les exercices guidés du TP.

Référence utilisée : `https://github.com/elomedah/iris-big-data/blob/master/TP-hadoop/02-usual-command-hadoop.md`

### Deux syntaxes possibles

Hadoop accepte généralement deux syntaxes.

```bash
hadoop fs <commande>
hdfs dfs <commande>
```

La commande `hadoop fs` peut cibler plusieurs systèmes de fichiers compatibles avec Hadoop, par exemple HDFS, un système local ou un stockage objet compatible.

La commande `hdfs dfs` cible directement HDFS. Dans ce TP, nous utiliserons principalement `hdfs dfs`.

### Créer un dossier dans HDFS

Créer un dossier simple.

```bash
hdfs dfs -mkdir /user/$USER/onboarding
```

Créer un sous-dossier même si le dossier parent n’existe pas encore.

```bash
hdfs dfs -mkdir -p /user/$USER/onboarding/data/input
```

### Lister le contenu d’un dossier

Lister un dossier.

```bash
hdfs dfs -ls /user/$USER
```

Lister récursivement une arborescence.

```bash
hdfs dfs -ls -R /user/$USER/onboarding
```

### Charger un fichier local dans HDFS

Créer un fichier local.

```bash
echo "première ligne HDFS" > onboarding.txt
echo "deuxième ligne HDFS" >> onboarding.txt
```

Charger le fichier dans HDFS.

```bash
hdfs dfs -put onboarding.txt /user/$USER/onboarding/data/input/
```

La commande équivalente suivante peut aussi être utilisée.

```bash
hdfs dfs -copyFromLocal onboarding.txt /user/$USER/onboarding/data/input/
```

### Afficher le contenu d’un fichier HDFS

```bash
hdfs dfs -cat /user/$USER/onboarding/data/input/onboarding.txt
```

### Copier un fichier dans HDFS

```bash
hdfs dfs -mkdir -p /user/$USER/onboarding/data/copy
hdfs dfs -cp /user/$USER/onboarding/data/input/onboarding.txt /user/$USER/onboarding/data/copy/
```

### Déplacer ou renommer un fichier dans HDFS

```bash
hdfs dfs -mv /user/$USER/onboarding/data/copy/onboarding.txt /user/$USER/onboarding/data/copy/onboarding-renamed.txt
```

### Exporter un fichier HDFS vers le système local

```bash
hdfs dfs -get /user/$USER/onboarding/data/input/onboarding.txt ./onboarding-from-hdfs.txt
```

La commande équivalente suivante peut aussi être utilisée.

```bash
hdfs dfs -copyToLocal /user/$USER/onboarding/data/input/onboarding.txt ./onboarding-from-hdfs-copy.txt
```

### Afficher l’aide d’une commande

Afficher l’aide générale.

```bash
hdfs dfs -help
```

Afficher l’aide d’une commande précise.

```bash
hdfs dfs -help stat
```

### Nettoyer les fichiers de l’onboarding

Supprimer les fichiers locaux.

```bash
rm -f onboarding.txt onboarding-from-hdfs.txt onboarding-from-hdfs-copy.txt
```

Supprimer le dossier HDFS de l’onboarding.

```bash
hdfs dfs -rm -r -f /user/$USER/onboarding
```


## Exercice 1 - Comprendre l’architecture HDFS

Répondez aux questions suivantes.

1. Quel est le rôle du NameNode ?
2. Quel est le rôle des DataNodes ?
3. Pourquoi HDFS découpe-t-il les fichiers en blocs ?
4. Pourquoi HDFS réplique-t-il les blocs ?
5. Quels sont les avantages et les limites d’un système de fichiers distribué par rapport à un système de fichiers local ?
6. Pourquoi le NameNode est-il un composant critique de HDFS ?
7. Quels risques apparaissent si les métadonnées HDFS sont perdues ?
8. En production, quelles stratégies peut-on mettre en place pour limiter ce risque ?
9. Pourquoi HDFS est-il adapté aux gros fichiers mais moins adapté à un très grand nombre de petits fichiers ?

## Exercice 2 - Préparer un espace utilisateur

Créez votre espace personnel dans HDFS.

```bash
hdfs dfs -mkdir -p /user/$USER
```

Vérifiez les droits.

```bash
hdfs dfs -ls /user
hdfs dfs -ls /user/$USER
```

Créez une arborescence de travail.

```bash
hdfs dfs -mkdir -p /user/$USER/tp02/input
hdfs dfs -mkdir -p /user/$USER/tp02/output
hdfs dfs -mkdir -p /user/$USER/tp02/tmp
```

Vérifiez l’arborescence.

```bash
hdfs dfs -ls -R /user/$USER/tp02
```

Répondez aux questions suivantes.

1. À quoi sert le dossier `/user/$USER` ?
2. Pourquoi est-il important que chaque étudiant travaille dans son propre espace ?
3. Quels problèmes peuvent apparaître si tous les utilisateurs écrivent dans le même dossier ?

## Exercice 3 - Créer et charger des données

Créez un fichier local représentant des logs applicatifs.

```bash
cat > logs-applications.csv <<'EOF'
timestamp,application,level,message
2026-01-10T10:00:00Z,payment-api,INFO,service started
2026-01-10T10:01:12Z,payment-api,WARN,slow response time
2026-01-10T10:02:18Z,auth-service,ERROR,invalid token
2026-01-10T10:03:44Z,core-banking,INFO,batch completed
2026-01-10T10:04:02Z,payment-api,ERROR,database timeout
EOF
```

Affichez le fichier local.

```bash
cat logs-applications.csv
```

Chargez le fichier dans HDFS dans le repertoire /user/$USER/tp02/input/.

```bash
hdfs dfs à vous de compléter 
```

Vérifiez que le fichier est présent.

```bash
hdfs dfs à vous de compléter 
```


## Exercice 4 - Manipuler les fichiers dans HDFS

Copiez le fichier dans un autre dossier HDFS par exemple /user/$USER/tp02/tmp/.

```bash
hdfs dfs à vous de compléter 
```

Renommez la copie en logs-applications-copy.csv

```bash
hdfs dfs à vous de compléter 
```

Affichez la taille des fichiers.

```bash
hdfs dfs -du -h /user/$USER/tp02
```

Affichez l’arborescence complète de /user/$USER/tp02.

```bash
hdfs dfs à vous de compléter 
```

Supprimez la copie logs-applications-copy.csv

```bash
hdfs dfs à vous de compléter 
```


## Exercice 5 - Observer les blocs et la réplication

Affichez les informations détaillées du fichier.

```bash
hdfs dfs -ls /user/$USER/tp02/input/logs-applications.csv
```

Analysez les blocs avec `fsck`.

```bash
hdfs fsck /user/$USER/tp02/input/logs-applications.csv -files -blocks -locations
```

Répondez aux questions suivantes.

1. Combien de blocs contient le fichier ?
2. Sur quels DataNodes les blocs sont-ils stockés ?
3. Quel est le facteur de réplication affiché ?
4. Pourquoi un petit fichier n’utilise-t-il pas forcément toute la taille d’un bloc HDFS ?
5. Quel est l’impact du facteur de réplication sur la tolérance aux pannes ?
6. Quel est l’impact du facteur de réplication sur le coût de stockage ?
7. Pourquoi un facteur de réplication élevé n’est-il pas toujours une bonne décision ?
8. Comment choisiriez-vous le facteur de réplication pour des logs critiques, des données temporaires et des données archivées ?

## Exercice 6 - Modifier la réplication

Affichez le facteur de réplication actuel.

```bash
hdfs dfs -stat %r /user/$USER/tp02/input/logs-applications.csv
```

Modifiez le facteur de réplication à `2`.

```bash
hdfs dfs -setrep -w 2 /user/$USER/tp02/input/logs-applications.csv
```

Vérifiez le résultat.

```bash
hdfs dfs -stat %r /user/$USER/tp02/input/logs-applications.csv
hdfs fsck /user/$USER/tp02/input/logs-applications.csv -files -blocks -locations
```

Remettez le facteur de réplication à `3`.

```bash
hdfs dfs -setrep -w 3 /user/$USER/tp02/input/logs-applications.csv
```

Répondez aux questions suivantes.

1. Que signifie l’option `-w` dans la commande `setrep` ?
2. Pourquoi la réplication peut-elle prendre du temps ?
3. Que se passe-t-il si le facteur demandé est supérieur au nombre de DataNodes disponibles ?
4. Pourquoi certaines organisations peuvent choisir des facteurs de réplication différents selon les zones du Data Lake ?

## Exercice 7 - Lire l’état du cluster HDFS

Affichez le rapport HDFS.

```bash
hdfs dfsadmin -report
```

Ouvrez aussi l’interface NameNode.

```text
http://<gateway_public_ip>:9870
```

Répondez aux questions suivantes.

1. Combien de DataNodes sont actifs ?
2. Quelle est la capacité totale du cluster ?
3. Quelle est la capacité utilisée ?
4. Quelle est la capacité restante ?
5. Y a-t-il des DataNodes indisponibles ?
6. Quels indicateurs HDFS surveilleriez-vous en priorité en production ?
7. Comment détecteriez-vous un risque de saturation du stockage ?
8. Pourquoi la capacité brute du cluster est-elle différente de la capacité utile ?
9. Quel lien faites-vous entre réplication, disponibilité et capacité réellement exploitable ?

## Exercice 8 - Organiser le Data Lake du projet

Le projet fil rouge utilise les zones suivantes :

```text
/datalake/raw
/datalake/archive
/datalake/processed
/datalake/audit
```

Dans votre espace personnel, créez une version de travail de cette organisation.

Description des zones :

- `/datalake/raw` : zone d’atterrissage des données brutes. Les fichiers y sont déposés dans leur format d’origine, sans transformation métier. Cette zone doit permettre de revenir à la donnée initiale en cas d’erreur de traitement.
- `/datalake/archive` : zone de conservation longue durée. Elle contient les données historisées qui doivent être gardées pour des raisons réglementaires, contractuelles ou d’audit. L’accès y est généralement plus contrôlé et les données y sont rarement modifiées.
- `/datalake/processed` : zone des données transformées, nettoyées ou enrichies. Elle contient les résultats produits à partir de la zone `raw`, par exemple des données normalisées, agrégées ou prêtes pour l’analyse.
- `/datalake/audit` : zone dédiée aux traces de contrôle. Elle peut contenir les journaux d’ingestion, les rapports de qualité, les preuves de traitement, les empreintes de fichiers, les dates de chargement et les informations utiles pour vérifier la conformité.

```bash
hdfs dfs -mkdir -p /user/$USER/datalake/raw
hdfs dfs -mkdir -p /user/$USER/datalake/archive
hdfs dfs -mkdir -p /user/$USER/datalake/processed
hdfs dfs -mkdir -p /user/$USER/datalake/audit
```

Créez une organisation par source et par date dans la zone `raw`.

```bash
hdfs dfs -mkdir -p /user/$USER/datalake/raw/application_logs/year=2026/month=01/day=10
```

Chargez le fichier de logs dans cette zone.

```bash
hdfs dfs -put -f logs-applications.csv /user/$USER/datalake/raw/application_logs/year=2026/month=01/day=10/
```

Vérifiez l’arborescence.

```bash
hdfs dfs -ls -R /user/$USER/datalake
```

Répondez aux questions suivantes.

1. Pourquoi séparer les zones `raw`, `archive`, `processed` et `audit` ?
2. Quelles données doivent rester dans la zone `raw` ?
3. Quelle différence faites-vous entre `raw` et `archive` ?
4. Que devrait contenir la zone `processed` ?
5. Que devrait contenir la zone `audit` ?
6. Pourquoi organiser les données par source et par date ?
7. Quels noms de répertoires éviteriez-vous dans un Data Lake professionnel ?
8. Comment garantir que les données `raw` restent immuables ?
9. Quels droits d’accès donneriez-vous aux étudiants, aux administrateurs, aux traitements automatiques et aux auditeurs ?
10. Quelles métadonnées doivent accompagner chaque fichier chargé dans le Data Lake ?
11. Comment géreriez-vous la rétention des données sur plusieurs années ?
12. Comment prouver qu’un fichier n’a pas été modifié depuis son ingestion ?

## Nettoyage

Supprimez les fichiers locaux créés pendant le TP.

```bash
rm -f logs-applications.csv
```

Supprimez votre dossier de test HDFS si l’enseignant le demande.

```bash
hdfs dfs -rm -r -f /user/$USER/tp02
```

Ne supprimez pas votre dossier `/user/$USER/datalake` sans consigne explicite : il pourra servir de base pour les séances suivantes.

## À retenir

HDFS est conçu pour stocker de gros volumes de données de manière distribuée et tolérante aux pannes.

Les points importants de cette séance sont :

- la distinction entre fichiers locaux et fichiers HDFS ;
- la structuration des répertoires ;
- le chargement de données ;
- la réplication ;
- la surveillance de l’état du cluster ;
- l’organisation initiale du Data Lake du projet.
