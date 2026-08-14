# TP 01 - Introduction au Big Data et configuration des accès

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

## Option locale - Installation d’un mini-cluster Hadoop avec Docker

Cette section permet de démarrer un mini-cluster Hadoop local pour découvrir les services principaux sans utiliser le cluster cloud.

Cette installation est utile pour observer les composants Hadoop, mais elle ne remplace pas le cluster partagé du cours. Pour les TP suivants, les consignes préciseront si vous devez travailler sur Docker ou sur le gateway fourni par l’enseignant.

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

Placez-vous dans le dossier du TP.

```bash
cd tp/01-big-data-hadoop
```

Démarrez le mini-cluster.

```bash
docker compose up -d
```

Vérifiez que les conteneurs sont démarrés.

```bash
docker compose ps
```

Ouvrez les interfaces Web locales.

```text
NameNode UI:          http://localhost:9870
YARN ResourceManager: http://localhost:8088
NodeManager UI:       http://localhost:8042
```

Si l’interface NameNode s’affiche sans mise en page correcte, essayez d’abord :

- rafraîchir la page avec `Ctrl + F5` ;
- ouvrir `http://127.0.0.1:9870` au lieu de `http://localhost:9870` ;
- tester dans une fenêtre de navigation privée ;
- utiliser un navigateur à jour, par exemple Firefox, Chrome ou Edge.

Vous pouvez aussi redémarrer les conteneurs.

```bash
docker compose restart
```

Si le problème persiste, contactez le professeur.

```bash
docker compose down -v
docker compose up -d
```

Entrez dans le conteneur `namenode`.

```bash
docker exec -it namenode bash
```

Vérifiez que Hadoop répond.

```bash
hadoop version
hdfs dfs -ls /
```

Quittez le conteneur.

```bash
exit
```

Consultez les logs si nécessaire.

```bash
docker compose logs -f namenode
docker compose logs -f datanode
docker compose logs -f resourcemanager
```

Arrêtez le mini-cluster.

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
2. Quels risques apparaissent si plusieurs utilisateurs partagent la même identité technique sur un cluster ?
3. Pourquoi le commentaire placé à la fin de la clé, par exemple `jean.dupont`, est-il utile pour l’administration ?
4. Que faudrait-il prévoir dans une organisation réelle lorsqu’un collaborateur quitte un projet ou perd sa clé privée ?

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
2. Quels avantages apporte un gateway pour la sécurité, l’administration et la traçabilité ?
3. Quels risques apparaissent si le gateway est mal configuré ou trop exposé sur Internet ?
4. Dans une architecture de production, quels mécanismes complémentaires pourraient renforcer ce point d’entrée ?
5. Expliquez la différence entre accéder à un cluster pour l’administrer et accéder à un cluster pour soumettre des traitements.

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
2. Pourquoi est-il important que tous les étudiants utilisent le même environnement logiciel pendant un TP ?
3. Quels problèmes peuvent apparaître si deux versions différentes de Spark, Hive ou Hadoop sont présentes sur la même machine ?
4. Pourquoi la reproductibilité de l’environnement est-elle importante dans un contexte data engineering ?

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
2. Pourquoi les interfaces Web sont-elles utiles pour l’exploitation d’un cluster distribué ?
3. Quelles informations visibles dans ces interfaces pourraient être sensibles dans un contexte professionnel ?
4. Pourquoi ne faudrait-il pas exposer directement toutes les interfaces internes d’un cluster Hadoop sur Internet ?
5. Quelles différences faites-vous entre monitoring, observabilité et audit ?
6. En cas d’incident sur un traitement distribué, quelles interfaces consulteriez-vous en premier et pourquoi ?

## Exercice 6 - Préparer le projet fil rouge

Le projet du module porte sur une plateforme de stockage à froid destinée à conserver plusieurs années de logs techniques dans un contexte inspiré du règlement DORA.

Répondez aux questions suivantes en vous plaçant dans le rôle d’une équipe data engineering.

1. Quels objectifs métiers peuvent justifier la conservation longue durée de logs techniques dans une institution financière ?
2. Quelles contraintes réglementaires, opérationnelles et techniques doivent être prises en compte dès la conception ?
3. Proposez une première séparation logique entre données brutes, données archivées, données transformées et données d’audit. Justifiez cette séparation.
4. Quels risques introduit une mauvaise gestion des droits d’accès sur un lac de données ?
5. Quelles métadonnées faudrait-il conserver pour rendre les données exploitables plusieurs années après leur ingestion ?
6. Comment arbitrer entre coût de stockage, performance d’accès, sécurité et durée de conservation ?
7. Quels indicateurs permettraient de démontrer que la plateforme est fiable et exploitable ?
8. Quelles limites voyez-vous à l’utilisation d’un cluster Hadoop pour ce type de besoin par rapport à des solutions cloud managées ?

## Exercice 7 - Analyser le besoin Big Data

Répondez aux questions suivantes en argumentant vos réponses.

1. Les 5V du Big Data sont souvent présentés comme une définition générale. En quoi cette grille d’analyse peut-elle être insuffisante pour décider si une architecture Big Data est réellement nécessaire ?
2. Pour une entreprise financière qui conserve plusieurs années de logs techniques, quels critères permettent de décider entre une base relationnelle classique, un stockage objet, un cluster Hadoop ou une architecture hybride ?
3. Expliquez pourquoi le volume de données n’est pas le seul facteur de complexité. Discutez aussi la variété, la vélocité, la qualité des données, la gouvernance et les exigences réglementaires.
4. Dans quels cas le scale up peut-il rester pertinent malgré les avantages du scale out ?
5. Quels compromis introduit une architecture distribuée en matière de coût, de performance, d’exploitation, de sécurité et de tolérance aux pannes ?

## À retenir

Pour cette première séance, l’objectif principal est d’avoir un accès fonctionnel au cluster et de comprendre les premiers choix d’architecture.

Les séances suivantes seront consacrées à des TP spécifiques :

- HDFS ;
- YARN ;
- MapReduce et Spark ;
- Hive ;
- HBase.
