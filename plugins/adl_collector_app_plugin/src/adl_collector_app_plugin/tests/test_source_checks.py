"""
Tests for this plugin's side of the ingestion-diagnostic contracts
(wmo-raf/adl#235).

This plugin is the internal / push-fed archetype: observations are submitted
to ADL directly and "ingestion" is a local sweep of what landed. It therefore
implements none of the four external surfaces, and its entire answer is one
class attribute — which is exactly why that attribute is asserted here. Where
a plugin declines a surface there is normally nothing to test, because
asserting core's ``UNSUPPORTED`` default would pin *core's* behaviour from a
plugin repo.

No database is touched: the declaration is read off the class, and the import
guard parses source rather than running it.
"""

import ast
import os

from django.test import SimpleTestCase

from adl_collector_app_plugin.models import ManualObservationConnection


class ExternalSourceDeclarationTests(SimpleTestCase):
    """The whole external half of this plugin's retrofit."""

    def test_the_connection_declares_no_external_source(self):
        # Read off the class, not an instance: core reads it off whichever
        # polymorphic row it loaded, so the class is where it has to live
        self.assertIs(ManualObservationConnection.has_external_source, False)


class OlderCoreImportSafetyTests(SimpleTestCase):
    """The plugin must import cleanly on a core release that predates the
    source-check contracts, so nothing may import ``adl.core.source_checks``
    at module level."""

    # The canonical guard names its modules explicitly. This repo ships 34
    # across four sub-packages, so an enumerated list would silently go stale
    # the first time a module is added — the exact failure the guard exists to
    # prevent. It walks the package instead, skipping the two directories the
    # rule does not bind: tests never ship, and migrations import no contracts.
    EXCLUDED_DIRS = {"tests", "migrations", "__pycache__", "vue-pwa"}

    def shipped_modules(self):
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for root, dirs, files in os.walk(package_dir):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
            for name in sorted(files):
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    yield os.path.relpath(path, package_dir), path

    def test_no_module_level_import_of_source_checks(self):
        checked = 0
        for name, path in self.shipped_modules():
            checked += 1
            with open(path) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if node.col_offset != 0:
                    continue  # indented imports are lazy, inside a function
                names = [a.name for a in node.names]
                module = getattr(node, "module", "") or ""
                self.assertNotIn(
                    "adl.core.source_checks", [module] + names,
                    f"{name} imports adl.core.source_checks at module level")
        # A walk that silently found nothing would pass vacuously
        self.assertGreater(checked, 0, "no shipped modules were parsed")
