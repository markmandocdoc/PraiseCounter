# -*- coding: utf-8 -*-

from bot import Bot
from gui import Gui


def main():

    # Initialize and run gui. Gui contains console and buttons.
    gui = Gui()

    # Initialize and run bot. Bot contains Selenium automation.
    # Will also initialize circular reference between gui and bot
    # Circular reference required for gui and bot to communicate
    bot = Bot()

    # Initialize bot and gui references in each others object.
    # Allows bi-directional communication between bot and gui.
    gui.bot = bot
    bot.gui = gui

    # Start automation
    bot.start()

if __name__ == '__main__':
    main()
