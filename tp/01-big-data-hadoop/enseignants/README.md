# TP 01 - Introduction au Big Data et configuration des accès - Corrigé enseignants

Ce document reprend le TP étudiant et place les réponses indicatives directement
sous les questions concernées. Les réponses servent de guide de correction et
peuvent être adaptées selon le contexte de classe.

## Objectifs

À la fin de ce TP, vous devez être capable de :

- situer Hadoop dans une architecture Big Data moderne ;
- expliquer pourquoi une architecture distribuée est nécessaire pour certains cas d’usage ;
- identifier les premiers enjeux d’accès, de sécurité et de gouvernance ;
- générer une clé SSH personnelle ;
- transmettre uniquement votre clé publique à l’enseignant ;
- vous connecter au gateway Hadoop ;
- vérifier que votre environnement de travail est prêt pour les prochaines séances.

Ce TP ne vise pas encore à manipuler HDFS, YARN, Hive ou HBase en détail. Ces outils feront l’objet de TP spécifiques dans les séances suivantes.

## Option locale - Image Docker tout-en-un

Cette section permet de démarrer un environnement Hadoop local dans un seul conteneur Docker.

L’image contient les services nécessaires aux TP du module :

- HDFS : NameNode et DataNode ;
- YARN : ResourceManager et NodeManager ;
- MapReduce : JobHistory Server ;
- Spark : client Spark et Spark History Server ;
- Hive : Metastore et HiveServer2 ;
- HBase : ZooKeeper, Master et RegionServer.

Cette installation est utile pour observer les composants Hadoop et travailler hors du cluster cloud. Elle reste un environnement pédagogique mono-machine : elle ne remplace pas un vrai cluster distribué.

### Prérequis Docker

Installez Docker Desktop si Docker n’est pas encore disponible sur votre machine :

```text
https://docs.docker.com/get-started/get-docker/
```

Vérifiez que Docker est installé.

```bash
docker --version
docker compose version
```

Prévoyez idéalement au moins 6 Go de RAM disponibles pour Docker Desktop. L’image démarre plusieurs services Big Data dans le même conteneur.

Placez-vous dans le dossier du TP.

```bash
cd tp/01-big-data-hadoop
```

Construisez l’image Docker.

```bash
docker compose build
```

Le premier build peut prendre plusieurs minutes, car l’image télécharge Hadoop, Spark, Hive et HBase.

Démarrez l’environnement.

```bash
docker compose up -d
```

Vérifiez que le conteneur est démarré.

```bash
docker compose ps
```

Ouvrez les interfaces Web locales.

```text
HDFS NameNode:          http://localhost:9870
HDFS DataNode:          http://localhost:9864
YARN ResourceManager:   http://localhost:8088
YARN NodeManager:       http://localhost:8042
MapReduce History:      http://localhost:19888
Spark History Server:   http://localhost:18080
HiveServer2 Web UI:     http://localhost:10002
HBase Master:           http://localhost:16010
HBase RegionServer:     http://localhost:16030
```

Si l’interface NameNode s’affiche sans mise en page correcte, essayez d’abord :

- rafraîchir la page avec `Ctrl + F5` ;
- ouvrir `http://127.0.0.1:9870` au lieu de `http://localhost:9870` ;
- tester dans une fenêtre de navigation privée ;
- utiliser un navigateur à jour, par exemple Firefox, Chrome ou Edge.

Vous pouvez aussi redémarrer le conteneur.

```bash
docker compose restart
```

Si le problème persiste, contactez le professeur.

```bash
docker compose down -v
docker compose up -d
```

Entrez dans le conteneur `tp-hadoop`.

```bash
docker exec -it tp-hadoop bash
```

Vérifiez que les commandes principales répondent.

```bash
hadoop version
hdfs dfsadmin -report
hdfs dfs -ls /
yarn node -list
spark-submit --version
beeline --version
hbase version
```

Vérifiez MapReduce.

```bash
hadoop jar $HADOOP_HOME/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar pi 2 10
```

