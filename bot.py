# -*- coding: utf-8 -*-

from random import randrange
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from urllib3.exceptions import MaxRetryError
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

        # Name of server owner. Will be used to find secret key
        self._server_owner = "Mark Mandocdoc"

        # Max number of praises to skip until next refresh.
        # During 'do_update()', an attempt is made to add praise.
        # If praise exists, 'duplicate_count' increases by one.
        # 'do_update()' ends when count is equal to threshold
        self._duplicate_threshold = 3

        # Before scraping, search results are refreshed with new
        # entries. Refresh time is a random number of minutes
        # between '_refresh_minutes_low' and '_refresh_minutes_high'.
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
        while self.gui.is_running:
            try:
                search_input_field = self.driver.find_element_by_xpath("//input[@id='searchInputField']")
                search_input_field.clear()
                search_input_field.send_keys('#secret_key')
                search_input_field.send_keys(Keys.ENTER)
            except NoSuchElementException:
                self.gui.log("Error: Search bar not found. Retrying in 1 second ...\n")
                time.sleep(1)
                continue
            except AttributeError:
                self.gui.log("Error: Secret key initialization failed. Element not found.\n")
                return
            except WebDriverException:
                self.gui.log("Error: Secret key initialization failed. Chrome not reachable.\n")
                return
            break

        while self.gui.is_running:
            try:
                if not self.gui.log("Initializing secret key ... "):
                    return
                search_result_text = self.driver.find_element_by_xpath(
                    "//div[@class='search-content']//span[contains(text(),'" + self._server_owner + "')]"
                    "/../..//div[contains(@class,'search-chat-body')]").text
                self._secret_key = search_result_text.split("#secret_key:")[1]
            except NoSuchElementException:
                self.gui.log("failure\n", False)
                self.gui.log("Error: Secret key not found. Retrying in 1 second ...\n")
                time.sleep(1)
                continue
            except AttributeError:
                self.gui.log("failure\n", False)
                self.gui.log("Error: Secret key private message not found.\n")
                return
            except NoSuchWindowException:
                self.gui.log("failure\n", False)
                self.gui.log("Error: Window closed before secret key can be located.\n")
                return
            except WebDriverException:
                self.gui.log("failure\n", False)
                self.gui.log("Error: Secret key could not be be initialized. Chrome not reachable.\n")
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
        except InvalidSessionIdException:
            self.gui.log("Praise verification failed. Invalid session ID. Stopping bot.\n")
            return False
        except NoSuchElementException:
            self.gui.log("Invalid Praise. Moving to next search result.\n")
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
            print_text = "Duplicate Praise. Moving to next search result.\n"
        elif r.content == "1":
            print_text = "New Praise. Database has been updated.\n"
        elif r.status_code != 200:
            print_text = "Error: Cannot connect to server.\n"
        else:
            print_text = "Error: Something bad happened.\n"

        self.gui.log(print_text)

        return r.content

    def do_update_time(self):
        """
        Update last refresh on web server. Fails if gui not running.
        """
        if not self.gui.is_running:
            return

        self.gui.log("Updating last refresh ... ")
        script = "update_time.php"
        parameters = "?s=" + self._secret_key
        r = requests.get(self._server_base + script + parameters, headers={"User-Agent": "Chrome"})
        if str(r.status_code) == "200":
            self.gui.log("successful\n", False)
        else:
            self.gui.log("failure\n", False)

    def do_refresh(self):
        """
        Refresh list of praises by performing search on Teams.
        Refresh performed to check if new praises have been
        given or if bot is unable to find search result elements.
        :return boolean False if exception thrown
        """
        try:
            self.gui.log("Updating search results ... ")
            search_input = self.driver.find_element_by_xpath("//input[@id='searchInputField']")
            search_input.clear()
            search_input.send_keys("got praise!")
            search_input.send_keys(Keys.ENTER)
            self.gui.log("successful\n", False)
        except NoSuchWindowException:
            self.gui.log("failure\n", False)
            self.gui.log("Error: Unable to refresh search results. Window has been closed.\n")
            return False
        except WebDriverException:
            self.gui.log("failure\n", False)
            self.gui.log("Error: Unable to refresh search results. Send keys failed.\n")
            return False
        except AttributeError:
            self.gui.log("failure\n", False)
            self.gui.log("Error: Unable to refresh search results. Search field not found.\n")
            return False
        return True

    def do_update(self):
        """
        Main automation logic. Search result entries clicked starting
        from most recent and moving down until 'duplicate_threshold'
        value reached. Will attempt to add praise if verified valid.
        After 'duplicate_threshold' reached, gui status loop started.
        :return boolean True if update completes successfully
        """
        duplicate_count = 0
        duplicate_threshold = self._duplicate_threshold
        search_result_index = 1
        search_result_max = 0

        # Refresh search results. If search results fail, return False.
        if not self.do_refresh():
            return

        # Element variables used for looping through search results
        praiser_name = ""
        text_value = ""

        while self.gui.is_running:

            while self.gui.is_running:
                try:

                    search_result = self.driver.find_element_by_xpath(
                        "//div[@class='search-content']/div[{}]/div[contains(@data-tid, 'search-content-item')]"
                        .format(search_result_index))
                    self.driver.execute_script("arguments[0].scrollIntoView();", search_result)

                    search_result.click()

                    search_result_name = self.driver.find_element_by_xpath(
                        "//div[@class='search-content']/div[{}]//div[contains(@class,'search-chat-entry-name-time')]"
                        "/span[contains(@class,'user-name')]".format(search_result_index)
                    )

                    # Full name of praiser taken from main full panel
                    praiser_name = str(search_result_name.text)

                    search_result_text = self.driver.find_element_by_xpath(
                        "//div[@class='search-content']/div[{}]"
                        "//div[contains(@class,'search-chat-body')]"
                        .format(search_result_index))

                    # UnicodeEncodeError exception found with character u'\u2019'
                    # Caused by casting search_result_text.text to string
                    text_value = search_result_text.text

                except MaxRetryError:
                    # Target machine actively refused connection
                    return
                except NoSuchWindowException:
                    self.gui.log("Error: Praise update failed. Window has been closed.\n")
                    return
                except WebDriverException:
                    self.gui.log("Error: Praise update failed. Chrome not reachable.\n")
                    return
                except AttributeError:
                    if not self.gui.log("Error: Could not reach element. Refreshing search results.\n"):
                        return
                    if not self.do_refresh():
                        return
                    continue

                # Break from while loop after selected message from left panel
                # search results successfully found in right panel
                break

            # Issue found with users marked for deletion
            # Need to remove the marked for deletion text in bracket
            # Partition used because no error thrown if pattern not found
            praiser_name = praiser_name.partition(" [Marked ")[0]

            # First name found in left panel search results
            praised_first_name = text_value.split()[0]

            # Issue found with first name having ellipses
            # Need to check for ellipses and remove if exists
            praised_first_name = praised_first_name.partition("...")[0]

            # Praise text value after "got praise!" string
            text_value = text_value.split(" got praise! ")[1]

            text_value = text_value.split(" {}".format(praised_first_name))[0]
            text_value_length = len(text_value)

            # Change text value length if too long or too short
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

            # Variables initialized before loop to suppress warnings
            # Element variables contain driver element objects
            praised_name = ""
            time_value = ""

            # While loop to verify 'praised_name' set successfully.
            # Variable required to add praise properly to server.
            while praised_name == "":
                # Order matters for the variables and xpath
                # Element must end with first name to get selected name
                try:

                    selected_element = self.driver.find_element_by_xpath(
                        "//div[@class='card-body']//div[@class='ac-container']//div[@class='ac-textBlock'][1]"
                        "/p[contains(text(),'{}')]/../../div"
                        "//p[contains(text(),'{}')]/../../div[3]"
                        "/p[contains(text(),'{}')]"
                        .format(praiser_name, text_value, praised_first_name)
                    )
                    praised_name = selected_element.text

                    time_element = selected_element.find_element_by_xpath(
                        "./../../../../../../../../../../../../../../../../../../../"
                        "/div/div/div/span[@data-tid='messageTimeStamp']")
                    time_value = time_element.get_attribute("title")

                    search_count_element = self.driver.find_elements_by_xpath("//div[@ng-repeat='item in sc.result']")
                    search_result_max = len(search_count_element)

                except NoSuchWindowException:
                    self.gui.log("Error: Selected praise scrape failed. Window has been closed.\n")
                    return
                except WebDriverException:
                    self.gui.log("Error: Selected praise scrape failed. Chrome not reachable.\n")
                    return
                except AttributeError:
                    self.gui.log("Error: Selected praise scrape failed. Element not found.\n")
                    return

            # Check if gui has been closed before continuing server calls
            if not self.gui.is_running:
                return

            # Initialize variable before if statements to suppress reference warning
            result = "0"

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
            if (search_result_index + 1) >= search_result_max:
                self.gui.log("Last praise found. Praise scraping stopped.\n")
                break

            search_result_index += 1

        # Update last updated time
        self.do_update_time()

        # Calculate next refresh time based on limits.
        # Random value between low and high used for countdown.
        seconds_low = self._refresh_minutes_low * 60
        seconds_high = self._refresh_minutes_high * 60
        num_seconds = randrange(seconds_low, seconds_high)

        self.gui.log("Next refresh in {} seconds\n".format(num_seconds))

        self.gui.countdown = num_seconds
        self.gui.countdown_max = num_seconds
        self.gui.start_refresh_countdown()

        return True

    def start_bot_loop(self):
        """
        Thread loop to keep thread alive. Uses gui.is_running
        variable to decide whether or not to stop looping. Will
        not run loop gui if secret key not initialized.
        """
        while self.gui.is_running:
            if self._secret_key == "":
                self.gui.log("Secret key not initialized. Stopping bot thread.\n")
                return
            if not self.is_open():
                self.gui.log("Chrome browser closed. Stopping bot thread.\n")
                return
            if self.gui.countdown > 0:
                time.sleep(1)
                continue
            if not self.do_update():
                break

    def is_open(self):
        """
        Check if browser open by checking if title available.
        Used in bot loop to end bot if browser closed by user.
        :return: boolean True if open False if not
        """
        try:
            if self.driver.title:
                return True
        except (NoSuchWindowException, AttributeError, InvalidSessionIdException, MaxRetryError, WebDriverException):
            return False

    def run(self):
        """
        Run method for bot threading object. Will remain alive
        while gui is alive using gui.is_running variable. When
        gui is no longer alive, run log reaches end and quits.
        """

        # Start bot console messages
        self.gui.update_progress_label("Initializing ...")
        self.gui.log("Starting bot ... successful\n")
        self.gui.log("Initializing chromedriver ... ")

        # Initialize chromedriver object
        # Will download required chromedriver
        self.chromedriver = Chromedriver()

        if not self.gui.log(str(self.chromedriver.version) + " installed\n", False):
            return

        # Initialize driver options using default profile to retain settings
        # Settings needed for Teams access after server owner logs in
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=" + os.getenv("LOCALAPPDATA") + "\\Google\\Chrome\\User Data")
        options.add_argument("user-profile=Default")

        # Initialize driver. If Chrome browser already open, catch
        # InvalidArgumentException and write error to log
        try:
            self.driver = webdriver.Chrome(self.chromedriver.filepath, chrome_options=options)
            self.driver.get(self._initial_page)
        except InvalidArgumentException:
            self.gui.log("Error: Close all Chrome browsers and restart application\n")
            self.gui.stop_bot()
            return
        except SessionNotCreatedException:
            self.gui.log("Error: Session not created. Driver failed to initialize\n")
            self.gui.stop_bot()
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

        # Signal gui bot is stopped
        # Changes Stop button to Start
        self.gui.stop_bot()
