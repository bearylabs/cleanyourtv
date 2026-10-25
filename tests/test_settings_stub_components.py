"""Resource/UI wiring for the exact matching policy exercised by SystemSettingsTest."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / 'launcher/app/src/main/java/com/gathin/tvhome'


class SettingsStubComponentsTest(unittest.TestCase):
    def test_only_known_trampoline_is_listed_not_entire_vendor(self):
        resources = ET.parse(ROOT / 'launcher/app/src/main/res/values/config.xml').getroot()
        stubs = resources.find("string-array[@name='settings_stub_components']")
        self.assertIsNotNone(stubs)
        self.assertEqual([item.text for item in stubs],
                         ['com.amazon.tv.launcher/.ui.SettingsActivity'])
        fallback = resources.find("string-array[@name='settings_fallback_components']")
        self.assertIn('com.amazon.tv.launcher/com.amazon.tv.launcher.ui.MainSettingsActivity',
                      [item.text for item in fallback])

    def test_settings_reads_resource_and_uses_tested_exact_policy(self):
        source = (JAVA / 'SystemSettings.java').read_text()
        self.assertIn('R.array.settings_stub_components', source)
        self.assertIn('!isStub(resolved.activityInfo.packageName, resolved.activityInfo.name,', source)
        self.assertNotIn('com.amazon.tv.launcher', source)
        self.assertIn('return vendor != null ? vendor : standard', source)
