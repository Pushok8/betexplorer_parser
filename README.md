# Betexplorer parser on Python 3.9.0
------------------------------
This script parses the required data defined in a make_pattern_xlsx module in a COLIMNS variable and outputs in Match_Statistic.xlsx file with various styles. If this file is not exist, script automatically to create patter xlsx file. First, the parser receives a date range from the user (beginning or end of YYYY-MM-DD) and receives a list of matches for each day between the date interval specified by the user. Then the parser iterates over the received links to the match receives data about the match by reference, writes it to Match_Statistic.xlsx and saves it.
--------------
### Installing
--------------
In order to start the parser, you need to enter `pip install -r requirements.txt`.
It is important that the virtual environment be in python 3.9, because the parser uses the functionality added in the new version of python.
And in console to write `python main.py`.
