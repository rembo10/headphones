# import os
# import mock
from unittestcompat import TestCase  # , TestArgs
from testenv import DRIVER
# from selenium.webdriver.common.keys import Keys


class ConfigTest(TestCase):

    def setUp(self):
        self.driver = DRIVER

    def test_config_open(self):
        """ SELENIUM: open config """
        driver = self.driver
        driver.get("http://localhost:8181/config")
        self.assertIn("Headphones - Settings", driver.title)

    def tearDown(self):
        self.driver.close()
        self.driver.quit()

if __name__ == "__main__":
    driver = DRIVER
    driver.get("http://localhost:8181/config")
    print driver.title
    print "expected:", "Headphones - Settings"
    driver.close()
