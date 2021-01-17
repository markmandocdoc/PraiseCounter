# -*- coding: utf-8 -*-

import tkMessageBox
from Tkinter import *
from bot import Bot
import threading
import datetime
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

        # Setup root
        self.root = Tk()
        self.root.geometry("+50+50")
        self.root.resizable(0, 0)
        self.root.title("Teams Praise Counter")
        self.root.after(100, self.change_icon)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self.confirm_quit)

        # Setup frame
        self.root.frame = Frame(self.root, bd=0)
        self.root.frame.pack(expand=1, side="left")

        self.countdown = 0
        # self.status_label = Label(
        #     self.root.frame, text="Refresh in 300 seconds")
        # self.status_label.pack(side="top", padx=(0,0), pady=(5,0), ipadx=5, ipady=3, fill="x")

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

        # Initialize buttons and status label - Settings, Status, Start
        self.settings_button = Button(
            self.root.frame, text="Settings", width=28, height=2, command=self.start_stop_bot)
        self.settings_button.pack(side="left", padx=(10, 5), pady=(5, 10), fill="x")

        self.start_stop_button = Button(
            self.root.frame, text="Start", width=28, height=2, command=self.start_stop_bot)
        self.start_stop_button.pack(side="left", padx=(5, 10), pady=(5, 10), fill="x")

        # self.update_countdown()

        # Threading.start method to start thread
        # Will also execute run() when started
        # self.start()

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

    # def update_countdown(self):
    #     self.countdown = self.countdown - 1
    #     if self.countdown < 0:
    #         if self.secret_key_initialized:
    #             countdown_text = 'Running refresh. Please wait ...'
    #         else:
    #             countdown_text = 'Initializing secret key ...'
    #     else:
    #         countdown_text = '{} seconds until next refresh.'.format(self.countdown)
    #
    #     self.status_label.configure(text=countdown_text)
    #     self.root.after(1000, self.update_countdown)

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
        self.bot.driver.quit()
        self.bot = None
        self.enable(self.start_stop_button)
        self.start_stop_button["text"] = "Start"

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
            print "Widget not found"

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
            print "Widget not found"

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
