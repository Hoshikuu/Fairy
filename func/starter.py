from os.path import isdir
from os import mkdir

def CheckDirs():
    if not isdir("csv"):
        mkdir("csv")

    if not isdir("database"):
        mkdir("database")