Vérifiez Spark sur YARN.

```bash
spark-submit \
  --master yarn \
  --class org.apache.spark.examples.SparkPi \
  $SPARK_HOME/examples/jars/spark-examples_2.12-3.5.8.jar \
  10
```

Vérifiez Hive.

```bash
beeline -u 'jdbc:hive2://localhost:10000/default;auth=noSasl' -e 'SHOW DATABASES;'
```

Vérifiez HBase.

```bash
echo "status 'simple'" | hbase shell -n
```

Quittez le conteneur.

```bash
exit
```

Consultez les logs si nécessaire.

```bash
docker compose logs -f tp-hadoop
```

Arrêtez l’environnement.

```bash
docker compose down
```

Supprimez aussi les volumes si vous voulez repartir de zéro.

```bash
docker compose down -v
```

## Prérequis cloud

Vous devez avoir :

- un terminal ;
- un navigateur Web ;
- l’adresse IP publique du gateway fournie par l’enseignant ;
- votre identifiant étudiant.

Votre identifiant correspond à la première partie de votre adresse e-mail, avant le caractère `@`.

Exemple :

```text
jean.dupont@ecole.fr
```

donne l’identifiant :

```text
jean.dupont
```

Dans les commandes, remplacez :

```text
identifiant
```

par votre identifiant étudiant.

Remplacez aussi :

```text
<gateway_public_ip>
```

par l’adresse IP publique du gateway.

## Exercice 1 - Générer votre clé SSH

Chaque étudiant doit générer sa propre clé SSH sur son ordinateur.

Exécutez la commande suivante :

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C identifiant
```

Exemple pour `jean.dupont` :

```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/m2-hadoop-student -C jean.dupont
```

La commande crée deux fichiers :

```text
~/.ssh/m2-hadoop-student
~/.ssh/m2-hadoop-student.pub
```

Le fichier sans extension est votre clé privée. Il doit rester sur votre ordinateur.

Le fichier avec l’extension `.pub` est votre clé publique. C’est ce fichier qui doit être transmis à l’enseignant.

Questions de réflexion :

1. Pourquoi une clé SSH personnelle est-elle préférable à un mot de passe commun pour tous les étudiants ?
   Réponse indicative : Une clé personnelle identifie clairement l'utilisateur, évite le partage d'un secret commun et permet de révoquer un accès sans impacter toute la classe.
2. Quels risques apparaissent si plusieurs utilisateurs partagent la même identité technique sur un cluster ?
   Réponse indicative : On perd la traçabilité, il devient difficile d'attribuer une action, et un incident de sécurité peut concerner tous les utilisateurs.
3. Pourquoi le commentaire placé à la fin de la clé, par exemple `jean.dupont`, est-il utile pour l’administration ?
   Réponse indicative : Le commentaire aide l'administrateur à relier rapidement une clé à une personne ou à un compte.
4. Que faudrait-il prévoir dans une organisation réelle lorsqu’un collaborateur quitte un projet ou perd sa clé privée ?
   Réponse indicative : Il faut révoquer la clé publique, auditer les accès, renouveler les secrets si nécessaire et documenter le départ ou l'incident.

## Exercice 2 - Transmettre votre clé publique

Affichez votre clé publique.

```bash
cat ~/.ssh/m2-hadoop-student.pub
```

Copiez toute la ligne affichée et envoyez-la à l’enseignant.

Elle doit ressembler à ceci :

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... identifiant
```

## Exercice 3 - Connexion au gateway Hadoop

Une fois votre clé publique installée par l’enseignant, connectez-vous au gateway.

```bash
ssh -i ~/.ssh/m2-hadoop-student identifiant@<gateway_public_ip>
```

Exemple :

```bash
ssh -i ~/.ssh/m2-hadoop-student jean.dupont@<gateway_public_ip>
```

Après connexion, vérifiez votre utilisateur.

```bash
whoami
hostname
pwd
```

Questions de réflexion :

