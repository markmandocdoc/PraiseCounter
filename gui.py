# -*- coding: utf-8 -*-

import tkMessageBox
from Tkinter import *
from Tkinter import Tk
from Tkinter import Frame
from Tkinter import Label
from Tkinter import Scrollbar
from Tkinter import Text
import threading
import datetime
import sys
import os


class Gui(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        # Reference to bot object. Allows bi-directional
        # communication between gui and bot objects
        self.bot = None

        # Auto checks this variable to see status
        self.is_running = True
        self.secret_key_initialized = False

        # Setup frame
        self.root = Tk()
        self.root.geometry("+50+50")
        self.root.resizable(0, 0)
        self.root.title("Teams Praise Counter")
        self.root.after(100, self.change_icon)
        self.root.attributes('-topmost', True)
        self.root.protocol('WM_DELETE_WINDOW', self.confirm_quit)

        self.root.frame = Frame(self.root, bd=0)
        self.root.frame.pack(expand=1)

        # Console label
        self.console_label = Label(
            self.root.frame, text="Console: ", justify="left", anchor="w")

        # Console text area
        self.console_text_frame = Frame(self.root.frame)
        self.console_text_frame.pack(side="top", expand="yes", fill="x", padx=10, pady=(5, 10))

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

        # Initialize countdown variables
        self.countdown = 0
        self.countdown_label = Label(
            self.root.frame,
            text=""
        )
        self.countdown_label.pack(fill="x")

        self.update_countdown()

        # Threading.start method to start thread
        # Will also execute run() when started
        self.start()

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

    def update_countdown(self):
        self.countdown = self.countdown - 1
        if self.countdown < 0:
            if self.secret_key_initialized:
                countdown_text = 'Running refresh. Please wait ...'
            else:
                countdown_text = 'Initializing secret key ...'
        else:
            countdown_text = '{} seconds until next refresh.'.format(self.countdown)

        self.countdown_label.configure(text=countdown_text)
        self.root.after(1000, self.update_countdown)

    def log(self, text):
        if not self.is_running:
            return False

        text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " : " + text
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
        if tkMessageBox.askokcancel("Quit", "Do you really wish to quit?"):
            self.is_running = False
            self.root.destroy()

    def run(self):
        """
        Gui threading class start thread method.
        Performed when Threading.start() performed.
        """
        self.root.mainloop()
