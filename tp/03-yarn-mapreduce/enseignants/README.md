# TP 03 - YARN et premier traitement MapReduce - Corrigé enseignants

Ce document reprend le TP étudiant et place les réponses indicatives directement
sous les questions concernées. Les réponses peuvent varier légèrement selon
l'état du cluster, le nombre de workers actifs et les ressources exposées à YARN.

## Objectifs

À la fin de ce TP, vous devez être capable de :

- expliquer le rôle de YARN dans Hadoop ;
- identifier les composants ResourceManager, NodeManager, ApplicationMaster et containers ;
- consulter l’état des nœuds YARN ;
- suivre l’exécution d’une application YARN ;
- consulter les logs d’une application ;
- lancer un premier traitement MapReduce de type WordCount ;
- relier les notions de ressources, files d’attente et capacité à un contexte projet.

## Contexte

Dans le TP précédent, vous avez manipulé HDFS pour stocker des fichiers.

Dans ce TP, vous allez utiliser YARN pour exécuter un traitement distribué sur ces données. Le premier traitement sera volontairement simple : un comptage de mots avec MapReduce.

L’objectif n’est pas seulement de lancer une commande, mais de comprendre ce qui se passe dans le cluster :

- qui reçoit la demande d’exécution ;
- où les containers sont lancés ;
- comment suivre l’état d’une application ;
- où retrouver les logs ;
- comment interpréter les ressources utilisées.

## Prérequis

Vous devez être connecté au gateway Hadoop avec votre compte étudiant.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Chargez l’environnement Hadoop.

```bash
source /etc/profile.d/hadoop.sh
```

Vérifiez que HDFS et YARN répondent.

```bash
hdfs dfs -ls /
yarn node -list
yarn application -list
```

Interfaces utiles :

```text
YARN ResourceManager:    http://<gateway_public_ip>:8088
MapReduce HistoryServer: http://<gateway_public_ip>:19888
NameNode UI:             http://<gateway_public_ip>:9870
```

## Exercice 1 - Comprendre l’architecture YARN

YARN signifie Yet Another Resource Negotiator. C’est le gestionnaire de ressources de Hadoop.

Les principaux composants sont :

- `ResourceManager` : service central qui reçoit les demandes d’exécution et arbitre l’allocation des ressources ;
- `NodeManager` : agent présent sur les machines de calcul, responsable de l’exécution locale des containers ;
- `ApplicationMaster` : processus créé pour piloter une application donnée ;
- `Container` : unité d’exécution à laquelle YARN attribue de la mémoire et des vCPU.

Répondez aux questions suivantes.

1. Pourquoi Hadoop sépare-t-il le stockage HDFS et l’exécution YARN ?
   Réponse indicative : HDFS stocke les données durablement, YARN planifie l'exécution des traitements. Cette séparation permet à plusieurs moteurs de calcul d'utiliser les mêmes données.
2. Quel est le rôle du ResourceManager ?
   Réponse indicative : Le ResourceManager reçoit les demandes d'applications, choisit où allouer les containers et arbitre les ressources du cluster.
3. Quel est le rôle d’un NodeManager ?
   Réponse indicative : Le NodeManager tourne sur chaque worker, démarre les containers, surveille leur consommation et remonte l'état au ResourceManager.
4. Pourquoi chaque application possède-t-elle son propre ApplicationMaster ?
   Réponse indicative : L'ApplicationMaster pilote une application précise : il négocie les containers, suit les tâches et signale la réussite ou l'échec.
5. Quelle différence faites-vous entre un nœud du cluster, un container et une application ?
   Réponse indicative : Un nœud est une machine du cluster, un container est une allocation de CPU/mémoire sur un nœud, une application est un job complet soumis à YARN.
6. Quels problèmes peuvent apparaître si un utilisateur consomme trop de mémoire ou trop de vCPU ?
   Réponse indicative : Les autres utilisateurs peuvent être ralentis, les jobs peuvent rester en attente, échouer par manque de mémoire, ou saturer les workers.
7. Pourquoi un gestionnaire de ressources est-il indispensable dans un cluster partagé par plusieurs utilisateurs ?
   Réponse indicative : Il évite qu'un utilisateur monopolise le cluster et permet de partager les ressources avec des règles explicites.

## Exercice 2 - Explorer l’état du cluster YARN

Listez les nœuds YARN actifs.

```bash
yarn node -list
```

