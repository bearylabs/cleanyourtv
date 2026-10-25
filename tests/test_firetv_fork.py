"""Fork-specific resource regressions; offline and independent of ADB."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class FireTvConfigTest(unittest.TestCase):
    def setUp(self):
        root = ET.parse(ROOT / 'launcher/app/src/main/res/values/config.xml').getroot()
        self.values = {node.attrib['name']: node for node in root if 'name' in node.attrib}

    def test_existing_dock_order_is_preserved(self):
        self.assertEqual([item.text for item in self.values['dock_apps']], [
            'com.netflix.ninja', 'com.amazon.firebat', 'com.amazon.firetv.youtube', 'com.disney.disneyplus'])

    def test_home_redirect_and_bottom_only_library_are_preserved(self):
        self.assertEqual(self.values['stock_home_redirect'].text, 'com.amazon.tv.launcher')
        self.assertEqual(self.values['app_library'].text, 'true')
        self.assertEqual(self.values['library_button'].text, 'false')
        self.assertEqual(list(self.values['top_bar_apps']), [])

    def test_new_options_do_not_silently_change_existing_behavior(self):
        for name in ('power_on_home', 'date_below_clock', 'library_ok_opens'):
            self.assertEqual(self.values[name].text, 'false', name)
        for name in ('dock_band', 'show_library_pill'):
            self.assertEqual(self.values[name].text, 'true', name)

    def test_hidden_tiles_are_still_cosmetic(self):
        hidden = {item.text for item in self.values['hidden_apps']}
        self.assertTrue({'com.amazon.spiderpork', 'com.amazon.firetv.troubleshooting',
                         'com.amazon.ssm', 'com.amazon.vizzini.ftvcds',
                         'com.android.providers.downloads.ui', 'com.amazon.minitv.android.app',
                         'com.amazon.ftv.profilepicker', 'com.amazon.tv.launcher'} <= hidden)
        self.assertNotIn('com.amazon.firebat', hidden)

    def test_no_launcher_network_permission(self):
        manifest = ET.parse(ROOT / 'launcher/app/src/main/AndroidManifest.xml').getroot()
        name = '{http://schemas.android.com/apk/res/android}name'
        self.assertNotIn('android.permission.INTERNET',
                         [item.attrib.get(name) for item in manifest.findall('uses-permission')])


if __name__ == '__main__':
    unittest.main()
