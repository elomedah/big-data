import base64
import json
import struct
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import patch

import yaml

from request import apply_request, parse_request, main
from validate import load_keys, public_key, requested_login, merge_keys, school_keys_path, school


def key(byte=1):
    return 'ssh-ed25519 ' + base64.b64encode(struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes([byte]) * 32).decode()


class AccessTests(unittest.TestCase):
    def test_school_lists(self):
        self.assertTrue(school_keys_path('Ensitech').endswith('student_ssh_keys_ensitech.yml'))
        for invalid in ['other', 'irisette', 'monensitech', 'efrei2', 'Iris / Efrei', '', None]:
            with self.assertRaises(ValueError):
                school_keys_path(invalid)
        self.assertEqual(merge_keys([{'alice': [key()]}, {}, {'bob': [key(2)]}]),
                         {'alice': [key()], 'bob': [key(2)]})
        with self.assertRaises(ValueError):
            merge_keys([{'alice': [key()]}, {'alice': [key(2)]}])

    def test_school_recognized_in_free_text(self):
        for text, expected in [('École ENSITECH', 'ensitech'), ('Iris Paris', 'iris'),
                               ('Campus Efrei - Paris', 'efrei'), (' iris ', 'iris'),
                               ('Iris (IRIS)', 'iris')]:
            with self.subTest(text=text):
                self.assertEqual(school(text), expected)
                self.assertTrue(school_keys_path(text).endswith('student_ssh_keys_' + expected + '.yml'))

    def test_empty_school_list(self):
        self.assertEqual(self.write_keys({}), {})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'keys.yml'

    def write_keys(self, mapping):
        self.path.write_text(yaml.safe_dump({'student_ssh_keys': mapping}))
        return load_keys(self.path)

    def test_public_form_replaces_existing_keys(self):
        name, keys = parse_request('### Username (nom.prenom)\n\ndupont.alice\n\n### Clés publiques SSH\n\n```text\n' + key(2) + ' comment\n```')
        result = apply_request({'dupont.alice': [key()]}, name, keys)
        self.assertEqual(result, {'dupont.alice': [key(2)]})

    def test_replace_idempotent_and_other_accounts_unchanged(self):
        old = {'dupont.alice': [key()], 'bob': [key(3)]}
        result = apply_request(old, 'dupont.alice', [key(2), key(2)])
        self.assertEqual(result, {'dupont.alice': [key(2)], 'bob': [key(3)]})
        self.assertEqual(apply_request(result, 'dupont.alice', [key(2)]), result)
        self.assertEqual(old['dupont.alice'], [key()])

    def test_public_form_deduplicates_normalized_keys(self):
        body = '### Username (nom.prenom)\n\ndupont.alice\n\n### Clés publiques SSH\n\n'
        _, keys = parse_request(body + '\n'.join([key() + ' first', key() + ' second'] * 6))
        self.assertEqual(keys, [key()])
        with self.assertRaises(ValueError):
            parse_request(body + '\n'.join(key(i) for i in range(11)))
        with self.assertRaises(ValueError):
            parse_request(body)

    def test_new_student_without_registration(self):
        self.assertEqual(apply_request({}, 'dupont.alice', [key()]), {'dupont.alice': [key()]})

    def test_username_format(self):
        for name in ['alice', 'Dupont.alice', 'dupont.alicé', 'dupont.alice.anne', 'dupont alice', 'dupont.alice1', '-dupont.alice', 'dupont..alice', 'a' * 30 + '.bob']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                requested_login(name)
        self.assertEqual(requested_login('le-gall.jean-pierre'), 'le-gall.jean-pierre')

    def test_invalid_and_private_keys(self):
        for value in ['-----BEGIN OPENSSH PRIVATE KEY-----', 'ssh-ed25519 AAAA', 'command="id" ' + key(), key() + '\n' + key(2), 'ssh-rsa AAAA']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                public_key(value)

    def test_empty_key_list_is_valid(self):
        self.assertEqual(self.write_keys({'alice': []}), {'alice': []})

    def test_cross_account_duplicates(self):
        with self.assertRaises(ValueError):
            self.write_keys({'alice': [key() + ' first'], 'bob': [key() + ' second']})

    def test_reserved_and_injected_login(self):
        for name in ['root', 'teacher', 'hadoop', 'ubuntu', 'alice;id', '../alice', '-x']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.write_keys({name: [key()]})

    def test_reject_extra_ansible_variables_and_duplicate_yaml(self):
        for raw in ['student_ssh_keys: {alice: []}\nansible_connection: local', 'student_ssh_keys:\n  alice: []\n  alice: []']:
            self.path.write_text(raw)
            with self.assertRaises(ValueError):
                load_keys(self.path)

    def test_missing_form_fields(self):
        with self.assertRaises(ValueError):
            parse_request('### Opération\nAjouter')

    def test_invalid_request_is_explained_and_closed(self):
        event = Path(self.temp.name) / 'event.json'
        event.write_text(json.dumps({'issue': {'number': 42}}), encoding='utf-8')
        body = ('### Username (nom.prenom)\n\ndupont.alice\n\n'
                '### Clés publiques SSH\n\nssh-ed25519 AAAA')
        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(self.data).encode()
        with patch.dict('os.environ', {'GH_TOKEN': 'test', 'GITHUB_REPOSITORY': 'example/repo',
                                      'GITHUB_EVENT_PATH': str(event)}):
            with patch('request.urlopen', side_effect=[Response({'state': 'open', 'body': body}),
                                                      Response({}), Response({})]) as fetch:
                main()
            requests = [call.args[0] for call in fetch.call_args_list]
            self.assertEqual([request.method for request in requests], ['GET', 'POST', 'PATCH'])
            comment = json.loads(requests[1].data)['body']
            self.assertIn('clé SSH non acceptée', comment)
            self.assertIn('incomplète ou invalide', comment)
            self.assertIn('nouvelle demande', comment)
            self.assertEqual(json.loads(requests[2].data), {'state': 'closed', 'state_reason': 'not_planned'})
            self.assertTrue(requests[2].full_url.endswith('/issues/42'))
            with patch('request.urlopen', side_effect=HTTPError('url', 503, 'Unavailable', {}, None)) as fetch:
                with self.assertRaises(HTTPError):
                    main()
                self.assertEqual(fetch.call_count, 1)

    def test_already_registered_request_is_closed_without_pr(self):
        event = Path(self.temp.name) / 'event.json'
        event.write_text(json.dumps({'issue': {'number': 42}}), encoding='utf-8')
        body = ('### Username (nom.prenom)\n\ndupont.alice\n\n'
                '### Clés publiques SSH\n\n' + key() + '\n\n### École\n\nIris')
        content = base64.b64encode(yaml.safe_dump(
            {'student_ssh_keys': {'dupont.alice': [key()]}}).encode()).decode()

        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(self.data).encode()

        responses = [Response({'state': 'open', 'body': body}),
                     Response({'default_branch': 'main'}),
                     Response({'object': {'sha': 'abc123'}}),
                     Response({'content': content}), Response({}), Response({})]
        with patch.dict('os.environ', {'GH_TOKEN': 'test', 'GITHUB_REPOSITORY': 'example/repo',
                                      'GITHUB_EVENT_PATH': str(event)}):
            with patch('request.urlopen', side_effect=responses) as fetch:
                main()

        requests = [call.args[0] for call in fetch.call_args_list]
        self.assertEqual([request.method for request in requests],
                         ['GET', 'GET', 'GET', 'GET', 'POST', 'PATCH'])
        self.assertIn('déjà enregistrées', json.loads(requests[4].data)['body'])
        self.assertEqual(json.loads(requests[5].data),
                         {'state': 'closed', 'state_reason': 'completed'})
        self.assertTrue(requests[5].full_url.endswith('/issues/42'))