1. Pourquoi l’accès étudiant se fait-il par un gateway plutôt que directement vers les machines internes du cluster ?
   Réponse indicative : Le gateway limite l'exposition du cluster : les étudiants passent par un point d'entrée contrôlé au lieu d'accéder directement aux nœuds internes.
2. Quels avantages apporte un gateway pour la sécurité, l’administration et la traçabilité ?
   Réponse indicative : Il centralise les accès SSH, les journaux, les règles réseau et l'administration des comptes.
3. Quels risques apparaissent si le gateway est mal configuré ou trop exposé sur Internet ?
   Réponse indicative : Il peut devenir une porte d'entrée vers tout le cluster : brute force, vol de clé, rebond réseau ou fuite d'interfaces internes.
4. Dans une architecture de production, quels mécanismes complémentaires pourraient renforcer ce point d’entrée ?
   Réponse indicative : MFA, bastion durci, filtrage IP, VPN, rotation des clés, supervision, audit, moindre privilège et séparation des comptes.
5. Expliquez la différence entre accéder à un cluster pour l’administrer et accéder à un cluster pour soumettre des traitements.
   Réponse indicative : Administrer signifie configurer et maintenir l'infrastructure. Soumettre des traitements signifie utiliser les services Hadoop avec des droits limités.

## Exercice 4 - Charger l’environnement de travail

Chargez les variables d’environnement disponibles sur le gateway.

```bash
source /etc/profile.d/hadoop.sh
source /etc/profile.d/spark.sh
source /etc/profile.d/hive.sh
source /etc/profile.d/hbase.sh
```

Vérifiez que les commandes principales répondent.

```bash
hadoop version
spark-submit --version
beeline --version
hbase version
```

Questions de réflexion :

1. À quoi servent les variables d’environnement comme `HADOOP_HOME`, `SPARK_HOME` ou `HBASE_HOME` ?
   Réponse indicative : Elles indiquent où les logiciels sont installés et permettent aux commandes de trouver les binaires, bibliothèques et fichiers de configuration.
2. Pourquoi est-il important que tous les étudiants utilisent le même environnement logiciel pendant un TP ?
   Réponse indicative : Cela évite les écarts de comportement et simplifie l'aide pendant le TP.
3. Quels problèmes peuvent apparaître si deux versions différentes de Spark, Hive ou Hadoop sont présentes sur la même machine ?
   Réponse indicative : Incompatibilités de protocole, erreurs de classes Java, mauvais fichiers de configuration, différences de syntaxe ou résultats difficiles à reproduire.
4. Pourquoi la reproductibilité de l’environnement est-elle importante dans un contexte data engineering ?
   Réponse indicative : Un pipeline data doit pouvoir être rejoué avec le même environnement pour diagnostiquer, auditer et industrialiser les traitements.

## Exercice 5 - Découverte des interfaces Web

Ouvrez les interfaces suivantes dans votre navigateur.

```text
NameNode UI:             http://<gateway_public_ip>:9870
YARN ResourceManager:    http://<gateway_public_ip>:8088
MapReduce HistoryServer: http://<gateway_public_ip>:19888
Spark History Server:    http://<gateway_public_ip>:18080
HiveServer2 Web UI:      http://<gateway_public_ip>:10002
HBase Master UI:         http://<gateway_public_ip>:16010
```

Questions de réflexion :

1. Classez ces interfaces selon leur fonction principale : stockage, calcul, historique d’exécution, requêtage ou base NoSQL.
   Réponse indicative : NameNode : stockage HDFS. YARN ResourceManager : calcul et ressources. MapReduce HistoryServer et Spark History Server : historique d'exécution. HiveServer2 : requêtage SQL. HBase Master : base NoSQL.
2. Pourquoi les interfaces Web sont-elles utiles pour l’exploitation d’un cluster distribué ?
   Réponse indicative : Elles donnent une vue rapide de l'état du cluster, des nœuds, des jobs, des erreurs et de l'utilisation des ressources.
