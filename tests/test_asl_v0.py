import unittest

from core.settings import DEFAULT_SETTINGS


class ASLV0IsolationTests(unittest.TestCase):
    def test_asl_disabled_by_default(self):
        self.assertFalse(DEFAULT_SETTINGS.get("useAthenaSemanticLanguage", True))


if __name__ == "__main__":
    unittest.main()
