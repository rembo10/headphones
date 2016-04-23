import os
import datetime
from selenium import webdriver

DRIVER = None
timestamp_str = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
tunnel_name = 'custom'

ci_travis = ("TRAVIS" in os.environ) and (os.environ["TRAVIS"] == "true")

use_sauce = ci_travis
use_sauce = True

caps = {
    "browserName": "firefox",
    "platform" : "Linux",
    "version" : "45.0",
}

caps = {
    "browserName": "safari",
    "platform": "OS X 10.11",
    "version": "9.0",
}

caps["recordVideo"] = False
caps["recordScreenshots"] = True
caps["screenResolution"] = "1024x768"

caps["tunnel-identifier"] = tunnel_name
caps["name"] = tunnel_name + '-name-' + timestamp_str
caps["build"] = tunnel_name + '-build-' + timestamp_str
caps["tags"] = tunnel_name + '-tags-' + timestamp_str

if ci_travis:
    caps["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
    caps["name"] = os.environ["TRAVIS_BRANCH"] + "-" + os.environ["TRAVIS_BUILD_NUMBER"]
    caps["build"] = os.environ["TRAVIS_BUILD_NUMBER"]
    caps["tags"] = [os.environ["TRAVIS_PYTHON_VERSION"], "CI"]

if use_sauce:
    username = os.environ["SAUCE_USERNAME"]
    access_key = os.environ["SAUCE_ACCESS_KEY"]

    hub_url = "%s:%s@localhost:4445" % (username, access_key)
    DRIVER = webdriver.Remote(desired_capabilities=caps, command_executor="http://%s/wd/hub" % hub_url)
else:
    DRIVER = webdriver.Firefox()
