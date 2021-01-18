# Praise Counter

**Praise Counter** is a Python 2.0 GUI application used to scrape Microsoft Teams and count user praises. 
PHP scripts are used to communicate with a MySQL database while HTML, CSS, and Javascript are used 
to display a user front-end with values and statistics.

## Dependencies
- Selenium
- Requests
- Tkinter

## Setup
To set secret key:
1. Open Teams
2. Navigate to Calendar
3. Select Meet Now and start a meeting
4. Select Show Conversation
5. Enter secret key into chat using format:

```buildoutcfg
#secret_key:SECRET_KEY_USED_TO_ALLOW_WEB_SERVER_ACCESS
```

## Executable
To build EXE:
1. Install pyinstaller
2. Launch CMD and navigate to project directory
3. Execute the following command

```
pyinstaller --onefile --noconsole --icon=icon.ico --add-data "icon.ico;." praise.py

Description:
--onefile: Creates one exe containing all files
--noconsole: Disables console when launching exe
--icon: Sets EXE icon
--add-data: Bundles ICO image into executable
--add-data: If more data required, add tag again
```