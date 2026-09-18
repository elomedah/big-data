import base64
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from request import apply_request, parse_request
from validate import load_keys, public_key, requested_login


def key(byte=1):
    return 'ssh-ed25519 ' + base64.b64encode(struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes([byte]) * 32).decode()


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'keys.yml'

    def write_keys(self, mapping):
        self.path.write_text(yaml.safe_dump({'student_ssh_keys': mapping}))
        return load_keys(self.path)

    def test_public_form_adds_without_replacing(self):
        name, keys = parse_request('### Username (nom.prenom)\n\ndupont.alice\n\n### Clés publiques SSH\n\n```text\n' + key(2) + ' comment\n```')
        result = apply_request({'dupont.alice': [key()]}, name, keys)
        self.assertEqual(result, {'dupont.alice': [key(), key(2)]})

    def test_append_idempotent_and_other_accounts_unchanged(self):
        old = {'dupont.alice': [key()], 'bob': [key(3)]}
        result = apply_request(old, 'dupont.alice', [key(), key(2)])
        self.assertEqual(result, {'dupont.alice': [key(), key(2)], 'bob': [key(3)]})
        self.assertEqual(old['dupont.alice'], [key()])

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


@unittest.skipIf(sys.platform == 'win32', 'Bastion synchronization uses Linux flock')
class SyncTests(unittest.TestCase):
    def test_existing_keys_preserved_and_failed_apply_retried(self):
        import sync
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'group_vars').mkdir()
            target = root / 'group_vars/student_ssh_keys.yml'
            target.write_text(yaml.safe_dump({'student_ssh_keys': {'alice': [key()], 'bob': [key(2)]}}))
            desired = yaml.safe_dump({'student_ssh_keys': {'alice': [key()]}}).encode()
            class Response:
                def __init__(self, data): self.data = data
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self): return json.dumps(self.data).encode()
            def fetch(request, **kwargs):
                return Response({'sha': 'abc123'} if '/commits/' in request.full_url else {'content': base64.b64encode(desired).decode()})
            config = {'ansible_dir': str(root), 'state_dir': str(root / 'state'), 'repository': 'example/repo', 'branch': 'main'}
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run', side_effect=RuntimeError('offline')):
                with self.assertRaises(RuntimeError): sync.synchronize(config)
            self.assertFalse((root / 'state/applied.sha256').exists())
            self.assertEqual(load_keys(target)['bob'], [key(2)])
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run') as run:
                sync.synchronize(config)
                sync.synchronize(config)
                self.assertEqual(run.call_count, 1)
            self.assertEqual(load_keys(root / 'state/applied.yml')['bob'], [key(2)])

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
            self.assertEqual(load_keys(target)['alice'], [key(), key(4)])

            desired = yaml.safe_dump({'student_ssh_keys': {'alice': []}}).encode()
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run'):
                sync.synchronize(config)
            self.assertEqual(load_keys(target)['alice'], [key(), key(4)])

            # Invalid remote data must not change the controller file or run Ansible.
            before = target.read_bytes()
            desired = b'student_ssh_keys: {root: []}'
            with patch.object(sync, 'urlopen', side_effect=fetch), patch.object(sync.subprocess, 'run') as run:
                with self.assertRaises(ValueError): sync.synchronize(config)
                run.assert_not_called()
            self.assertEqual(target.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
