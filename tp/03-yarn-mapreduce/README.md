# TP 03 - YARN et premier traitement MapReduce

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

Vous pouvez réaliser ce TP dans l'environnement Docker local du TP 01 ou sur le
gateway Hadoop du cours.

### Option A - Docker local

Démarrez l'environnement Docker du TP 01, puis entrez dans le conteneur avec
l'utilisateur `hadoop`.

```bash
cd tp/01-big-data-hadoop
docker compose up -d
docker exec -it --user hadoop tp-hadoop bash
```

Dans le conteneur, initialisez la variable `USER` et vérifiez que HDFS et YARN
répondent.

```bash
export USER=$(whoami)
hdfs dfs -ls /
yarn node -list
yarn application -list
```

Interfaces locales utiles :

```text
YARN ResourceManager:    http://localhost:8088
MapReduce HistoryServer: http://localhost:19888
NameNode UI:             http://localhost:9870
```

L'environnement Docker contient un seul NodeManager. Il permet d'observer le
fonctionnement de YARN et de lancer des jobs MapReduce, mais les exercices sur
la capacité du cluster ou les files d'attente doivent être interprétés comme une
version locale simplifiée.

### Option B - Gateway Hadoop du cours

Connectez-vous au gateway Hadoop avec votre compte étudiant.

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
2. Quel est le rôle du ResourceManager ?
3. Quel est le rôle d’un NodeManager ?
4. Pourquoi chaque application possède-t-elle son propre ApplicationMaster ?
5. Quelle différence faites-vous entre un nœud du cluster, un container et une application ?
6. Quels problèmes peuvent apparaître si un utilisateur consomme trop de mémoire ou trop de vCPU ?
7. Pourquoi un gestionnaire de ressources est-il indispensable dans un cluster partagé par plusieurs utilisateurs ?

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
Docker:  http://localhost:8088
Cluster: http://<gateway_public_ip>:8088
```

Répondez aux questions suivantes.

1. Combien de NodeManagers sont visibles ?
2. Quelle est la mémoire totale disponible pour YARN ?
3. Combien de vCPU sont visibles ?
4. Y a-t-il des applications en cours d’exécution ?
5. Pourquoi l’état des NodeManagers est-il important avant de lancer un traitement distribué ?

## Exercice 3 - Explorer les files d’attente YARN

Affichez les informations de la file `default`.

```bash
yarn queue -status default
```

Sur le cluster du cours, si une file dédiée vous est indiquée, vérifiez-la aussi.
L'exemple suivant n'est à lancer que si la file `students` existe dans votre
environnement.

```bash
yarn queue -status students
```

Affichez les applications présentes dans toutes les files.

```bash
yarn application -list -appStates ALL
```

Dans l’interface ResourceManager, ouvrez la partie liée au scheduler.

```text
Docker:  http://localhost:8088/cluster/scheduler
Cluster: http://<gateway_public_ip>:8088/cluster/scheduler
```

Répondez aux questions suivantes.

1. À quoi sert une file d’attente YARN ?
2. Pourquoi peut-on vouloir séparer les ressources entre étudiants, enseignants et traitements automatiques ?
3. Quelle différence faites-vous entre capacité minimale, capacité maximale et ressources réellement utilisées ?
4. Dans un cluster partagé, pourquoi le scheduling est-il un sujet de gouvernance autant qu’un sujet technique ?
5. Pour le projet DORA, quels traitements devraient être prioritaires : ingestion, archivage, audit, traitements analytiques ? Justifiez.

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
2. Pourquoi un moteur de traitement distribué doit-il connaître la localisation des blocs HDFS ?
3. Que se passerait-il si le fichier d’entrée était uniquement présent sur le disque local du gateway ?

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
Docker:  http://localhost:8088
Cluster: http://<gateway_public_ip>:8088
```

Vérifiez le résultat.

```bash
hdfs dfs -ls /user/$USER/tp03/output-wordcount
hdfs dfs -cat /user/$USER/tp03/output-wordcount/part-r-00000
```

Répondez aux questions suivantes.

1. Quel est l’identifiant de l’application YARN lancée ?
2. Quel est le nom de l’application affiché dans YARN ?
3. Combien de temps le job a-t-il duré ?
4. Quel fichier contient le résultat final ?
5. Quels mots apparaissent le plus souvent dans le résultat ?

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
Docker:  http://localhost:19888
Cluster: http://<gateway_public_ip>:19888
```

Répondez aux questions suivantes.

1. Où voyez-vous l’état final de l’application ?
2. Où voyez-vous les logs du job ?
3. Quelle différence faites-vous entre l’interface ResourceManager et le HistoryServer ?
4. Pourquoi les logs sont-ils essentiels pour diagnostiquer un échec de traitement ?


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
2. L’application apparaît-elle dans YARN ?
3. Est-ce une erreur d’entrée, une erreur de ressources, une erreur de code ou une erreur système ?
4. Pourquoi est-il important de distinguer ces catégories d’erreurs ?
5. Quelle démarche suivriez-vous pour diagnostiquer un job MapReduce échoué en production ?


### Erreur 2

Lancez volontairement un job avec un dossier de sortie existant.

```bash
hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  wordcount \
  /user/$USER/tp03/input \
  /user/$USER/tp03/output-wordcount
```

### Erreur 3

Simulez une erreur après le lancement du job : démarrez un traitement YARN en
arrière-plan, attendez quelques secondes, puis supprimez son fichier d'entrée
pendant l'exécution.

```bash
hdfs dfs -rm -r -f /user/$USER/tp03/output-input-deleted

