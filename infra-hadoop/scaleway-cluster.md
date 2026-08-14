
# Déploiement d'un cluster Hadoop sur Scaleway
## Plateforme pédagogique pour un Master 2 Big Data

## Objectif

Mettre à disposition des étudiants une plateforme Hadoop déployée dans le cloud afin de leur permettre de manipuler un cluster proche des environnements rencontrés en entreprise.

Le déploiement sera entièrement automatisé :

- **Terraform** : création de l'infrastructure.
- **Ansible** : installation et configuration des composants Hadoop.

L'objectif est également de :

- maîtriser les coûts d'exploitation ;
- limiter les ressources consommées par les étudiants ;
- automatiser la création des comptes utilisateurs ;
- reproduire une démarche DevOps / Infrastructure as Code.

---

# Budget d'utilisation recommandé

## Budget maximum

**1 700 € HT / mois**

Ce budget suppose que les machines virtuelles sont démarrées uniquement pendant :

- les séances de cours ;
- les travaux pratiques ;
- les périodes de préparation.

Les instances seront arrêtées automatiquement en dehors des créneaux pédagogiques afin de limiter les coûts.

## Estimation budgétaire

| Poste | Budget estimé |
|-------|--------------:|
| Bastion, Gateway et Hadoop Master | 222 € |
| Workers Hadoop x5 avec redimensionnement 75 % du temps | 1 183 € |
| Object Storage sauvegarde (~500 Go) | 4 € |
| Réserve technique (IP, snapshots, marge) | 100 € |
| **Total estimé en fonctionnement continu** | **~2 471 € HT** |
| **Total estimé avec redimensionnement 75 % du temps** | **~1 510 € HT** |
| **Budget plafond recommandé** | **1 700 € HT** |

> Le budget exact dépendra du type d'instances Scaleway choisi, de la région, de la durée réelle d'utilisation et du volume de stockage provisionné. Les machines doivent être arrêtées automatiquement hors séance pour rester dans le budget.

---

# Architecture proposée

```text
                Internet
                    |
               Bastion SSH
                    |
        -------------------------
        |                       |
     Gateway             Hadoop Master
                               |
        -------------------------------------
        |                 |                |
    Workers 1-2      Workers 3-4       Worker 5
```

---

# Détail des machines

## Vue synthétique

| Machine | Nombre | Rôle | CPU | RAM | Disque système | Disque données | Accès public |
|--------|-------:|------|----:|----:|---------------:|---------------:|--------------|
| Bastion / Ansible | 1 | Administration, Terraform, Ansible | 2 vCPU | 4 Go | 40 Go | Aucun | Oui, IP enseignant uniquement |
| Gateway étudiants | 1 | Connexion SSH des étudiants, clients Hadoop/Hive/HBase | 4 vCPU | 8 Go | 80 Go | Aucun | Oui, SSH étudiants uniquement |
| Hadoop Master | 1 | NameNode, ResourceManager, JobHistory Server, Hive Metastore | 8 vCPU | 32 Go | 100 Go | 100 Go | Non |
| Workers Hadoop | 5 | DataNode, NodeManager | 16 vCPU par worker | 32 Go par worker | 100 Go par worker | 600 Go par worker | Non |

## Capacité globale

| Ressource | Capacité |
|----------|---------:|
| Nombre total de VM | 8 |
| CPU total | 94 vCPU |
| RAM totale | 204 Go |
| CPU total en mode réduit hors TP | 34 vCPU |
| RAM totale en mode réduit hors TP | 84 Go |
| Stockage HDFS brut | 3 To |
| Stockage HDFS utile avec réplication x3 | ~1 To |
| Nombre d'étudiants | 160 |
| Ressources cibles par étudiant | 1 vCPU, 1 Go RAM, 5 Go SSD utiles |
| CPU étudiant total théorique | 160 vCPU |
| RAM étudiante totale réservée | 160 Go |
| Quota HDFS par étudiant | 5 Go |
| Stockage étudiant total réservé | 800 Go utiles |
| Marge restante pour datasets, résultats et administration | ~200 Go utiles, à compléter par nettoyage régulier ou stockage objet pour les datasets volumineux |