Listez tous les nœuds, y compris ceux qui ne sont pas actifs.

```bash
yarn node -list -all
```

Affichez les applications connues par YARN.

```bash
yarn application -list -appStates ALL
```

Ouvrez l’interface ResourceManager.

```text
http://<gateway_public_ip>:8088
```

Répondez aux questions suivantes.

1. Combien de NodeManagers sont visibles ?
   Réponse indicative : Sur le cluster tiny attendu, 3 NodeManagers actifs doivent être visibles. Sur un cluster large, le nombre dépend de `large_worker_count`.
2. Quelle est la mémoire totale disponible pour YARN ?
   Réponse indicative : La mémoire totale correspond à la somme de la mémoire exposée par les NodeManagers à YARN, après réserve système si elle est configurée.
3. Combien de vCPU sont visibles ?
   Réponse indicative : Le nombre de vCPU correspond à la somme des vcores exposés par les workers. Il peut être inférieur aux CPU physiques si YARN garde une réserve.
4. Y a-t-il des applications en cours d’exécution ?
   Réponse indicative : Cela dépend du moment. Avant le TP, il ne devrait pas y avoir d'application `RUNNING`, sauf si d'autres étudiants utilisent le cluster.
6. Pourquoi l’état des NodeManagers est-il important avant de lancer un traitement distribué ?
   Réponse indicative : Si des NodeManagers sont absents, perdus ou unhealthy, le parallélisme est réduit et certains jobs peuvent rester bloqués ou échouer.

## Exercice 3 - Explorer les files d’attente YARN

Affichez les informations de la file `default`.

```bash
yarn queue -status default
```

Affichez les applications présentes dans toutes les files.

```bash
yarn application -list -appStates ALL
```

Dans l’interface ResourceManager, ouvrez la partie liée au scheduler.

```text
http://<gateway_public_ip>:8088/cluster/scheduler
```

Répondez aux questions suivantes.

1. À quoi sert une file d’attente YARN ?
   Réponse indicative : Une file d'attente organise le partage des ressources entre groupes d'utilisateurs ou types de traitements.
2. Pourquoi peut-on vouloir séparer les ressources entre étudiants, enseignants et traitements automatiques ?
   Réponse indicative : Les étudiants, enseignants et traitements automatiques n'ont pas les mêmes priorités ni les mêmes garanties de service.
3. Quelle différence faites-vous entre capacité minimale, capacité maximale et ressources réellement utilisées ?
   Réponse indicative : La capacité minimale est une part garantie, la capacité maximale est une limite haute, les ressources utilisées sont la consommation réelle à un instant donné.
4. Dans un cluster partagé, pourquoi le scheduling est-il un sujet de gouvernance autant qu’un sujet technique ?
   Réponse indicative : Le scheduling traduit des choix d'organisation : priorité des cours, équité entre groupes, protection des traitements critiques et maîtrise des coûts.
5. Pour le projet DORA, quels traitements devraient être prioritaires : ingestion, archivage, audit, traitements analytiques ? Justifiez.
   Réponse indicative : Pour DORA, ingestion et audit sont généralement prioritaires car ils garantissent la disponibilité et la traçabilité des données. Les traitements analytiques peuvent souvent attendre.

## Exercice 4 - Préparer les données d’entrée MapReduce

Créez un dossier de travail HDFS.

```bash
hdfs dfs -mkdir -p /user/$USER/tp03/input
```

Créez un fichier local avec des lignes de logs simplifiées.

```bash
cat > logs-mapreduce.txt <<'EOF'
payment-api INFO service started
payment-api WARN slow response
auth-service ERROR invalid token
core-banking INFO batch completed
payment-api ERROR database timeout
auth-service INFO token refreshed
core-banking WARN delayed batch
payment-api INFO request completed
EOF
```

Ajoutez plus de lignes pour rendre le traitement plus visible.

```bash
for i in $(seq 1 1000); do cat logs-mapreduce.txt >> logs-mapreduce-large.txt; done
```

Chargez le fichier dans HDFS.

```bash
hdfs dfs -put -f logs-mapreduce-large.txt /user/$USER/tp03/input/
```

Vérifiez le chargement.

```bash
hdfs dfs -ls /user/$USER/tp03/input
hdfs dfs -du -h /user/$USER/tp03/input
```

Répondez aux questions suivantes.

