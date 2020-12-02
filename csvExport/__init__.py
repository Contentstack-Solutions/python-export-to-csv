'''
Export entries to CSV file
oskar.eiriksson@contentstack.com
2020-12-02
'''
from datetime import datetime
# import collections
import pandas as pd
import flatdict
import cma
import config

def getEnvironments(apiKey, token, region):
    '''
    Creates a uid to name map for all environments in stack
    '''
    envDict = {}
    environments = cma.getAllEnvironments(apiKey, token, region)
    for environment in environments['environments']:
        envDict[environment['uid']] = environment['name']
    return envDict

# def flatten(d, parent_key='', sep='.'):
#     items = []
#     for k, v in d.items():
#         new_key = parent_key + sep + k if parent_key else k
#         if isinstance(v, collections.MutableMapping):
#             items.extend(flatten(v, new_key, sep=sep).items())
#         else:
#             items.append((new_key, v))
#     return dict(items)

def cleanEntries(entries, language, environments):
    '''
    Clean up workflow and environment info
    Flattening the dictionary as well
    '''
    entriesArr = []
    for entry in entries:
        if (language != entry['locale']) and not entry['publish_details']:
            continue # We don't need unpublished and unlocalized items
        envArr = []
        for environment in entry['publish_details']:
            envArr.append((environments[environment['environment']], environment['locale']))
        del entry['publish_details']
        workflow = ''
        if '_workflow' in entry:
            workflow = entry['_workflow']['name']
            del entry['_workflow']
        entry = flatdict.FlatterDict(entry)
        entry.set_delimiter('.')
        entry = dict(entry)
        entry['publish_details'] = envArr
        entry['_workflow'] = workflow
        entriesArr.append(entry)
    return entriesArr


def export(entries, contentType, language, apiKey, token, region):
    '''
    Start here
    '''
    entries = entries['entries']
    environments = getEnvironments(apiKey, token, region)
    entries = cleanEntries(entries, language, environments)
    df = pd.DataFrame(entries)
    # df = pd.json_normalize(entries, sep='.')
    now = datetime.now()
    strNow = now.strftime("%d-%m-%Y-%H-%M-%S")
    fileName = config.dataRootFolder + contentType + '_' + language + '_export_' + strNow + '.csv'
    df.to_csv(fileName, index=False)
    config.logging.info('{}Finished Export to File: {}{}'.format(config.BOLD, fileName, config.END))
    return True