Ce dimensionnement repose sur la mutualisation de la plateforme : tous les étudiants ne lanceront pas en permanence un traitement consommant leur quota CPU et mémoire complet. Les limites sont donc pensées comme des plafonds pédagogiques, pas comme une réservation dédiée et isolée pour chaque compte. La capacité physique CPU est volontairement inférieure au cumul théorique des quotas étudiants.

Pendant les séances de TP, les Workers sont dimensionnés en mode actif. En dehors des séances, environ 75 % du temps, ils peuvent être redimensionnés en mode réduit avec 4 vCPU et 8 Go RAM par Worker, tout en conservant les volumes Block Storage attachés.

---

# Justification du dimensionnement

## Bastion / Ansible

Le Bastion sert uniquement à l'administration.

Il permet :

- de lancer Terraform ;
- d'exécuter Ansible ;
- d'accéder aux machines internes ;
- de centraliser les clés SSH d'administration.

Configuration recommandée :

```text
2 vCPU
4 Go RAM
40 Go disque système
```

Cette machine n'a pas besoin de disque de données.

---

## Gateway étudiants

La Gateway est la seule machine accessible par les étudiants.

Elle permet :

- la connexion SSH des étudiants ;
- l'utilisation des clients Hadoop ;
- l'utilisation de `hdfs dfs` ;
- l'exécution des commandes Hive ;
- l'accès au shell HBase ;
- la compilation éventuelle des projets Java MapReduce.

Configuration recommandée :

```text
4 vCPU
8 Go RAM
80 Go disque système
```

La Gateway ne stocke pas les données Hadoop et ne doit pas exécuter les traitements lourds. Elle sert de point d'entrée pédagogique pour les connexions SSH, les clients Hadoop et la soumission des jobs vers YARN.

---

## Hadoop Master

Le Master héberge les services centraux du cluster.

Services installés :

- NameNode ;
- ResourceManager ;
- JobHistory Server ;
- Hive Metastore ;
- services d'administration Hadoop.

Configuration recommandée :

```text
8 vCPU
32 Go RAM
100 Go disque système
100 Go disque données / métadonnées
```

Justification :

- le NameNode a besoin de mémoire pour gérer les métadonnées HDFS ;
- le ResourceManager gère les ressources YARN ;
- le disque supplémentaire permet de séparer les métadonnées et les journaux des services Hadoop.

---

## Workers Hadoop

Les Workers exécutent les traitements et stockent les blocs HDFS.

Services installés :

- DataNode ;
- NodeManager.

Configuration recommandée par Worker :

```text
16 vCPU
32 Go RAM
100 Go disque système
600 Go disque HDFS
```

Avec 5 Workers :

```text
80 vCPU
160 Go RAM
3 To de stockage HDFS brut
```

Avec un facteur de réplication HDFS de 3, la capacité réellement utilisable est d'environ :

```text
3 To / 3 = 1 To utile
```

Cette capacité est suffisante pour :

- 160 étudiants ;
- un quota de 5 Go par étudiant ;
- des jeux de données de TP ;
- des résultats MapReduce ;
- des tables Hive ;
- des fichiers d'audit du projet DORA.

---

# Déploiement automatisé

## Terraform

Terraform assurera :

- création du réseau privé ;
- création des instances ;
- création des volumes Block Storage ;
- configuration des Security Groups ;
- attribution des adresses IP ;
- création des ressources réseau.

## Ressources Terraform à prévoir

```text
scaleway_instance_server.bastion
scaleway_instance_server.gateway
scaleway_instance_server.hadoop_master
scaleway_instance_server.worker_1
scaleway_instance_server.worker_2
scaleway_instance_server.worker_3
scaleway_instance_server.worker_4
scaleway_instance_server.worker_5

scaleway_instance_volume.master_metadata
scaleway_instance_volume.worker_1_hdfs
scaleway_instance_volume.worker_2_hdfs
scaleway_instance_volume.worker_3_hdfs
scaleway_instance_volume.worker_4_hdfs
scaleway_instance_volume.worker_5_hdfs
```

Dans l'implémentation Terraform, les Workers peuvent être déclarés avec `count` ou `for_each` afin d'éviter de dupliquer manuellement les cinq blocs.

