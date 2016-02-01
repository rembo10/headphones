#!/usr/bin/env python

import os
import sys

# Ensure that we use the Headphones provided libraries.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))

import urlparse


def can_import(module):
    """
    Return True if a given module can be imported or not.
    """

    try:
        __import__(module)
    except ImportError:
        return False

    # Module can be imported
    return True


def check_installation():
    """
    Check if some core modules are available. Info is based on this topic:
    https://github.com/rembo10/headphones/issues/2210.
    """

    if can_import("requests"):
        import requests
        requests_version = requests.__version__
    else:
        requests_version = "no"

    if can_import("OpenSSL"):
        import OpenSSL
        openssl_version = OpenSSL.__version__
    else:
        openssl_version = "no"

    if can_import("cryptography"):
        import cryptography
        cryptography_version = cryptography.__version__
    else:
        cryptography_version = "no"

    if can_import("pyasn1"):
        import pyasn1
        pyasn1_version = pyasn1.__version__
    else:
        pyasn1_version = "no"

    if can_import("ndg.httpsclient"):
        from ndg import httpsclient
        ndg_version = httpsclient.__date__
    else:
        ndg_version = "no"

    # Print some system information.
    sys.stdout.write(
        "* Checking Python version: %s.%s.%s\n" % sys.version_info[:3])
    sys.stdout.write("* Operating system: %s\n" % sys.platform)

    sys.stdout.write(
        "* Checking if requests can be imported: %s\n" % requests_version)
    sys.stdout.write(
        "* Checking if pyOpenSSL is installed: %s\n" % openssl_version)
    sys.stdout.write(
        "* Checking if cryptography is installed: %s\n" % cryptography_version)
    sys.stdout.write(
        "* Checking if pyasn1 is installed: %s\n" % pyasn1_version)
    sys.stdout.write(
        "* Checking if ndg.httpsclient is installed: %s\n" % ndg_version)


def main():
    """
    Test if the current Headphones installation can connect to SNI-enabled
    servers.
    """

    # Read the URL to test.
    if len(sys.argv) == 1:
        url = "https://sni.velox.ch/"
    else:
        url = sys.argv[1]

    # Check if it is a HTTPS website.
    parts = urlparse.urlparse(url)

    if parts.scheme.lower() != "https":
        sys.stderr.write(
            "Error: provided URL does not start with https://\n")
        return 1

    # Gather information
    check_installation()

    # Do the request.
    if not can_import("requests"):
        sys.stderr.exit("Error: cannot continue without requests module!\n")
        return 1

    sys.stdout.write("* Performing request: %s\n" % url)

    import requests
    requests.packages.urllib3.disable_warnings()

    try:
        try:
            response = requests.get(url)
        except requests.exceptions.SSLError as e:
            sys.stdout.write(
                "- Server certificate seems invalid. I will disable "
                "certificate check and try again. You'll see the real "
                "exception if it fails again.\n")
            sys.stdout.write(
                "* Retrying request with certificate verification off.\n")
            response = requests.get(url)
    except Exception as e:
        sys.stdout.write(
            "- An error occured while performing the request. The "
            "exception was: %s\n" % e.message)
        sys.stdout.write(
            "- Consult the Troubleshooting wiki (https://github.com/"
            "rembo10/headphones/wiki/Troubleshooting) before you post an "
            "issue!")
        return 0

    # Verify the response.
    if response.status_code == 200:
        sys.stdout.write("+ Got a valid response. All seems OK!\n")
    else:
        sys.stdout.write(
            "- Server returned status code %s. Expected a status code 200.\n",
            response.status_code)
        sys.stdout.write(
            "- However, I was able to communicate to the server!\n")

# E.g. `python sni_test.py https://example.org'.
if __name__ == "__main__":
    sys.exit(main())