1. Pourquoi le fichier d’entrée doit-il être dans HDFS avant de lancer MapReduce ?
   Réponse indicative : MapReduce lit les données depuis HDFS pour les rendre accessibles aux workers du cluster.
2. Pourquoi un moteur de traitement distribué doit-il connaître la localisation des blocs HDFS ?
   Réponse indicative : La localisation des blocs permet de rapprocher le calcul des données et de limiter les transferts réseau.
3. Que se passerait-il si le fichier d’entrée était uniquement présent sur le disque local du gateway ?
   Réponse indicative : Les workers ne verraient pas le fichier local du gateway. Le job échouerait ou ne pourrait être exécuté que depuis cette machine, ce qui perd l'intérêt du calcul distribué.

## Exercice 5 - Lancer un premier job MapReduce WordCount

Supprimez l’ancien dossier de sortie s’il existe.

```bash
hdfs dfs -rm -r -f /user/$USER/tp03/output-wordcount
```

Lancez le job MapReduce WordCount fourni avec Hadoop.

```bash
hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  wordcount \
  /user/$USER/tp03/input \
  /user/$USER/tp03/output-wordcount
```

Pendant l’exécution, ouvrez l’interface YARN.

```text
http://<gateway_public_ip>:8088
```

Vérifiez le résultat.

```bash
hdfs dfs -ls /user/$USER/tp03/output-wordcount
hdfs dfs -cat /user/$USER/tp03/output-wordcount/part-r-00000
```

Répondez aux questions suivantes.

1. Quel est l’identifiant de l’application YARN lancée ?
   Réponse indicative : L'identifiant a la forme `application_<timestamp>_<numéro>`.
2. Quel est le nom de l’application affiché dans YARN ?
   Réponse indicative : Le nom affiché est généralement `word count` ou un nom proche selon la version Hadoop.
3. Combien de temps le job a-t-il duré ?
   Réponse indicative : La durée dépend du cluster et de la charge. Sur un petit fichier, elle est souvent de quelques secondes à quelques dizaines de secondes.
4. Quel fichier contient le résultat final ?
   Réponse indicative : Le résultat est dans `/user/$USER/tp03/output-wordcount/part-r-00000`.
6. Quels mots apparaissent le plus souvent dans le résultat ?
   Réponse indicative : Les mots les plus fréquents devraient être ceux répétés dans `logs-mapreduce.txt`, par exemple `payment-api`, `INFO`, `ERROR`, `WARN`, selon le contenu exact.

## Exercice 6 - Suivre une application YARN

Listez les applications terminées.

```bash
yarn application -list -appStates FINISHED
```

Récupérez l’identifiant de votre application, par exemple :

```text
application_XXXXXXXXXXXXX_0001
```

Affichez son statut.

```bash
yarn application -status <application_id>
```

Affichez ses logs.

```bash
yarn logs -applicationId <application_id>
```

Ouvrez aussi le MapReduce HistoryServer.

```text
http://<gateway_public_ip>:19888
```

Répondez aux questions suivantes.

1. Où voyez-vous l’état final de l’application ?
   Réponse indicative : L'état final est visible avec `yarn application -status`, dans l'interface ResourceManager et dans le HistoryServer après terminaison.
2. Où voyez-vous les logs du job ?
   Réponse indicative : Les logs sont accessibles avec `yarn logs -applicationId <application_id>` et via les liens du HistoryServer si l'agrégation est active.
3. Quelle différence faites-vous entre l’interface ResourceManager et le HistoryServer ?
   Réponse indicative : Le ResourceManager montre surtout l'état courant et récent des applications. Le HistoryServer conserve les informations détaillées des jobs terminés.
4. Pourquoi les logs sont-ils essentiels pour diagnostiquer un échec de traitement ?
   Réponse indicative : Les logs donnent la cause technique : fichier absent, droits insuffisants, mémoire dépassée, exception applicative ou problème de container.

## Exercice 7 - Simuler une erreur et lire les logs

### Erreur 1

Lancez volontairement un job avec un dossier d’entrée inexistant.

```bash
hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  wordcount \
  /user/$USER/tp03/input-does-not-exist \
  /user/$USER/tp03/output-error
```

Répondez aux questions suivantes.

1. Quel message d’erreur est affiché dans le terminal ?
   Réponse indicative : Le message attendu mentionne que la ressource demandée dépasse l'allocation maximale, par exemple une mémoire ou des vcores supérieurs à `yarn.scheduler.maximum-allocation-*`.