Une première implémentation Infrastructure as Code est disponible dans :

- `infra-hadoop/scaleway/terraform` pour la création des ressources Scaleway ;
- `infra-hadoop/scaleway/ansible` pour l'installation et la configuration Hadoop.

Le flux recommandé est :

```bash
cd infra-hadoop/scaleway/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook site.yml
```

## Ansible

Ansible installera automatiquement :

- Java ;
- Hadoop ;
- HDFS ;
- YARN ;
- MapReduce ;
- Hive ;
- HBase ;
- création des comptes Linux ;
- configuration HDFS ;
- configuration YARN ;
- déploiement des jeux de données.

---

# Gestion des étudiants

160 comptes seront créés automatiquement :

```text
student01
student02
...
student160
```

Chaque étudiant disposera :

- d'un compte Linux ;
- d'un répertoire personnel ;
- d'un espace HDFS dédié ;
- d'un accès SSH via la Gateway.

Exemple d'arborescence HDFS :

```text
/user/student01
/user/student02
...
/user/student160
/datalake/raw
/datalake/archive
/datalake/processed
/datalake/audit
```

---

# Limitation des ressources

## HDFS

Limites recommandées par étudiant :

```text
Quota espace : 5 Go
Quota fichiers : 50 000 fichiers
```

Exemple :

```bash
hdfs dfsadmin -setSpaceQuota 5g /user/student01
hdfs dfsadmin -setQuota 50000 /user/student01
```

## YARN

Configuration recommandée :

```text
Queue dédiée : students
Capacité de la queue : 60 %
Capacité maximale : 70 %
Mémoire max par container : 1 Go
vCore max par container : 1
Applications simultanées : 160
```

Objectif :

- éviter qu'un étudiant monopolise le cluster ;
- permettre l'exécution simultanée des TP ;
- garantir un partage équitable des ressources.

## Linux

Limiter aussi les ressources au niveau système :

```text
Nombre de processus par étudiant : 100 à 150
Nombre de fichiers ouverts : 1024 à 2048
```

Exemple dans `/etc/security/limits.conf` :

```text
@student soft nproc 100
@student hard nproc 150
@student soft nofile 1024
@student hard nofile 2048
```

---

# Sécurité

Les étudiants disposeront uniquement :

- d'un accès SSH vers la Gateway ;
- des commandes Hadoop ;
- des commandes Hive ;
- des commandes HBase.

Les interfaces d'administration du cluster ne seront accessibles qu'à l'enseignant.

## Règles réseau recommandées

| Flux | Autorisation |
|------|--------------|
| SSH enseignant vers Bastion | Oui |
| SSH étudiants vers Gateway | Oui |
| SSH Bastion vers machines internes | Oui |
| Accès public NameNode UI | Non |
| Accès public ResourceManager UI | Non |
| Accès public DataNode / NodeManager | Non |
| Accès direct étudiants aux Workers | Non |

---

# Optimisation des coûts

Le cluster sera :

- démarré automatiquement avant les séances ;
- redimensionné automatiquement après les séances ;
- éventuellement arrêté complètement pendant les longues périodes sans TP ;
- recréé si nécessaire avec Terraform.

Des alertes de consommation seront configurées afin de suivre le budget.

## Recommandations

- Définir une alerte à 50 % du budget.
- Définir une alerte à 80 % du budget.
- Définir une alerte à 100 % du budget.
- Redimensionner les Workers hors créneaux pédagogiques.
- Arrêter les instances pendant les longues périodes d'inactivité.
- Supprimer les volumes inutilisés.
- Nettoyer régulièrement les répertoires temporaires HDFS.

---

# Coût indicatif si les machines ne sont pas éteintes

## Hypothèse

À titre d'information, si les machines restent allumées en continu **24h/24 et 7j/7 pendant un mois complet**, le coût sera beaucoup plus élevé.

Cette estimation prend en compte :

- 8 machines virtuelles allumées en permanence ;
- les volumes Block Storage attachés ;
- le stockage HDFS provisionné ;
- une marge technique pour les IP, snapshots éventuels et trafic.

