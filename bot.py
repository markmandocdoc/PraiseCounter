# -*- coding: utf-8 -*-

from random import randrange
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from chromedriver import Chromedriver
import threading
import requests
import time
import os


class Bot(threading.Thread):
    """
    Bot contains attributes and logic for Selenium automation.
    Attributes handle when the bot starts and stops. Chromedriver
    class used to validate and update installed chromedriver.
    Gui reference used to check if gui is still running.
    """

    def __init__(self):
        threading.Thread.__init__(self)

        # Bot settings
        # Initial page loaded by driver is Teams search page
        self._initial_page = "https://teams.microsoft.com/_#/apps/a2da8768-95d5-419e-9441-3b539865b118/search?q="

        # Url of web server containing PHP scripts
        self._server_base = "http://boxofmarkers.com/tools/praise/"

        # Integer value of time till next refresh of search results
        # Value is set after 'do_update()' completes scraping results.
        # Reduces by 1 every second in gui loop while gui is running.
        # If gui is no longer running, bot ends gui loop and thread.
        self._countdown = 0

        # Max number of praises to skip until next refresh.
        # During 'do_update()', an attempt is made to add praise.
        # If praise exists, 'duplicate_count' increases by one.
        # 'do_update()' ends when count is equal to threshold
        self._duplicate_threshold = 3

        # Before scraping, search results are refreshed with new
        # entries. Refresh time is a random number between
        # '_refresh_minutes_low' and '_refresh_minutes_high'.
        self._refresh_minutes_low = 7
        self._refresh_minutes_high = 10

        # Implicit wait for Selenium. Driver will attempt to contact
        # element for '_implicit_wait_seconds' amount of time until
        # the attempt is cancelled and exception is thrown.
        self._implicit_wait_seconds = 10

        # String used as a password to use PHP scripts on web server.
        # Stored in web server owners private messages on Teams and
        # scraped by bot using a key phrase in search bar.
        self._secret_key = ""

        # Reference to gui in bot. Allows checking status of each
        # other from within each others object. Used to check if
        # gui is still running and driver still exists.
        self.gui = None

        # Chromedriver object contains logic to check current
        # version and download new version if outdated
        self.chromedriver = None

        # Selenium driver to run automation
        self.driver = None

    def init_secret_key(self):
        """
        Initialize secret key. Secret key is used to allow access
        to web server. Without secret key, web server will not allow
        updating or adding to database. Secret key is found in
        private message of web server owner using #secret_key keyword.
        Refer to READ_ME for more information regarding setup.
        """
        search_input_field = ""
        while self.gui.is_running:
            try:
                search_input_field = self.driver.find_element_by_xpath("//input[@id='searchInputField']")
                search_input_field.clear()
                search_input_field.send_keys('#secret_key')
                search_input_field.send_keys(Keys.ENTER)
            except NoSuchElementException:
                self.gui.log("ERROR: Search bar not found. Retrying in 1 second ...\n")
                time.sleep(1)
                continue
            except AttributeError:
                self.gui.log("ERROR: Secret key initialization failed. Element not found.\n")
                return
            except WebDriverException:
                self.gui.log("ERROR: Secret key initialization failed. Chrome not reachable.\n")
                return
            break

        while self.gui.is_running:
            try:
                if not self.gui.log("Initializing secret key ... "):
                    return
                # Get secret API key
                search_result_text = self.driver.find_element_by_xpath(
                    '//div[@class="search-content"]//span[contains(text(),"Mark Mandocdoc")]'
                    '/../..//div[contains(@class,"search-chat-body")]').text
                self._secret_key = search_result_text.split('#secret_key:')[1]
            except NoSuchElementException:
                self.gui.log("failure\n", False)
                self.gui.log("ERROR: Secret key not found. Retrying in 1 second ...\n")
                time.sleep(1)
                continue
            except AttributeError:
                self.gui.log("failure\n", False)
                self.gui.log("ERROR: Secret key private message not found.\n")
                return
            except NoSuchWindowException:
                self.gui.log("failure\n", False)
                self.gui.log("ERROR: Window closed before secret key can be located.\n")
                return
            except WebDriverException:
                self.gui.log("failure\n", False)
                self.gui.log("ERROR: Secret key could not be be initialized. Chrome not reachable.\n")
                return
            break
        self.gui.secret_key_initialized = True
        self.gui.log("successful\n", False)

    def verify_praise(self, praiser_name, praised_name, praise_text):
        """
        Verify valid praise clicked on search panel. Uses xpath and
        input parameters to validate the clicked search result is
        a valid praise. Will not find xpath if praise invalid.
        :param praiser_name: string name of praiser
        :param praised_name: string name of praised
        :param praise_text: string partial sub string of praise
            text. Will be used to differentiate with other praises
        :return: boolean True if valid praise and False if invalid
        """
        try:
            self.driver.find_element_by_xpath(
                "//div[@class='card-body']//div[@class='ac-container']//div[@class='ac-textBlock'][1]"
                "/p[contains(text(), '{}')]/../../div[3]"
                "/p[contains(text(), '{}')]/../../div"
                "//p[contains(text(), '{}')]/../../../../../.."
                "//span[contains(text(),'Praise')]"
                .format(praiser_name, praised_name, praise_text)
            )
        except NoSuchElementException:
            self.gui.log("Invalid Praise. Moving to next message.\n")
            return False
        return True

    def do_add_praise(self, time_value, praiser_name, praised_name):
        """
        Send data to web server. Web server attempts to add praise
        information to database. Handles errors based on data received.
        Web server results returned and displayed in gui.
        :param time_value: string time of praise
        :param praiser_name: string first and last name of praiser
        :param praised_name: string first and last name of praised
        :return: string web server results. Returns 1 if successful
            add to database. Returns 2 if duplicate found.
        """
        server_base = self._server_base
        add_praise = "add_praise.php"
        parameters = "?s=" + self._secret_key + "&t=" + time_value + "&r=" + praiser_name + "&d=" + praised_name
        r = requests.get(server_base + add_praise + parameters, headers={"User-Agent": "Chrome"})

        if r.content == "2":
            print_text = "Duplicate Praise. Moving to next message.\n"
        elif r.content == "1":
            print_text = "New Praise. Database has been updated.\n"
        elif r.status_code != 200:
            print_text = "ERROR: Cannot connect to server.\n"
        else:
            print_text = "ERROR: Something bad happened.\n"

        self.gui.log(print_text)

        return r.content

    def do_update_time(self):
        """
        Update last refresh on web server. Fails if gui not running.
        """
        if not self.gui.is_running:
            return
        server_base = self._server_base
        script = "update_time.php"
        parameters = "?s=" + self._secret_key
        r = requests.get(server_base + script + parameters, headers={"User-Agent": "Chrome"})

        self.gui.log("Time updated - Status code: {}\n".format(r.status_code))

    def do_refresh(self):
        """
        Refresh list of praises by performing search on Teams.
        Refresh performed to check if new praises have been
        given or if bot is unable to find search result elements.
        :returns
        """
        try:
            self.gui.log("Refreshing ... ")
            search_input = self.driver.find_element_by_xpath("//input[@id='searchInputField']")
            search_input.clear()
            search_input.send_keys("got praise!")
            search_input.send_keys(Keys.ENTER)
            self.gui.log("successful\n", False)
        except NoSuchWindowException:
            self.gui.log("failure\n", False)
            self.gui.log("ERROR: Unable to refresh search results. Window has been closed.\n")
            return False
        except WebDriverException:
            self.gui.log("failure\n", False)
            self.gui.log("ERROR: Unable to refresh search results. Send keys failed.\n")
            return False
        except AttributeError:
            self.gui.log("failure\n", False)
            self.gui.log("ERROR: Unable to refresh search results. Search field not found.\n")
            return False
        return True

    def do_update(self):
        """
        Main automation logic. Search result entries clicked starting
        from most recent and moving down until 'duplicate_threshold'
        value reached. Will attempt to add praise if verified valid.
        After 'duplicate_threshold' reached, gui status loop started.
        :returns boolean True if update completes successfully
        """
        duplicate_count = 0
        duplicate_threshold = self._duplicate_threshold
        search_result_index = 1

        # Refresh search results. If search results fail, return False.
        if not self.do_refresh():
            return

        while self.gui.is_running:

            while self.gui.is_running:
                try:
                    search_result = self.driver.find_element_by_xpath(
                        "//div[@class='search-content']/div[{}]/div[contains(@data-tid, 'search-content-item')]"
                        .format(search_result_index))
                    self.driver.execute_script("arguments[0].scrollIntoView();", search_result)
                    search_result.click()
                except NoSuchWindowException:
                    self.gui.log("ERROR: Praise update failed. Window has been closed.\n")
                    return
                except Exception as e:
                    print "Exception: " + str(e)
                    if not self.gui.log("ERROR: Could not reach element. Refreshing ... \n"):
                        break
                    time.sleep(1)
                    self.do_refresh()
                    continue
                break
            if not self.gui.is_running:
                return

            search_result_name = self.driver.find_element_by_xpath(
                "//div[@class='search-content']/div[{}]//div[contains(@class,'search-chat-entry-name-time')]"
                "/span[contains(@class,'user-name')]".format(search_result_index)
            )

            # Full name of praiser taken from main full panel
            praiser_name = str(search_result_name.text)

            # Issue found with users marked for deletion
            # Need to remove the marked for deletion text in bracket
            # Partition used because no error thrown if pattern not found
            praiser_name = praiser_name.partition(" [Marked ")[0]

            search_result_text = self.driver.find_element_by_xpath(
                "//div[@class='search-content']/div[{}]"
                "//div[contains(@class,'search-chat-body')]"
                .format(search_result_index))

            # UnicodeEncodeError exception found with character u'\u2019'
            # Caused by casting search_result_text.text to string
            text_value = search_result_text.text

            # First name found in left panel search results
            praised_first_name = text_value.split()[0]

            # Issue found with first name having ellipses
            # Need to check for ellipses and remove if exists
            praised_first_name = praised_first_name.partition("...")[0]

            # Praise text value after "got praise!" string
            text_value = text_value.split(" got praise! ")[1]

            text_value = text_value.split(" {}".format(praised_first_name))[0]
            text_value_length = len(text_value)

            if text_value_length >= 20:
                text_value_length = 20
            elif 6 <= text_value_length < 20:
                text_value_length = text_value_length
            elif 0 < text_value_length <= 5:
                text_value_length = 5
            else:
                text_value_length = len(praised_first_name)

            text_value = text_value[0:text_value_length]

            # After clicking search result, verify message is a praise
            # If not, show error and continue down search results
            if not self.verify_praise(praiser_name, praised_first_name, text_value):
                search_result_index += 1
                continue

            # Praise name initialized before loop to suppress warning
            praised_name = ""
            selected_element = None
            while self.gui.is_running:
                # Order matters for the variables and xpath
                # Element must end with first name to get selected name
                selected_element = self.driver.find_element_by_xpath(
                    "//div[@class='card-body']//div[@class='ac-container']//div[@class='ac-textBlock'][1]"
                    "/p[contains(text(),'{}')]/../../div"
                    "//p[contains(text(),'{}')]/../../div[3]"
                    "/p[contains(text(),'{}')]"
                    .format(praiser_name, text_value, praised_first_name)
                )
                praised_name = selected_element.text
                if praised_name == "":
                    time.sleep(1)
                    continue
                else:
                    break
            if not self.gui.is_running:
                return

            time_element = selected_element.find_element_by_xpath(
                "./../../../../../../../../../../../../../../../../../../../"
                "/div/div/div/span[@data-tid='messageTimeStamp']")
            time_value = time_element.get_attribute("title")

            result = '0'

            # Split any praises that have multiple names
            if "," in praised_name:
                praised_names = str(praised_name).split(", ")
                for name in praised_names:
                    result = self.do_add_praise(time_value, praiser_name, name)
            else:
                result = self.do_add_praise(time_value, praiser_name, praised_name)

            # Increase duplicate count by 1 if duplicate
            if result == "2":
                duplicate_count += 1
            else:
                duplicate_count = 0

            # If duplicate count goes higher than threshold, stop
            if duplicate_count >= duplicate_threshold:
                break

            # Stop at the very first praise
            if praiser_name == "Zachary Blodgett" and praised_name == "Andre Le":
                break

            search_result_index += 1

        # Update last updated time
        self.do_update_time()

        # Calculate next refresh time based on attributes.
        # Random value between low and high used for countdown.
        seconds_low = self._refresh_minutes_low * 60
        seconds_high = self._refresh_minutes_high * 60
        num_seconds = randrange(seconds_low, seconds_high)
        self.gui.countdown = num_seconds
        self._countdown = num_seconds

        self.gui.log("Next refresh in {} seconds\n".format(num_seconds))

        return True

    def start_bot_loop(self):
        """
        Thread loop to keep thread alive. Uses gui.is_running
        variable to decide whether or not to stop looping. Will
        not run loop gui if secret key not initialized.
        """
        while self.gui.is_running:
            if self._secret_key == "":
                self.gui.log("ERROR: Secret key not initialized. Stopping bot thread.\n")
                return
            if self._countdown > 0:
                time.sleep(1)
                self._countdown = self._countdown - 1
                continue
            if not self.do_update():
                break

    def run(self):
        """
        Run method for bot threading object. Will remain alive
        while gui is alive using gui.is_running variable. When
        gui is no longer alive, run log reaches end and quits.
        """

        # Start bot console messages.
        # Temporary delay added to wait for gui to load.
        # Adding buttons will fix this later.
        time.sleep(1)
        if not self.gui.log("Initializing chromedriver ... "):
            return

        # Initialize chromedriver object
        # Will download required chromedriver
        self.chromedriver = Chromedriver()

        if not self.gui.log(str(self.chromedriver.version) + " installed\n", False):
            return

        # Initialize driver options
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=" + os.getenv("LOCALAPPDATA") + "\\Google\\Chrome\\User Data")
        options.add_argument("user-profile=Default")

        # Initialize driver. If Chrome browser already open, catch
        # InvalidArgumentException and write error to log
        try:
            self.driver = webdriver.Chrome(self.chromedriver.filepath, chrome_options=options)
            self.driver.get(self._initial_page)
        except InvalidArgumentException:
            self.gui.log("ERROR: Close all Chrome browsers and restart application\n")
            self.driver = None
            return
        except SessionNotCreatedException:
            self.driver = None
            self.gui.log("ERROR: Session not created. Driver failed to initialize\n")
            return

        # Check if gui running in case closed before setting value
        if self.gui.is_running:
            self.driver.implicitly_wait(self._implicit_wait_seconds)
        else:
            return

        # Init secret key needs to be performed before refresh.
        self.init_secret_key()

        # Start update process. Gui loop starts after secret key init.
        # Gui loop keeps run thread alive. Ends when gui not running.
        self.start_bot_loop()

        # When run ends, thread ends. Clean driver
        self.driver.quit()

        # Set driver to default state
        self.driver = None
