# TP en cours — Bash / WSL

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml
cd ../terraform

terraform plan \
  -var='cluster_size=large' \
  -var='worker_mode=active' \
  -var='gateway_mode=active' \
  -var='master_mode=active' \
  -var='worker_active_commercial_type=BASIC2-A4C-8G' \
  -var='master_active_commercial_type=BASIC2-A4C-16G' \
  -var='gateway_active_commercial_type=BASIC2-A4C-16G' \
  -var='master_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='gateway_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='worker_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='large_worker_data_size_gb=50' \
  -out=resize-active.tfplan

terraform show resize-active.tfplan
# Continuer uniquement si aucune VM, aucun disque et aucune IP ne sont remplacés ou supprimés.
terraform apply resize-active.tfplan
terraform output -raw ansible_inventory > ../ansible/inventory.ini

cd ../ansible
ansible-playbook start-services.yml
```

# Hors TP — Bash / WSL

```bash
cd infra-hadoop/scaleway/ansible
ansible-playbook stop-services.yml
cd ../terraform

terraform plan \
  -var='cluster_size=large' \
  -var='worker_mode=reduced' \
  -var='gateway_mode=reduced' \
  -var='master_mode=reduced' \
  -var='worker_active_commercial_type=BASIC2-A4C-16G' \
  -var='master_active_commercial_type=BASIC2-A4C-16G' \
  -var='gateway_active_commercial_type=BASIC2-A4C-16G' \
  -var='master_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='gateway_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='worker_reduced_commercial_type=BASIC2-A2C-4G' \
  -var='large_worker_data_size_gb=50' \
  -out=resize-reduced.tfplan

terraform show resize-reduced.tfplan
# Continuer uniquement si aucune VM, aucun disque et aucune IP ne sont remplacés ou supprimés.
terraform apply resize-reduced.tfplan
terraform output -raw ansible_inventory > ../ansible/inventory.ini
```

# Si le changement de type échoue — Bash / WSL

```bash
# Depuis infra-hadoop/scaleway/terraform ; CLI scw authentifiée.
terraform state show 'scaleway_instance_server.node["worker-4"]'

# Remplacer par l’UUID Scaleway de la VM, sans le préfixe fr-par-1/.
SERVER_ID='UUID_DE_LA_VM'
ZONE='fr-par-1'
TARGET_TYPE='BASIC2-A4C-8G'
# Pour master/gateway actifs : BASIC2-A4C-16G ; pour le mode réduit : DEV1-S.

scw instance server get "$SERVER_ID" zone="$ZONE"
scw instance server-type list zone="$ZONE"
scw instance server-type get zone="$ZONE"

scw instance server stop "$SERVER_ID" zone="$ZONE"
# Attendre que state soit stopped avant la commande update.
scw instance server get "$SERVER_ID" zone="$ZONE"
scw instance server update "$SERVER_ID" zone="$ZONE" commercial-type="$TARGET_TYPE"
# Si update échoue, arrêter ici et conserver le message Scaleway.
scw instance server start "$SERVER_ID" zone="$ZONE"
scw instance server get "$SERVER_ID" zone="$ZONE"

# Refaire le plan du mode choisi ci-dessus avant de l’appliquer.
# Ne pas utiliser terraform destroy, taint ou -replace avec le main.tf actuel.
```
