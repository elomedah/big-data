import importlib.util
import json
import unittest
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hadoop_exporter', ROOT / 'ansible/roles/monitoring/files/hadoop_exporter.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

HDFS = {'beans': [{
    'name': 'Hadoop:service=NameNode,name=NameNodeInfo',
    'Total': 1000, 'Used': 400, 'Free': 600,
    'LiveNodes': json.dumps({'worker-1': {}, 'worker-2': {}}),
    'DeadNodes': '{}', 'Safemode': '',
}]}
YARN = {'clusterMetrics': {
    'appsRunning': 2, 'appsPending': 1, 'activeNodes': 2,
    'lostNodes': 0, 'unhealthyNodes': 0, 'allocatedMB': 1024,
    'availableMB': 2048, 'totalMB': 3072,
    'allocatedVirtualCores': 1, 'availableVirtualCores': 3,
}}


class ExporterTests(unittest.TestCase):
    def test_realistic_api_responses_and_memory_conversion(self):
        fetch = lambda url: HDFS if '/jmx' in url else YARN
        metrics = exporter.collect({'master': '10.0.0.10'}, fetch)
        self.assertIn('hadoop_scrape_success{component="hdfs"} 1', metrics)
        self.assertIn('hadoop_hdfs_live_nodes 2', metrics)
        self.assertIn('hadoop_hdfs_free_bytes 600', metrics)
        self.assertIn('hadoop_yarn_allocated_memory_bytes 1073741824', metrics)
        self.assertIn('hadoop_yarn_apps_running 2', metrics)

    def test_failed_component_does_not_hide_healthy_component(self):
        def fetch(url):
            if '/jmx' in url:
                raise TimeoutError('offline')
            return YARN
        with self.assertLogs(level='WARNING'):
            metrics = exporter.collect({'master': '10.0.0.10'}, fetch)
        self.assertIn('hadoop_scrape_success{component="hdfs"} 0', metrics)
        self.assertNotIn('hadoop_hdfs_free_bytes', metrics)
        self.assertIn('hadoop_scrape_success{component="yarn"} 1', metrics)

    def test_malformed_responses_do_not_emit_partial_or_stale_gauges(self):
        for document in [{}, {'beans': []}, {'beans': [{'name': 'other'}]},
                         {'beans': [{**HDFS['beans'][0], 'Free': float('nan')}]}]:
            with self.subTest(document=document), self.assertLogs(level='WARNING'):
                metrics = exporter.collect({'master': '10.0.0.10'}, lambda url: document)
            self.assertNotIn('hadoop_hdfs_total_bytes', metrics)
            self.assertIn('hadoop_scrape_success{component="hdfs"} 0', metrics)

    def test_http_routes_and_prometheus_content_type(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), exporter.handler_for({'master': 'unused'}))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        base = f'http://127.0.0.1:{server.server_port}'
        with urlopen(base + '/health') as response:
            self.assertEqual(response.read(), b'ok\n')
        with patch.object(exporter, 'collect', return_value='test_metric 1\n'):
            with urlopen(base + '/metrics') as response:
                self.assertIn('version=0.0.4', response.headers['Content-Type'])
                self.assertEqual(response.read(), b'test_metric 1\n')
        with self.assertRaises(HTTPError) as error:
            urlopen(base + '/missing')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
