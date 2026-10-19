# YARN web submission containment

Repository review found Hadoop 3.3.6 without configured Kerberos, an unrestricted
Nginx proxy to the ResourceManager on public port 8088, and a Terraform default
of `student_web_cidrs = ["0.0.0.0/0"]`. These are repository findings, not a
verification of the running EFREI servers. `dr.who` is Hadoop's default static web
identity; filtering that name alone is bypassable by claiming another identity.

The gateway template now permits only GET and HEAD on port 8088. Other methods
receive 403 before reaching YARN. This blocks public REST submissions, kills,
queue updates, and writes through proxied application UIs. Browsing and ordinary
Spark/YARN submissions from the SSH gateway via the private RPC endpoint remain
available. No Hadoop restart is required for this proxy change.

## Deploy

Copy the updated Ansible project to your usual controller/bastion first. From
its `infra-hadoop/scaleway/ansible` directory, using your EFREI inventory:

```bash
ansible-playbook -i inventory.ini harden-yarn-web.yml --check --diff
ansible-playbook -i inventory.ini harden-yarn-web.yml
```

The role runs `nginx -t` before reloading. No live deployment was performed as
part of the local repository edit.

After deployment, check that the dashboard still loads. Check method blocking
using a nonexistent path so verification cannot submit or kill an application:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://efrei.big-data-ing.fr:8088/cluster/apps
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://efrei.big-data-ing.fr:8088/__method_block_check__
curl -s -o /dev/null -w '%{http_code}\n' -X PUT http://efrei.big-data-ing.fr:8088/__method_block_check__
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE http://efrei.big-data-ing.fr:8088/__method_block_check__
```

Expected: dashboard 200, all three mutations 403. Submit a normal course job
from the SSH gateway to verify the private client path still works.

## Remaining boundaries

- Restrict `student_web_cidrs` in the actual Terraform variables to university
  or VPN CIDRs, review `terraform plan`, then apply the firewall change.
  This also protects the other exposed Hadoop web services, which this patch
  does not secure. The default/example permits access from the entire Internet.
- Confirm there is no alternate proxy or public route to master port 8088 or
  YARN RPC (normally 8032). The repository puts masters/workers on private
  addresses with an internal security group, but live rules must be checked.
- This is Internet-facing containment, not authenticated student identity.
  Internal clients can still claim identities in Hadoop simple mode. Use
  Kerberos and appropriate queue/service ACLs for enforced user identity.
- `core-site.xml.j2` also allows the Hadoop service user to impersonate every
  group from every host. Review and narrow that delegation as part of securing
  the internal cluster; do not treat the proxy patch as full cluster hardening.

## Investigate existing submissions

Preserve existing logs before rotation. On the gateway, search historical
`/var/log/nginx/access.log*` for `/ws/v1/cluster/apps` and the incident time.
New port-8088 requests go to `/var/log/nginx/yarn-access.log` (covered by Ubuntu's
usual `/var/log/nginx/*.log` rotation). The combined format records the peer IP,
timestamp with offset, method, URI, status and user agent. A further upstream
proxy can make that peer IP a proxy address; do not trust arbitrary forwarded
headers for attribution.

On the master, inspect the ResourceManager service journal and Hadoop daemon
logs for the exact application ID and `RMAuditLogger`. The RM may record the
gateway address because Nginx forwards requests. Correlate the gateway logs
with university VPN/DHCP/NAT records; an IP alone does not identify a student.
