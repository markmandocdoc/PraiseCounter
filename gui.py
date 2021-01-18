# -*- coding: utf-8 -*-

import tkMessageBox
from ttk import Progressbar, Style
from Tkinter import *
from bot import Bot
import threading
import datetime
# import ttk
import sys
import os


class Gui(threading.Thread):
    """
    Gui class contains tkinter gui attributes and logic.
    When gui closed, is_running flag set to false to end
    bot actions when possible. Gui remains open until
    bot thread reaches end of run and sets driver to None.
    """
    def __init__(self):
        threading.Thread.__init__(self)

        # Reference to bot object. Allows bi-directional
        # communication between gui and bot objects
        self.bot = None

        # Bot checks this variable to see status
        self.is_running = True
        self.secret_key_initialized = False

        # Integer value of time till next refresh of search results
        # Value is set after 'do_update()' completes scraping results.
        # Reduces by 1 every second in gui loop while gui is running.
        # If gui is no longer running, bot ends gui loop and thread.
        self.countdown = 0
        self.countdown_max = 0

        # Setup root
        self.root = Tk()
        self.root.geometry("+50+50")
        self.root.resizable(0, 0)
        self.root.title("Teams Praise Counter")
        self.root.after(100, self.change_icon)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self.confirm_quit)

        # Setup frame
        self.root.frame = Frame(self.root)
        self.root.frame.pack(expand=1, side="top", fill="x")

        self.progress_frame = Frame(self.root)
        self.progress_frame.pack(expand=1, side="top", fill="x")

        self.button_frame = Frame(self.root)
        self.button_frame.pack(expand=1, side="top", fill="x")

        # Console label
        self.console_label = Label(
            self.root.frame, text="Console: ", justify="left", anchor="w")

        # Console text area
        self.console_text_frame = Frame(self.root.frame)
        self.console_text_frame.pack(side="top", expand="yes", fill="x", padx=10, pady=(10, 10))

        # Vertical Scroll Bar
        self.console_y_scroll_bar = Scrollbar(self.console_text_frame)
        self.console_y_scroll_bar.pack(side="right", fill="y")

        # Set text area to text widget
        self.console_text_area = Text(
            self.console_text_frame, width=80, height=10,
            yscrollcommand=self.console_y_scroll_bar.set, font=("Helvetica", 7))
        self.console_text_area.pack(side="top")

        # Configure the scrollbars
        self.console_y_scroll_bar.config(command=self.console_text_area.yview)

        # Refresh timer progress bar
        self.progress_bar_style = Style(self.root)
        self.progress_bar_style.theme_use("default")
        self.progress_bar = None
        self.root.after(100, self.load_progress_bar)

        # Initialize buttons and status label - Settings, Status, Start
        self.settings_button = Button(
            self.button_frame, text="Settings", width=28, height=2, command=self.start_stop_bot)
        self.settings_button.pack(side="left", padx=(10, 5), pady=(10, 10), fill="x", expand=1)

        self.start_stop_button = Button(
            self.button_frame, text="Start", width=28, height=2, command=self.start_stop_bot)
        self.start_stop_button.pack(side="left", padx=(5, 10), pady=(10, 10), fill="x", expand=1)

    def load_progress_bar(self):
        """
        Load progress bar method used with root.after.
        If root.after not used, gui will not load.
        """
        self.progress_bar_style.layout(
            "progress_bar",
            [
                (
                    "progress_bar.trough",
                    {
                        "children": [
                            ("progress_bar.pbar", {"side": "left", "sticky": "ns"}),
                            ("progress_bar.label", {"sticky": ""})
                        ],
                        "sticky": "nswe",
                    }
                )
            ]
        )

        self.progress_bar = Progressbar(self.progress_frame, orient="horizontal", style="progress_bar")
        self.progress_bar.pack(expand=1, fill="x", side="left", padx=10, ipadx=3, ipady=3)
        self.progress_bar["value"] = 0

        self.progress_bar_style.configure(
            "progress_bar", background="deepskyblue", font=('Helvetica', 8),
            pbarrelief="flat", troughrelief="flat", troughcolor="ghostwhite")
        self.update_progress_label("Press Start to Launch Automation")

    def update_progress_bar(self, current_time, max_time):
        """
        Update progress bar using current and max time with percentage
        :param current_time: integer current time till refresh in seconds
        :param max_time: integer max time till refresh in seconds
        """
        try:
            self.update_progress_label("{} seconds until next refresh".format(current_time))
            self.progress_bar["value"] = ((max_time-current_time)/float(max_time))*100
        except TclError:
            # Invalid command name "configure" for progress_bar["value"]
            pass

    def update_progress_label(self, text):
        """
        Wrapper used to call actual method using root.after
        :param text: string text used for progress label
        """
        self.root.after(100, lambda: self.update_progress_label_after(text))

    def update_progress_label_after(self, text):
        """
        Set progress bar label text. Must be called using root.after
        :param text: string text used for progress label
        """
        # Spaces added after text to center string on progress bar
        self.progress_bar_style.configure("progress_bar", text="{}     ".format(text))

    def change_icon(self):
        """
        Change icon outside of main thread. If after is not used,
        application will hang when an icon change attempt is made
        """
        self.root.iconbitmap(self.resource_path("icon.ico"))

    @staticmethod
    def resource_path(relative_path):
        """
        When EXE generated, icon is bundled. When EXE executed, icon
        and other resources placed in temp folder. Function identifies
        whether to use current working directory or temp folder.
        :param relative_path: string relative path of file name
        :return: full path name of file including resource directory
        """
        if hasattr(sys, '_MEIPASS'):
            # noinspection PyProtectedMember
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def start_stop_bot(self):
        """
        Start or stop bot. Runtime error thrown if thread already started.
        """
        try:
            if self.bot.is_open():

                # Not in 'stop_bot()' to allow faster disabling of button
                self.start_stop_button["text"] = "Stopping ..."
                self.disable(self.start_stop_button)

                # After disabling button, driver is closed. After driver
                # closes successfully, buttons enabled and text changed.
                self.root.after(10, self.stop_bot)

        except AttributeError:
            # Bot object set to none exception
            self.start_bot()
        except RuntimeError:
            # Thread already running exception
            pass

    def start_bot(self):
        """
        Method called by start_stop_button to start bot.
        It creates a new bot instance and sets circular
        reference in gui and bot objects. After bot has
        been started, button text changed to Stop.
        """
        self.bot = Bot()
        self.bot.gui = self
        self.bot.start()
        self.start_stop_button["text"] = "Stop"

    def stop_bot(self):
        """
        Method called by root.after to close driver and
        change button text from Stopping to Start. Called
        by root.after to allow root to update while closing.
        """
        try:
            self.bot.driver.quit()
            self.bot = None
            self.enable(self.start_stop_button)
            self.start_stop_button["text"] = "Start"
            self.update_progress_label("Automation stopped")
        except (AttributeError, TclError):
            # Bot has already been closed
            pass

    def start_refresh_countdown(self):
        self.root.after(100, self.refresh_countdown)

    def refresh_countdown(self):
        if self.bot is None:
            self.update_progress_label("Automation stopped")
            return

        if self.countdown > 0:
            self.countdown = self.countdown - 1
            self.root.after(100, lambda: self.update_progress_bar(self.countdown, self.countdown_max))
            self.root.after(1000, self.refresh_countdown)
        else:
            self.update_progress_label("Running refresh automation ...")

    def log(self, text, timestamp=True):
        """
        Add text to gui console log given string parameter.
        :param text: string text to be added to gui console
        :param timestamp: boolean is timestamp added to text
        :return: boolean True if gui is running, otherwise
            return False. If required in case gui has been
            closed and bot attempts to add to log.
        """
        if not self.is_running:
            return False

        # Add timestamp to beginning of text string
        if timestamp:
            text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " : " + text

        # Enable text area, add text, move cursor to end, disable text area
        self.enable(self.console_text_area)
        self.console_text_area.insert("insert", text)
        self.console_text_area.see("end")
        self.disable(self.console_text_area)

        return True

    @staticmethod
    def enable(widget):
        """
        Enables tkinter widget. Primarily used to enable
        text widgets to allow writing text into widget.
        :param widget: tkinter widget object
        """
        try:
            widget.config(state="normal")
        except tkinter.TclError:
            # Widget not found exception
            pass

    @staticmethod
    def disable(widget):
        """
        Disable tkinter widget. Primarily used to disable
        text widgets so user is not allowed to edit text area.
        :param widget: tkinter widget object
        """
        try:
            widget.config(state="disabled")
        except tkinter.TclError:
            # Widget not found exception
            pass

    def confirm_quit(self):
        """
        Handle gui close logic. Sets 'is_running' variable to
        False. When bot sees gui is no longer running, bot
        begins closing thread process and driver is set to None.
        Root is destroyed once bot thread has ended gracefully.
        """
        if tkMessageBox.askokcancel("Quit", "Do you really wish to quit?"):
            self.log("Closing application. Please wait ...")
            # Update required to show message in console log
            self.root.update()
            self.is_running = False
            try:
                # Wait for bot driver to close
                while self.bot.driver is not None:
                    pass
            except AttributeError:
                # Bot stopped and set to None
                pass
            self.root.destroy()

    def run(self):
        """
        Gui threading class start thread method.
        Performed when Threading.start() performed.
        """
        self.root.mainloop()
