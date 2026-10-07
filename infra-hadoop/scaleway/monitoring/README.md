# Monitoring de la plateforme

Le playbook installe Node Exporter sur toutes les machines du groupe `cluster`
(bastion, gateway, master et workers). La gateway héberge Prometheus, Grafana,
Blackbox Exporter et un petit adaptateur Python pour les API HDFS/YARN.
Il utilise les paquets Ubuntu pour Prometheus et les exporters, et le dépôt
officiel Grafana OSS. Docker n'est pas nécessaire.

## Déployer

Depuis le bastion, après avoir mis à jour sa copie du dépôt et généré
`ansible/inventory.ini` avec Terraform :

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook monitoring.yml
```

Le déploiement complet `site.yml` inclut aussi le monitoring. Pour ne lancer
que ce composant : `ansible-playbook site.yml --tags monitoring`.
Le playbook autonome ne demande pas de paramètre `student_school`.
Les machines doivent pouvoir accéder aux dépôts Ubuntu et à `apt.grafana.com`.

## Accéder au tableau de bord

Grafana écoute sur `0.0.0.0:3000` de la gateway. Après `terraform apply`,
ouvrir `http://GATEWAY_PUBLIC_IP:3000` depuis le réseau administrateur
défini dans `teacher_ssh_cidr`. Utiliser une IP ou un réseau précis pour ce CIDR.
L'adresse d'écoute peut être modifiée avec `monitoring_grafana_bind_address`.

Prometheus écoute uniquement sur `127.0.0.1` de la gateway.
Pour accéder à Prometheus, ou utiliser Grafana via un tunnel SSH :
Utiliser le compte SSH administrateur, généralement `ubuntu`, depuis le poste
enseignant (remplacer `GATEWAY_PUBLIC_IP`) :

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 ubuntu@GATEWAY_PUBLIC_IP
```

Ouvrir <http://localhost:3000> et se connecter avec `admin`. Le mot de passe
initial est généré une seule fois sur la gateway ; aucun secret n'est versionné :

```bash
ssh ubuntu@GATEWAY_PUBLIC_IP 'sudo cat /etc/grafana/admin-password'
```

Changer le mot de passe dans Grafana après la première connexion. Le fichier
conserve le mot de passe initial ; les changements ultérieurs sont stockés dans
la base Grafana et une réexécution d'Ansible ne réinitialise pas le compte.
Le tableau de bord **Platform / Plateforme Big Data** et sa source Prometheus
sont provisionnés automatiquement. Les modifications du tableau de bord se
font dans `ansible/roles/monitoring/files/platform-dashboard.json`.

Node Exporter écoute sur l'IP privée de chaque machine, port `9100`.
Blackbox Exporter (`9115`) et l'adaptateur Hadoop (`9116`) restent sur localhost.
Terraform autorise le port Grafana `3000` pour `teacher_ssh_cidr` uniquement.

## Ce qui est surveillé

- CPU, mémoire disponible et espace disque par machine.
- Disponibilité TCP : NameNode, ResourceManager, DataNode, NodeManager,
  historiques Spark/MapReduce, HBase, Hive Metastore, HiveServer2 et SSH gateway.
- HDFS : capacité totale/utilisée/libre, DataNodes actifs/morts et safe mode.
- YARN : applications actives/en attente, nœuds actifs/perdus/non sains,
  mémoire et cœurs disponibles/alloués.

Une sonde TCP confirme qu'un port répond ; elle ne garantit pas qu'une requête
Hive ou un job Spark réussira. L'adaptateur HDFS/YARN utilise les API du master
sur les ports `9870` et `8088`, avec un timeout de 5 secondes par API. Une API
inaccessible produit `hadoop_scrape_success=0` pour ce composant, sans réutiliser
ses anciennes valeurs. `/health` vérifie le processus de l'adaptateur ; consulter
`hadoop_scrape_success` pour la disponibilité réelle des API Hadoop.

## Rétention et alertes

Collecte et évaluation toutes les **30 secondes**. Prometheus conserve au maximum
**7 jours** ou **2 Go de blocs**, selon la première limite atteinte. Cette limite
n'inclut pas le WAL et les données en mémoire : prévoir de la marge disque sur
la gateway. Les données restent dans `/var/lib/prometheus/metrics2` et
`/var/lib/grafana` lors d'un redémarrage ou d'une réexécution d'Ansible.

Les règles détectent les collectes indisponibles et les services injoignables
(2 minutes), CPU > 90 % (10 minutes), mémoire/disque/HDFS libres < 10 %
(5 minutes), ainsi que les DataNodes morts (2 minutes).
Consulter les alertes sur <http://localhost:9090/alerts> ou dans le tableau de
bord. Les notifications externes nécessitent un Alertmanager existant ;
configurer `monitoring_alertmanager_targets` avec ses adresses. Aucun courriel
n'est envoyé par défaut.

Les paramètres sont dans `ansible/roles/monitoring/defaults/main.yml` et peuvent
être surchargés dans l'inventaire ou via un fichier `-e @monitoring-vars.yml` :

```yaml
monitoring_scrape_interval: 30s
monitoring_retention_time: 7d
monitoring_retention_size: 2GB
monitoring_extra_tcp_targets:
  - target: 10.0.0.20:5432
    service: postgresql
monitoring_alertmanager_targets: []
```

Après un changement du nombre de workers, régénérer l'inventaire Terraform puis
relancer `monitoring.yml` : les cibles suivent l'inventaire. Le monitoring reste
actif lors de `stop-services.yml` et signale donc les services arrêtés pour une
maintenance. Si toute la plateforme est arrêtée, le monitoring local l'est aussi.

## Vérifier et dépanner

```bash
cd infra-hadoop/scaleway/ansible
ansible gateway -b -m command -a 'systemctl status prometheus grafana-server prometheus-blackbox-exporter platform-hadoop-exporter'
ansible cluster -b -m command -a 'systemctl status prometheus-node-exporter'
ansible gateway -b -m command -a 'journalctl -u platform-hadoop-exporter -n 30 --no-pager'
```

Pour les tests locaux, Python, PyYAML, Jinja2 et `promtool` sont nécessaires.
`promtool` est fourni par le paquet Ubuntu `prometheus` :

```bash
python3 -m pip install -r infra-hadoop/scaleway/monitoring/requirements.txt
python3 -m unittest discover -s infra-hadoop/scaleway/monitoring -p 'test_*.py'
```

Le workflow `Monitoring validation` vérifie les réponses de l'adaptateur, les
configurations générées pour un et quatre workers, les règles Prometheus et
le déclenchement des alertes, ainsi que la syntaxe du playbook.
