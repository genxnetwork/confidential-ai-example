"""Runtime identity checks reject mixed builds even when versions are identical."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from demo import runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'build/wheels').mkdir(parents=True)
        self.modules = {}
        self.manifest = {'schema_version': 1, 'pipeline_revision': 2, 'confido_root': str(self.root),
                         'sources': {x: x + '-source' for x in ('core', 'python', 'transport', 'application')},
                         'artifacts': {}}
        for name, module in [('confido-verifier', 'confido_verifier.confido_verifier'),
                             ('confai-transport', '_confai_transport._confai_transport')]:
            binary = self.root / (name + '.so'); binary.write_bytes(b'new binary')
            wheel = self.root / 'build/wheels' / (name + '.whl'); wheel.write_bytes(b'new wheel')
            info = {'version': '0.4.0', 'source_sha256': 'transport-source'} if name == 'confai-transport' else {
                'core': {'version': '0.4.0', 'pipeline_revision': 2, 'source_sha256': 'core-source'},
                'wrapper': {'version': '0.4.0', 'source_sha256': 'python-source'}}
            self.manifest['artifacts'][name] = {'binary_sha256': runtime.file_digest(binary),
                'wheel_sha256': runtime.file_digest(wheel), 'wheel': wheel.name, 'build_info': info}
            self.modules[module] = SimpleNamespace(__file__=str(binary), build_info=lambda info=info: info)
        (self.root / 'build/runtime.json').write_text(json.dumps(self.manifest))

    def check(self, sources=None, packaged=False):
        sources = sources or self.manifest['sources']
        with patch.object(runtime, 'ROOT', self.root), \
             patch.object(runtime.importlib, 'import_module', side_effect=self.modules.__getitem__), \
             patch.object(runtime, 'source_digest', side_effect=lambda root, scope: sources[scope]), \
             patch.dict(runtime.os.environ, {'CONFIDO_RUNTIME_MODE': 'packaged' if packaged else 'development'}):
            return runtime.ensure_runtime()

    def test_matching_build_and_packaged_build(self):
        self.assertEqual(self.check()['pipeline_revision'], 2)
        for p in (self.root / 'build/wheels').glob('*'): p.unlink()
        self.assertEqual(self.check(packaged=True)['pipeline_revision'], 2)
        with self.assertRaises(RuntimeError): self.check()

    def test_old_binary_with_same_version_and_new_manifest_is_rejected(self):
        Path(self.modules['confido_verifier.confido_verifier'].__file__).write_bytes(b'old binary')
        for packaged in (False, True):
            with self.assertRaisesRegex(RuntimeError, 'binary differs'):
                self.check(packaged=packaged)

    def test_old_manifest_wheel_and_binary_do_not_hide_changed_sources(self):
        for scope in ('core', 'python', 'transport', 'application'):
            sources = dict(self.manifest['sources']); sources[scope] = 'changed source'
            with self.assertRaisesRegex(RuntimeError, 'sources'):
                self.check(sources)

    def test_changes_during_build_do_not_publish_a_manifest(self):
        spec = importlib.util.spec_from_file_location('build_wheels', runtime.ROOT / 'scripts/build_wheels.py')
        build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
        before = (self.root / 'build/runtime.json').read_bytes()
        calls = [0]
        def build_step(*args, **kwargs): calls[0] += 1
        with patch.object(build, 'ROOT', self.root), \
             patch.object(build, 'source_digest', side_effect=lambda root, scope: f'{scope}-{calls[0]}'), \
             patch.object(build.subprocess, 'run', side_effect=build_step), \
             patch.object(build.sys, 'argv', ['build_wheels.py', '--confido-lib', str(self.root/'lib'), '--maturin', 'maturin']):
            with self.assertRaisesRegex(RuntimeError, 'Sources changed during build'):
                build.main()
        self.assertEqual((self.root / 'build/runtime.json').read_bytes(), before)
