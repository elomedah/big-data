"""Expose HDFS NameNode JMX and YARN REST gauges without third-party packages."""
import json
import logging
import math
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen


def hdfs_metrics(document):
    bean = next(bean for bean in document['beans']
                if bean['name'] == 'Hadoop:service=NameNode,name=NameNodeInfo')
    return {
        'hadoop_hdfs_total_bytes': bean['Total'],
        'hadoop_hdfs_used_bytes': bean['Used'],
        'hadoop_hdfs_free_bytes': bean['Free'],
        'hadoop_hdfs_live_nodes': len(json.loads(bean['LiveNodes'])),
        'hadoop_hdfs_dead_nodes': len(json.loads(bean['DeadNodes'])),
        'hadoop_hdfs_safemode': int(bool(bean['Safemode'])),
    }


def yarn_metrics(document):
    metrics = document['clusterMetrics']
    fields = {
        'apps_running': 'appsRunning',
        'apps_pending': 'appsPending',
        'active_nodes': 'activeNodes',
        'lost_nodes': 'lostNodes',
        'unhealthy_nodes': 'unhealthyNodes',
        'allocated_memory_bytes': 'allocatedMB',
        'available_memory_bytes': 'availableMB',
        'total_memory_bytes': 'totalMB',
        'allocated_vcores': 'allocatedVirtualCores',
        'available_vcores': 'availableVirtualCores',
    }
    return {'hadoop_yarn_' + name: metrics[field] * (1024 ** 2 if name.endswith('_bytes') else 1)
            for name, field in fields.items()}


def render_gauges(metrics):
    lines = []
    for name, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('Invalid gauge: ' + name)
        lines.extend([f'# TYPE {name} gauge', f'{name} {value}'])
    return lines


def collect(config, fetch=None):
    if fetch is None:
        def fetch(url):
            with urlopen(url, timeout=config.get('timeout', 5)) as response:
                return json.load(response)

    master = config['master']
    sources = [
        ('hdfs', f'http://{master}:9870/jmx?qry=Hadoop:service=NameNode,name=NameNodeInfo', hdfs_metrics),
        ('yarn', f'http://{master}:8088/ws/v1/cluster/metrics', yarn_metrics),
    ]
    lines = ['# TYPE hadoop_scrape_success gauge']
    for component, url, convert in sources:
        try:
            # Only emit a component's metrics after validating the entire response.
            gauges = render_gauges(convert(fetch(url)))
        except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
            logging.warning('%s metrics unavailable: %s', component, exc)
            lines.append(f'hadoop_scrape_success{{component="{component}"}} 0')
        else:
            lines.append(f'hadoop_scrape_success{{component="{component}"}} 1')
            lines.extend(gauges)
    return '\n'.join(lines) + '\n'


def handler_for(config):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                data, content_type = b'ok\n', 'text/plain'
            elif self.path == '/metrics':
                data = collect(config).encode()
                content_type = 'text/plain; version=0.0.4; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass
    return Handler


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    with open(sys.argv[1], encoding='utf-8') as stream:
        config = json.load(stream)
    ThreadingHTTPServer(('127.0.0.1', int(config['port'])), handler_for(config)).serve_forever()