2. L’application apparaît-elle dans YARN ?
   Réponse indicative : Selon la configuration, le job peut être refusé immédiatement ou rester en attente si aucune allocation compatible n'est disponible.
3. Est-ce une erreur d’entrée, une erreur de ressources, une erreur de code ou une erreur système ?
   Réponse indicative : Dans l'exemple, les deux peuvent poser problème : `4096 MB` dépasse une limite à `2048 MB`, et `2 vcores` dépasse une limite à `1 vcore`.
4. Pourquoi est-il important de distinguer ces catégories d’erreurs ?
   Réponse indicative : Pour garantir l'équité, empêcher la saturation du cluster et éviter qu'un seul job bloque tous les autres.
5. Quelle démarche suivriez-vous pour diagnostiquer un job MapReduce échoué en production ?
   Réponse indicative : Diminuer `mapreduce.map.memory.mb`, `mapreduce.reduce.memory.mb`, `mapreduce.map.cpu.vcores` et `mapreduce.reduce.cpu.vcores` pour rester dans les limites autorisées.

## Exercice 9 - Lien avec le projet fil rouge

Dans le projet DORA, les traitements distribués peuvent servir à :

- compter des événements par application ;
- détecter des erreurs fréquentes ;
- produire des indicateurs quotidiens ;
- préparer des données pour Hive ;
- produire des preuves d’audit.

Répondez aux questions suivantes.

1. Quels traitements du projet devraient être lancés régulièrement sur YARN ?
   Réponse indicative : Les traitements réguliers peuvent inclure le comptage quotidien des événements par application, la détection des niveaux `ERROR` ou `WARN`, les agrégations par jour, la préparation de données pour Hive et la génération de rapports d'audit.
2. Quels traitements peuvent être exécutés en batch de nuit ?
   Réponse indicative : Les traitements lourds non urgents, comme les recomputations complètes, les enrichissements historiques, les contrôles qualité profonds ou la reconstruction de tables, sont adaptés au batch de nuit.
3. Quels traitements doivent être prioritaires en cas d’incident ?
   Réponse indicative : En cas d'incident, les traitements d'ingestion, de détection d'erreurs, de contrôle qualité et d'audit doivent passer avant les analyses exploratoires. L'objectif est de comprendre vite ce qui s'est passé et de préserver les preuves.
4. Quelles informations faut-il conserver pour prouver qu’un traitement a bien été exécuté ?
   Réponse indicative : Conserver l'identifiant YARN, l'heure de début et de fin, l'utilisateur, les paramètres, les chemins d'entrée et de sortie, le statut final, le nombre de lignes traitées, les compteurs MapReduce et les logs.
5. Comment organiseriez-vous les sorties MapReduce dans les zones `processed` et `audit` du Data Lake ?
   Réponse indicative : Les résultats métiers vont dans `processed`, par exemple `/user/$USER/datalake/processed/application_logs/year=2026/month=01/day=10/`. Les preuves d'exécution, logs de traitement, compteurs, statuts et contrôles vont dans `audit`, par exemple `/user/$USER/datalake/audit/mapreduce/wordcount/year=2026/month=01/day=10/`.
6. Quels risques apparaissent si les étudiants ou les traitements automatiques écrivent tous dans les mêmes dossiers de sortie ?
   Réponse indicative : Il y a des risques d'écrasement, de mélange de données, de droits mal maîtrisés, de résultats non reproductibles et de difficulté à attribuer les erreurs. En production, il faut isoler les sorties par utilisateur, application, date d'exécution et identifiant de job.

## Nettoyage

Supprimez les fichiers locaux créés pendant le TP.

```bash
rm -f logs-mapreduce.txt logs-mapreduce-large.txt
```

```bash
hdfs dfs -rm -r -f /user/$USER/tp03
```

## À retenir

YARN est le gestionnaire de ressources du cluster Hadoop. Il permet de partager CPU et mémoire entre plusieurs applications et plusieurs utilisateurs.

MapReduce est un modèle de traitement distribué fondamental. Même s’il est moins utilisé que Spark dans de nombreux contextes modernes, il reste utile pour comprendre les bases du calcul distribué :

- lecture distribuée ;
- mapper ;
- shuffle ;
- reducer ;
- écriture des résultats ;
- suivi des applications ;
- analyse des logs.
