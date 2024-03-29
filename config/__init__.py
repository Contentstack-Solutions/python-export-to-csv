'''
oskar.eiriksson@contentstack.com
2020-09-28

Various config functions and variables user in both export and import scripts
'''
import os
from time import sleep
from datetime import datetime
import json
import logging
import inquirer
import requests
import cma

dataRootFolder = 'data/' # Relative path to the export root folder - Remember the slash at the end if you change this.
authTokenFile = 'authtoken.json'
logLevel = logging.INFO # Possible levels e.g.: DEBUG, ERROR, INFO
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logLevel)
cancelString = 'Cancel and Exit'

# Text formatting for terminal logs.
PURPLE = '\033[95m'
CYAN = '\033[96m'
DARKCYAN = '\033[36m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
WHITE = '\033[0;37m'
REDBG = '\033[0;41m'
GREENBG = '\033[0;42m'
END = '\033[0m'

def checkDir(folder):
    '''
    Checks if folder exists
    '''
    if not os.path.exists(folder):
        logging.info('Creating folder: ' + folder)
        os.makedirs(folder)
        return True
    return False

def yesNoQuestion(questionStr):
    '''
    Possibly reusable question - Default False answer value
    '''
    answer = inquirer.confirm(questionStr, default=False)
    return answer

def createFolder(name):
    '''
    Creates an export folder with name
    '''
    cont = [inquirer.Text('folderName', message="{}Give the export folder a name:{}".format(BOLD, END), default=name + ' - ' + str(datetime.now()))]
    folderName = inquirer.prompt(cont)['folderName'] + '/'
    return folderName

def defineFullFolderPath(folder, key):
    '''
    Reusable function getting the full path of export folders
    '''
    fullPath = folder['fullPath'] + folderNames[key]
    checkDir(fullPath)
    logging.debug('{}Full Folder Path Defined: {}{}'.format(YELLOW, fullPath, END))
    return fullPath

def defineFullFilePath(folder, key):
    '''
    Reusable function getting the full path of export files for everything
    '''
    fullPath = defineFullFolderPath(folder, key)
    filePath = fullPath + fileNames[key]
    logging.info('{}Full File Path Defined: {}{}'.format(YELLOW, filePath, END))
    return filePath

def writeToJsonFile(payload, filePath, overwrite=False):
    '''
    Takes dictionary and writes to .json file in the relevant folder
    '''
    if os.path.isfile(filePath) and not overwrite: # Not writing over file
        logging.info('File exists. Not overwriting ({})'.format(filePath))
        return False
    try:
        with open(filePath, 'w') as fp:
            json.dump(payload, fp)
        return True
    except Exception as e:
        logging.critical('{}Failed writing dictionary to file: {} - Error Message: {}{}'.format(RED, filePath, e, END))
        return False

def addToJsonFile(payload, filePath):
    '''
    Adding to JSON file
    Various export functions add to reporting file information about the export.
    Could be used for other files later when needed.
    '''
    if not os.path.isfile(filePath): # If file does not exist, we just create it.
        return writeToJsonFile(payload, filePath)
    try: # If it exists, we update it
        with open(filePath, "r+") as file:
            data = json.load(file)
            data.update(payload)
            file.seek(0)
            json.dump(data, file)
        return True
    except Exception as e:
        logging.error('{}Unable to update {}{}'.format(RED, filePath, END))
        logging.error('{}Error: {}{}'.format(RED, e, END))
        return False

def addToExportReport(key, value, folder):
    '''
    Used in many places to enrich the export report
    '''
    addToJsonFile({key:value}, folder + exportReportFile)

def readFromJsonFile(filePath):
    try:
        with open(filePath) as json_file:
            return json.load(json_file)
    except Exception as e:
        logging.critical('Failed reading from json file: '  + filePath + ' - ' + str(e))
        return False

def downloadFileToDisk(url, folder, fileName):
    '''
    Downloading asset file to local disk
    '''
    if os.path.isfile(folder + fileName): # Not writing over file
        logging.info('File exists. Not overwriting ({})'.format(folder + fileName))
        return True
    try:
        res = requests.get(url, allow_redirects=True)
        if res.status_code not in (200, 201):
            logging.error('{}Unable to download asset: {} from URL: {}{}'.format(RED, fileName, url, END))
            logging.error('{}Error Message: {} {}'.format(RED, res.text, END))
            return False
        write = open(folder + fileName, 'wb').write(res.content)
        if not write:
            logging.error('{}Unable write asset to disk: {}/{}{}'.format(RED, folder, fileName, END))
            return False
        logging.info('Asset downloaded: {}'.format(fileName))
        return True
    except Exception as e:
        logging.error('{}Unable to download asset: {} from URL: {}{}'.format(RED, fileName, url, END))
        logging.error('{}Error Message: {} {}'.format(RED, e, END))
        return False

def countFilesInFolder(folder):
    count = 0
    for path in os.listdir(folder):
        if os.path.isfile(os.path.join(folder, path)):
            count += 1
    return count

def countFoldersInFolder(folder):
    count = 0
    for path in os.listdir(folder):
        if os.path.isdir(os.path.join(folder, path)):
            count += 1
    return count

def structureReport(folder):
    '''
    Iterates all folders and generates 'crude' analytics to be pumped in report
    '''
    d = {}
    for key, _ in folderNames.items():
        if key not in ['assets', 'entries', 'folders']: # Those types are exported to more folders and/or files
            label = 'Number of {} Exported'.format(key)
            value = folder + folderNames[key]
            d[label] = countFilesInFolder(value)
    try:
        d['Number of Assets Exported'] = countFoldersInFolder(folder + folderNames['assets'])
        if os.path.isfile(folder + folderNames['folders'] + fileNames['folders']):
            d['Number of Asset Folders Exported'] = len(readFromJsonFile(folder + folderNames['folders'] + fileNames['folders'])['assets'])
        else:
            d['Number of Asset Folders Exported'] = 0
    except Exception:
        d['Number of Assets Exported'] = None
        d['Number of Asset Folders Exported'] = None
    d['Number of Content types with Exported Entries'] = countFoldersInFolder(folder + folderNames['entries'])
    d['Number of Entries Per Content Type and Language'] = {}
    for contentType in os.listdir(folder + folderNames['entries']):
        d['Number of Entries Per Content Type and Language'][contentType] = {}
        ctFolder = folder + folderNames['entries'] + contentType + '/'
        for f in os.listdir(ctFolder):
            lang = f.replace('.json', '')
            r = readFromJsonFile(ctFolder + f)
            d['Number of Entries Per Content Type and Language'][contentType][lang] = len(r['entries'])
    addToJsonFile({'Numbers':d}, folder + exportReportFile) # Adding our findings to the report