3. Quelles informations visibles dans ces interfaces pourraient être sensibles dans un contexte professionnel ?
   Réponse indicative : Noms d'utilisateurs, chemins de données, volumes, logs applicatifs, erreurs, configuration, adresses internes et informations d'infrastructure.
4. Pourquoi ne faudrait-il pas exposer directement toutes les interfaces internes d’un cluster Hadoop sur Internet ?
   Réponse indicative : Elles ne sont pas toutes prévues pour être exposées publiquement et peuvent révéler des informations sensibles ou permettre des actions non souhaitées.

## Exercice 6 - Préparer le projet fil rouge

Le projet du module porte sur une plateforme de stockage à froid destinée à conserver plusieurs années de logs techniques dans un contexte inspiré du règlement DORA.

Répondez aux questions suivantes en vous plaçant dans le rôle d’une équipe data engineering.

1. Quels objectifs métiers peuvent justifier la conservation longue durée de logs techniques dans une institution financière ?
   Réponse indicative : Audit, investigation d'incident, traçabilité, conformité, preuve de fonctionnement, analyse de pannes et amélioration de la supervision.
2. Quelles contraintes réglementaires, opérationnelles et techniques doivent être prises en compte dès la conception ?
   Réponse indicative : Durée de conservation, intégrité, confidentialité, disponibilité, droits d'accès, traçabilité, coûts de stockage et capacité à retrouver les données.
3. Proposez une première séparation logique entre données brutes, données archivées, données transformées et données d’audit. Justifiez cette séparation.
   Réponse indicative : `raw` conserve les données originales, `archive` garde l'historique long terme, `processed` contient les données transformées, `audit` stocke les preuves et contrôles.
4. Quels risques introduit une mauvaise gestion des droits d’accès sur un lac de données ?
   Réponse indicative : Fuite de données, modification non autorisée, perte de preuve, non-conformité et difficulté à attribuer les actions.

## Exercice 7 - Analyser le besoin Big Data

Répondez aux questions suivantes en argumentant vos réponses.

1. Les 5V du Big Data sont souvent présentés comme une définition générale. En quoi cette grille d’analyse peut-elle être insuffisante pour décider si une architecture Big Data est réellement nécessaire ?
   Réponse indicative : Les 5V décrivent des symptômes, mais ne suffisent pas à décider l'architecture. Il faut aussi regarder les usages, les SLA, les coûts, les compétences et la gouvernance.
2. Pour une entreprise financière qui conserve plusieurs années de logs techniques, quels critères permettent de décider entre une base relationnelle classique, un stockage objet, un cluster Hadoop ou une architecture hybride ?
   Réponse indicative : Une base relationnelle convient aux volumes modérés et requêtes structurées. Le stockage objet convient à l'archive massive. Hadoop convient au traitement distribué proche des données. Une architecture hybride combine souvent ces besoins.
3. Expliquez pourquoi le volume de données n’est pas le seul facteur de complexité. Discutez aussi la variété, la vélocité, la qualité des données, la gouvernance et les exigences réglementaires.
   Réponse indicative : Des données variées, rapides, de qualité inégale ou fortement réglementées peuvent rendre le système complexe même avec un volume raisonnable.
4. Dans quels cas le scale up peut-il rester pertinent malgré les avantages du scale out ?
   Réponse indicative : Le scale up reste pertinent pour des workloads simples, prévisibles, peu distribuables, ou quand une grosse machine coûte moins cher qu'un cluster à exploiter.
5. Quels compromis introduit une architecture distribuée en matière de coût, de performance, d’exploitation, de sécurité et de tolérance aux pannes ?
   Réponse indicative : Le distribué apporte scalabilité et tolérance aux pannes, mais augmente la complexité d'exploitation, de sécurité, de supervision, de réseau et de diagnostic.

## À retenir

Pour cette première séance, l’objectif principal est d’avoir un accès fonctionnel au cluster et de comprendre les premiers choix d’architecture.

Les séances suivantes seront consacrées à des TP spécifiques :

- HDFS ;
- YARN ;
- MapReduce et Spark ;
- Hive ;
- HBase.