(
  hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
    wordcount \
    /user/$USER/tp03/input \
    /user/$USER/tp03/output-input-deleted &

  job_pid=$!
  sleep 5
  hdfs dfs -rm -f /user/$USER/tp03/input/logs-mapreduce-large.txt
  wait $job_pid
)
```

Observez ensuite l'état de l'application dans YARN.

```bash
yarn application -list -appStates ALL
yarn logs -applicationId <application_id>
```

Si le job se termine trop vite, recommencez l'expérience avec un fichier
d'entrée plus volumineux ou diminuez le délai `sleep 5`. Selon le moment où les
tâches MapReduce ont déjà ouvert leurs splits, le job peut échouer ou se
terminer malgré la suppression.

Restaurez le fichier d'entrée après l'expérience.

```bash
hdfs dfs -put -f logs-mapreduce-large.txt /user/$USER/tp03/input/
```

Répondez aux questions suivantes.

1. Le job échoue-t-il toujours lorsque le fichier d'entrée est supprimé après le lancement ?
2. À quel moment l'erreur apparaît-elle : soumission du job, exécution des mappers, reducers ou écriture de sortie ?
3. Où trouvez-vous le message le plus utile : terminal, ResourceManager, HistoryServer ou logs YARN ?
4. Pourquoi cette erreur est-elle plus intéressante qu'un dossier d'entrée inexistant avant le lancement ?
5. Que faudrait-il éviter en production pour ne pas supprimer des données pendant qu'un traitement les lit ?


### Erreur 4

Lancez volontairement un job qui demande plus de CPU et de mémoire que ce qui
est autorisé dans votre environnement.

Dans Docker, l'image locale limite YARN à une petite capacité. Utilisez cette
variante.

```bash
hdfs dfs -rm -r -f /user/$USER/tp03/output-resource-error

hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  wordcount \
  -D mapreduce.map.memory.mb=4096 \
  -D mapreduce.reduce.memory.mb=4096 \
  -D mapreduce.map.cpu.vcores=2 \
  -D mapreduce.reduce.cpu.vcores=2 \
  /user/$USER/tp03/input \
  /user/$USER/tp03/output-resource-error
```

Sur le cluster du cours, les conteneurs étudiants peuvent avoir d'autres limites.
Si la commande précédente ne provoque pas d'erreur, augmentez les valeurs pour
dépasser les limites indiquées par YARN.

Consultez l'interface du scheduler dans le ResourceManager pour repérer les
limites de mémoire et de vCPU applicables à votre file.

Dans les deux cas, si la demande dépasse la mémoire maximale ou le nombre
maximal de vcores autorisés par YARN, l'application doit être refusée ou rester
impossible à planifier.

Observez l'erreur dans le terminal, puis dans YARN.

```bash
yarn application -list -appStates ALL
yarn logs -applicationId <application_id>
```

Répondez aux questions suivantes.

1. Quel message indique que la demande de ressources est trop élevée ?
2. Le job est-il refusé immédiatement ou reste-t-il en attente ?
3. Quelle ressource pose problème : mémoire, CPU ou les deux ?
4. Pourquoi YARN limite-t-il les ressources demandées par une seule application ?
5. Quel réglage faudrait-il diminuer pour que ce job puisse être accepté ?


## Exercice 8 - Lien avec le projet fil rouge

Dans le projet DORA, les traitements distribués peuvent servir à :

- compter des événements par application ;
- détecter des erreurs fréquentes ;
- produire des indicateurs quotidiens ;
- préparer des données pour Hive ;
- produire des preuves d’audit.

Répondez aux questions suivantes.

1. Quels traitements du projet devraient être lancés régulièrement sur YARN ?
2. Quels traitements peuvent être exécutés en batch de nuit ?
3. Quels traitements doivent être prioritaires en cas d’incident ?
4. Quelles informations faut-il conserver pour prouver qu’un traitement a bien été exécuté ?
5. Comment organiseriez-vous les sorties MapReduce dans les zones `processed` et `audit` du Data Lake ?
6. Quels risques apparaissent si les étudiants ou les traitements automatiques écrivent tous dans les mêmes dossiers de sortie ?

## Nettoyage

Supprimez les fichiers locaux créés pendant le TP.

```bash
rm -f logs-mapreduce.txt logs-mapreduce-large.txt
```

```bash
hdfs dfs -rm -r -f /user/$USER/tp03
```

## Exercice 9 - Comprendre le déroulement MapReduce (Optionnel)

Un job MapReduce WordCount suit plusieurs étapes :

1. lecture des données d’entrée ;
2. découpage logique en splits ;
3. exécution des mappers ;
4. production de paires clé-valeur intermédiaires ;
5. shuffle et tri ;
6. exécution des reducers ;
7. écriture du résultat final dans HDFS.

Pour le WordCount, le mapper produit des paires de ce type :

```text
payment-api 1
INFO 1
ERROR 1
```

Le reducer agrège les valeurs par clé.

```text
payment-api 4000
INFO 3000
ERROR 2000
```

Répondez aux questions suivantes.

1. Quel est le rôle du mapper ?
2. Quel est le rôle du reducer ?
3. Pourquoi l’étape de shuffle est-elle coûteuse ?
4. Pourquoi MapReduce écrit-il le résultat final dans HDFS ?
5. Quelles sont les limites de MapReduce pour des traitements interactifs ou itératifs ?
6. Pourquoi MapReduce reste-t-il utile à étudier même si Spark est souvent utilisé en production ?

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
