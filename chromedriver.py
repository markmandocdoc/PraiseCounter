# -*- coding: utf-8 -*-

from io import BytesIO
import subprocess
import zipfile
import urllib2
import os
import re


class Chromedriver:
    """
    Chromedriver handles necessary logic to use correct
    chromedriver version required for installed Chrome
    browser. If incorrect chromedriver installed, correct
    chromedriver downloaded, unzipped, and installed based
    on current Chrome browser installed using registry data.
    """

    def __init__(self):
        # Expected filename to be used for chromedriver
        self.chromedriver_filename = "chromedriver.exe"

        # String chromedriver version
        # Initialized after chrome version identified
        self.version = ""

        # Filepath of chromedriver
        # If invalid chromedriver installed, correct chromedriver downloaded
        self.filepath = self.download_chromedriver(self)

    @staticmethod
    def get_chromedriver_url(version):
        """
        Generates the chromedriver download URL for Windows
        :param version: chromedriver version string
        :return: Download URL for chromedriver
        """
        base_url = "https://chromedriver.storage.googleapis.com/"
        return base_url + version + "/chromedriver_win32.zip"

    @staticmethod
    def check_version(binary, required_version):
        """
        Compare version of binary with expected version required
        :param binary: string filepath of binary to be checked
        :param required_version: string expected version of binary
        :return: boolean true if binary version matches required version
        """
        # Run shell command to get version of binary
        version = subprocess.check_output([binary, '-v'])

        # Regex on shell output to retrieve binary version
        # Group required since match returns match object
        version = re.match(r'.*?([\d.]+).*?', version.decode("utf-8")).group(1)

        if version == required_version:
            return True
        return False

    @staticmethod
    def get_chrome_version():
        """
        Get installed chrome version from registry using shell command
        :return: string version of chrome installed on client
        """
        process = subprocess.Popen(
            ["reg", "query", "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon", "/v", "version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True
        )

        # 0 index of communicate output is stdout
        chrome_version = process.communicate()[0].decode("UTF-8").strip().split()[-1]

        # End process used to retrieve Chrome version via shell commands
        process.kill()

        return chrome_version

    @staticmethod
    def get_major_version(version):
        """
        :param version: version in format w.x.y.z
        :return: major version clipped to format w
        """
        return version.split(".")[0]

    @staticmethod
    def get_matched_chromedriver_version(version):
        """
        Chromedriver version selection as per documentation found here:
        https://chromedriver.chromium.org/downloads/version-selection
        :param version: string chrome version
        :return: string chromedriver version
        """
        # Chromedriver download url
        url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_"

        # Adjusted version to append to download url
        url_version = version.rsplit(".", 1)[0]

        try:
            # URL output contains compatible chromedriver based on chrome version
            return urllib2.urlopen(url + url_version).read()
        except urllib2.URLError:
            print "Failed to retrieve selected chromedriver version"
            quit()

    @staticmethod
    def download_chromedriver(self):
        """
        Downloads, unzips and installs chromedriver.
        If a chromedriver binary is found in PATH it will be copied, otherwise downloaded.

        :return: The file path of chromedriver
        """

        # Get version of Chrome installed
        chrome_version = self.get_chrome_version()
        if not chrome_version:
            print "Chrome is not installed"
            quit()

        # Get corresponding Chromedriver based on Chrome version
        chromedriver_version = self.get_matched_chromedriver_version(chrome_version)
        if not chromedriver_version:
            print "Cannot find chromedriver for currently installed chrome version"
            quit()

        # Create directory to place downloaded Chromedriver
        chromedriver_dir = os.path.abspath(os.getcwd())

        # Created filepath based on directory and filename
        chromedriver_filepath = os.path.join(chromedriver_dir, self.chromedriver_filename)

        # If chromedriver.exe does not exist or
        # Current chromedriver version does not match required
        if not os.path.isfile(chromedriver_filepath) or \
                not self.check_version(chromedriver_filepath, chromedriver_version):
            print "Downloading chromedriver " + str(chromedriver_version)

            # If directory does not exist, create directory
            if not os.path.isdir(chromedriver_dir):
                os.makedirs(chromedriver_dir)

            # Create chromedriver url based on current version of chrome
            url = self.get_chromedriver_url(self, version=chromedriver_version)

            # Initialize response to resolve reference warning
            response = None

            try:
                response = urllib2.urlopen(url)
                if response.getcode() != 200:
                    raise urllib2.URLError("Not Found")
            except urllib2.URLError:
                print "Failed to download chromedriver archive from " + url
                quit()
            archive = BytesIO(response.read())

            # If file successfully downloaded, unzip contents
            with zipfile.ZipFile(archive) as zip_file:
                zip_file.extract(self.chromedriver_filename, chromedriver_dir)

        # Set chromedriver version after correct version identified
        self.version = chromedriver_version

        # If chromedriver not accessible, chmod file
        if not os.access(chromedriver_filepath, os.X_OK):
            os.chmod(chromedriver_filepath, 0o744)

        return chromedriver_filepath
