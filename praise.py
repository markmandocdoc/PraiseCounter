# -*- coding: utf-8 -*-

from gui import Gui


def main():
    """
    Praise Counter main module
    """

    # Initialize and run gui. Gui contains console and buttons.
    # Gui contains buttons to instantiate and start Bot object.
    # Gui and Bot object circular reference set when bot started.
    gui = Gui()
    gui.start()


if __name__ == '__main__':
    main()