@unittest.skipIf(sys.platform == 'win32', 'Bastion synchronization uses Linux flock')
class SyncTests(unittest.TestCase):
    def test_keys_replaced_omitted_accounts_preserved_and_failed_apply_retried(self):
        import sync
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'group_vars').mkdir()
            target = root / 'group_vars/student_ssh_keys_iris.yml'
            target.write_text(yaml.safe_dump({'student_ssh_keys': {'alice': [key()], 'bob': [key(2)]}}))
            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key()]}}).encode()
            class Response:
                def __init__(self, data): self.data = data
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self): return json.dumps(self.data).encode()
            def fetch(request, **kwargs):
                if '/contents/' in request.full_url:
                    self.assertIn('student_ssh_keys_iris.yml', request.full_url)
                return Response({'sha': 'abc123'} if '/commits/' in request.full_url else {'content': base64.b64encode(desired).decode()})
            config = {'ansible_dir': str(root), 'state_dir': str(root / 'state'), 'student_school': 'iris', 'repository': 'example/repo', 'branch': 'main', 'ansible_playbook': '/opt/ansible/bin/ansible-playbook'}
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError): sync.synchronize(config)
            self.assertFalse((root / 'state/iris/applied.sha256').exists())
            self.assertEqual(load_keys(target)['bob'], [key(2)])
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run') as run:
                sync.synchronize(config)
                sync.synchronize(config)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0], ['/opt/ansible/bin/ansible-playbook', 'site.yml', '--tags', 'students', '-e', 'student_school=iris'])
            self.assertEqual(load_keys(root / 'state/iris/applied.yml')['bob'], [key(2)])

            # Keys from a partially failed run remain even if removed from Git.
            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key()], 'carol': [key(3)]}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError): sync.synchronize(config)
            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key()]}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run'):
                sync.synchronize(config)
            self.assertEqual(load_keys(target)['carol'], [key(3)])

            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key(4)]}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run'):
                sync.synchronize(config)
            self.assertEqual(load_keys(target)['alice'], [key(4)])
            self.assertEqual(load_keys(root / 'state/iris/applied.yml')['alice'], [key(4)])

            # A failed replacement retries without resurrecting old applied keys.
            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key(5)]}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError): sync.synchronize(config)
            self.assertEqual(load_keys(target)['alice'], [key(5)])
            self.assertEqual(load_keys(root / 'state/iris/applied.yml')['alice'], [key(4)])
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run') as run:
                sync.synchronize(config)
                sync.synchronize(config)
                self.assertEqual(run.call_count, 1)
            self.assertEqual(load_keys(target)['alice'], [key(5)])

            desired = yaml.safe_dump({'student_ssh_keys': {'alice': []}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run'):
                sync.synchronize(config)
            self.assertEqual(load_keys(target)['alice'], [])

            # Invalid remote data must not change the controller file or run Ansible.
            before = target.read_bytes()
            desired = b'student_ssh_keys: {root: []}'
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run') as run:
                with self.assertRaises(ValueError): sync.synchronize(config)
                run.assert_not_called()
            self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
