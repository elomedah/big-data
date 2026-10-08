"""Render inventory-dependent configs and validate them with Prometheus tools."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'ansible/roles/monitoring'


def render_config(worker_count, **overrides):
    values = yaml.safe_load((ROOT / 'ansible/group_vars/all.yml').read_text())
    values.update(yaml.safe_load((ROLE / 'defaults/main.yml').read_text()))
    workers = ['worker-' + str(n) for n in range(1, worker_count + 1)]
    hosts = ['bastion', 'gateway', 'master'] + workers
    values.update({
        'groups': {'cluster': hosts, 'masters': ['master'], 'workers': workers, 'gateway': ['gateway']},
        'hostvars': {host: {'private_ip': '10.0.0.' + str(n)} for n, host in enumerate(hosts, 10)},
    })
    values.update(overrides)
    env = Environment(loader=FileSystemLoader(ROLE / 'templates'), undefined=StrictUndefined)
    env.filters['to_json'] = json.dumps
    return env.get_template('prometheus.yml.j2').render(**values)


class ConfigurationTests(unittest.TestCase):
    def test_all_inventory_hosts_and_services_are_monitored(self):
        for workers in [1, 4]:
            with self.subTest(workers=workers):
                config = yaml.safe_load(render_config(workers))
                jobs = {job['job_name']: job for job in config['scrape_configs']}
                nodes = jobs['node']['static_configs']
                self.assertEqual(len(nodes), workers + 3)
                self.assertEqual({item['labels']['node'] for item in nodes},
                                 {'bastion', 'gateway', 'master'} | {'worker-' + str(n) for n in range(1, workers + 1)})
                probes = jobs['services']['static_configs']
                self.assertEqual(len(probes), 8 + 3 * workers)
                self.assertTrue(all(item['targets'][0].startswith('10.0.0.') for item in probes))
                self.assertEqual(jobs['services']['relabel_configs'][-1]['replacement'], '127.0.0.1:9115')
                self.assertNotIn('alerting', config)

    def test_optional_alertmanager_and_extra_service(self):
        config = yaml.safe_load(render_config(1, monitoring_alertmanager_targets=['10.0.0.20:9093'],
                                             monitoring_extra_tcp_targets=[{'target': '10.0.0.30:1234', 'service': 'extra'}]))
        self.assertEqual(config['alerting']['alertmanagers'][0]['static_configs'][0]['targets'], ['10.0.0.20:9093'])
        probes = next(job for job in config['scrape_configs'] if job['job_name'] == 'services')['static_configs']
        self.assertEqual(probes[-1]['labels']['service'], 'extra')

    @unittest.skipUnless(shutil.which('promtool'), 'Install promtool to validate Prometheus syntax')
    def test_promtool_accepts_generated_configs_and_rules(self):
        subprocess.run(['promtool', 'check', 'rules', str(ROLE / 'files/alerts.yml')], check=True)
        subprocess.run(['promtool', 'test', 'rules', str(ROOT / 'monitoring/alert-tests.yml')], check=True)
        for workers in [1, 4]:
            with self.subTest(workers=workers), tempfile.TemporaryDirectory() as directory:
                config = yaml.safe_load(render_config(workers))
                config['rule_files'] = [str(ROLE / 'files/alerts.yml')]
                path = Path(directory) / 'prometheus.yml'
                path.write_text(yaml.safe_dump(config))
                subprocess.run(['promtool', 'check', 'config', str(path)], check=True)

        dashboard = json.loads((ROLE / 'files/platform-dashboard.json').read_text())
        queries = [target['expr'].replace('$node', '.*')
                   for panel in dashboard['panels'] for target in panel['targets']]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dashboard-queries.yml'
            path.write_text(yaml.safe_dump({'groups': [{'name': 'dashboard', 'rules': [
                {'record': 'dashboard_query_' + str(n), 'expr': query}
                for n, query in enumerate(queries)]}]}))
            subprocess.run(['promtool', 'check', 'rules', str(path)], check=True)

    def test_dashboard_uses_provisioned_datasource(self):
        dashboard = json.loads((ROLE / 'files/platform-dashboard.json').read_text())
        self.assertEqual(dashboard['uid'], 'big-data-platform')
        for panel in dashboard['panels']:
            self.assertEqual(panel['datasource']['uid'], 'platform-prometheus')
        provider = yaml.safe_load((ROLE / 'templates/dashboard-provider.yml.j2').read_text())
        self.assertEqual(provider['providers'][0]['options']['path'], '/var/lib/grafana/dashboards')


if __name__ == '__main__':
    unittest.main()