## Estimation mensuelle en fonctionnement continu

| Poste | Estimation mensuelle HT |
|-------|------------------------:|
| Bastion / Ansible | ~21 € |
| Gateway étudiants | ~39 € |
| Hadoop Master | ~163 € |
| Workers Hadoop x5 | ~2 418 € |
| Object Storage sauvegarde | ~4 € |
| Réserve technique | ~100 € |
| **Total indicatif si tout reste allumé** | **~2 471 € HT / mois** |

## Estimation avec redimensionnement 75 % du temps

Hypothèse :

- 25 % du temps : Workers en mode TP actif, avec 16 vCPU et 32 Go RAM par Worker ;
- 75 % du temps : Workers en mode réduit, avec 4 vCPU et 8 Go RAM par Worker ;
- les volumes Block Storage restent conservés et facturés pendant toute la période.

| Poste | Estimation mensuelle HT |
|-------|------------------------:|
| Bastion / Ansible | ~21 € |
| Gateway étudiants | ~39 € |
| Hadoop Master | ~163 € |
| Workers Hadoop x5, 25 % en mode TP actif | ~536 € |
| Workers Hadoop x5, 75 % en mode réduit | ~647 € |
| Object Storage sauvegarde | ~4 € |
| Réserve technique | ~100 € |
| **Total indicatif avec redimensionnement** | **~1 510 € HT / mois** |

## Comparaison

| Mode d'utilisation | Coût mensuel estimé HT |
|--------------------|-----------------------:|
| Utilisation pédagogique avec Workers réduits 75 % du temps | ~1 510 € HT |
| Budget plafond recommandé | 1 700 € HT |
| Fonctionnement continu 24h/24 | ~2 471 € HT |

## Conclusion

Pour maîtriser les coûts, il est indispensable de mettre en place :

- l'arrêt automatique des machines après les séances ;
- le démarrage automatique avant les TP ;
- le redimensionnement automatique des Workers en mode réduit hors TP ;
- des alertes de facturation Scaleway ;
- une supervision régulière des volumes non utilisés ;
- une suppression des ressources inutiles après le module.

Le fonctionnement continu peut augmenter fortement le coût mensuel par rapport à une utilisation pédagogique maîtrisée. Pour ce dimensionnement, l'écart estimé est d'environ **960 € HT par mois** entre des Workers toujours en mode TP actif et des Workers réduits 75 % du temps.

---

# Résumé de l'installation

## Infrastructure

```text
1 Bastion / Ansible
1 Gateway étudiants
1 Hadoop Master
5 Workers Hadoop
```

## Stockage

```text
3 To HDFS brut
~1 To HDFS utile avec réplication x3
5 Go HDFS par étudiant
```

## Étudiants

```text
160 comptes Linux
160 espaces HDFS
1 queue YARN partagée
quotas HDFS
limites Linux
```

## Technologies installées

```text
Java
Hadoop
HDFS
YARN
MapReduce
Hive
HBase
Terraform
Ansible
```

---

# Ressources officielles Scaleway

## Tarification générale

https://www.scaleway.com/en/pricing/

## Tarification des machines virtuelles

https://www.scaleway.com/en/pricing/virtual-instances/

## Tarification du stockage

https://www.scaleway.com/en/pricing/storage/

## Documentation sur la facturation des instances

https://www.scaleway.com/en/docs/instances/reference-content/understanding-instance-pricing/

## Documentation Terraform Provider Scaleway

https://registry.terraform.io/providers/scaleway/scaleway/latest

## Documentation Ansible Scaleway

https://docs.ansible.com/projects/ansible/latest/collections/community/general/docsite/guide_scaleway.html

---

# Conclusion

Cette architecture permet de fournir aux 160 étudiants une véritable expérience cloud Hadoop tout en gardant un budget maîtrisé.

Le choix d'un cluster partagé avec quotas HDFS, file YARN dédiée et accès via Gateway permet de :

- réduire les coûts ;
- centraliser l'administration ;
- limiter les abus de ressources ;
- habituer les étudiants à un environnement proche d'une plateforme Big Data d'entreprise ;
- automatiser entièrement le déploiement avec Terraform et Ansible.
