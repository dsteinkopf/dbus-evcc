import configparser
import re
import unittest

from evcc_service_loader import REPO_CONFIG, SERVICE_SOURCE, new_service_without_dbus, parse_config


class ConfigValueTest(unittest.TestCase):
    def setUp(self):
        self.service = new_service_without_dbus()

    def test_repo_config_contains_every_value_the_service_reads(self):
        with open(SERVICE_SOURCE, encoding="utf-8") as source:
            used = set(re.findall(r"_getConfigValue\(config, '(\w+)', '(\w+)'", source.read()))
        config = configparser.ConfigParser()
        config.read(REPO_CONFIG)

        self.assertTrue(used)
        missing = [(section, key) for section, key in sorted(used) if not config.has_option(section, key)]
        self.assertEqual(missing, [])

    def test_missing_key_names_section_key_and_file(self):
        config = parse_config("[DEFAULT]\nAccessType = OnPremise\n")

        with self.assertRaises(ValueError) as raised:
            self.service._getConfigValue(config, "DEFAULT", "HttpTimeout")

        self.assertEqual(
            str(raised.exception),
            f"Missing config value [DEFAULT] HttpTimeout in {REPO_CONFIG}")

    def test_missing_section_is_reported_like_a_missing_key(self):
        config = parse_config("[DEFAULT]\nAccessType = OnPremise\n")

        with self.assertRaisesRegex(ValueError, r"Missing config value \[ONPREMISE\] Host"):
            self.service._getConfigValue(config, "ONPREMISE", "Host")

    def test_missing_file_is_reported_like_a_missing_key(self):
        with self.assertRaisesRegex(ValueError, r"Missing config value \[DEFAULT\] Deviceinstance"):
            self.service._getConfigValue(configparser.ConfigParser(), "DEFAULT", "Deviceinstance")

    def test_wrong_type_names_value_and_expected_type(self):
        config = parse_config("[DEFAULT]\nHttpTimeout = abc\n")

        with self.assertRaises(ValueError) as raised:
            self.service._getConfigValue(config, "DEFAULT", "HttpTimeout", float)

        self.assertEqual(
            str(raised.exception),
            f"Invalid config value [DEFAULT] HttpTimeout = 'abc' in {REPO_CONFIG}: expected float")

    def test_value_is_converted_to_requested_type(self):
        config = parse_config("[DEFAULT]\nStaticVoltage = 230\nHttpTimeout = 2.5\n")

        self.assertEqual(self.service._getConfigValue(config, "DEFAULT", "StaticVoltage", int), 230)
        self.assertEqual(self.service._getConfigValue(config, "DEFAULT", "HttpTimeout", float), 2.5)
        self.assertEqual(self.service._getConfigValue(config, "DEFAULT", "StaticVoltage"), "230")

    def test_empty_sign_of_life_interval_disables_it(self):
        self.service._getConfig = lambda: parse_config("[DEFAULT]\nSignOfLifeLog =\n")

        self.assertEqual(self.service._getSignOfLifeInterval(), 0)

    def test_sign_of_life_interval_is_read_as_int(self):
        self.service._getConfig = lambda: parse_config("[DEFAULT]\nSignOfLifeLog = 7\n")

        self.assertEqual(self.service._getSignOfLifeInterval(), 7)

    def test_status_url_is_built_from_host(self):
        self.service._getConfig = lambda: parse_config(
            "[DEFAULT]\nAccessType = OnPremise\n[ONPREMISE]\nHost = evcc.example:7070\n")

        self.assertEqual(self.service._getEvccChargerStatusUrl(), "http://evcc.example:7070/api/state")

    def test_unsupported_access_type_is_rejected(self):
        self.service._getConfig = lambda: parse_config("[DEFAULT]\nAccessType = Cloud\n")

        with self.assertRaisesRegex(ValueError, "AccessType Cloud is not supported"):
            self.service._getEvccChargerStatusUrl()


if __name__ == "__main__":
    unittest.main()
