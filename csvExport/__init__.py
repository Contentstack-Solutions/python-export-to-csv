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
    if environments:
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

def cleanAssets(assets, apiKey, token, region):
    '''
    Cleaning up the Asset response from Contentstack
    Making it human readable
    '''
    environments = getEnvironments(apiKey, token, region)
    newAssets = []
    if assets:
        for asset in assets['assets']:
            del asset['ACL']
            envArr = []
            try:
                for environment in asset['publish_details']:
                    try:
                        envArr.append((environments[environment['environment']], environment['locale']))
                    except KeyError:
                        pass
            except KeyError:
                pass
            asset['publish_details'] = envArr
            newAssets.append(asset)
    return newAssets


def cleanOrgUsers(orgUsers, userMap, roleMap):
    '''
    Cleaning up User response from Contentstack
    Making it human readable, instead of uid's for example
    '''
    userList = []
    for user in orgUsers:
        try:
            invitedBy = userMap[user['invited_by']]
        except KeyError:
            invitedBy = 'System'
        u = {}
        u['Email'] = user['email']
        u['User UID'] = user['user_uid']
        u['Organization Role'] = determineUserOrgRole(user, roleMap)
        u['Status'] = user['status']
        u['Invited By'] = invitedBy
        u['Created Time'] = user['created_at']
        u['Updated Time'] = user['updated_at']
        userList.append(u)
    return userList

def getTime():
    now = datetime.now()
    return now.strftime("%d-%m-%Y-%H-%M-%S")

def getUserMap(users):
    '''
    Map Object userid:username
    '''
    userMap = {}
    for user in users:
        userMap[user['user_uid']] = user['email']
    userMap['System'] = 'System'
    return userMap

def getRoleMap(orgRoles):
    '''
    Map Object roleid:rolename
    '''
    roleMap = {}
    for role in orgRoles:
        roleMap[role['uid']] = role['name']
    return roleMap

def determineUserOrgRole(user, roleMap):
    '''
    Just determining the actual role for the user...
    Admin, Member or possibly the Owner
    '''
    roleName = 'No Role'
    roleUid = user.get('org_roles', None)
    if roleUid:
        roleUid = roleUid[0]
        roleName = roleMap[roleUid] # I don't know why this is of type list - Never has more than one item
    if 'is_owner' in user:
        if user['is_owner']: # == True:
            roleName = 'Owner'
    return roleName



def exportEntries(entries, contentType, language, apiKey, token, region, orgName, stackName):
    '''
    Entries Export Starts Here
    '''
    if entries:
        entries = entries['entries']
        environments = getEnvironments(apiKey, token, region)
        entries = cleanEntries(entries, language, environments)
        df = pd.DataFrame(entries)
        # df = pd.json_normalize(entries, sep='.')
        fileName = config.dataRootFolder + orgName + '_' + stackName + '_' + contentType + '_' + language + '_entries_export_' + getTime() + '.csv'
        df.to_csv(fileName, index=False)
        config.logging.info('{}Finished Exporting Entries to File: {}{}'.format(config.BOLD, fileName, config.END))
    return True

def exportOrgUsers(orgName, orgUsers, orgRoles):
    '''
    Org Users Export Starts Here
    '''
    orgUsers = orgUsers['shares']
    orgRoles = orgRoles['roles']
    fileName = config.dataRootFolder + orgName + '_users_export_' + getTime() + '.csv'
    userMap = getUserMap(orgUsers)
    roleMap = getRoleMap(orgRoles)
    userList = cleanOrgUsers(orgUsers, userMap, roleMap)
    df = pd.DataFrame(userList)
    df.to_csv(fileName, index=False)
    config.logging.info('{}Finished Exporting Organization Users ({}) to File: {}{}'.format(config.BOLD, orgName, fileName, config.END))
    return True

def exportAssets(assets, apiKey, token, region, orgName, stackName):
    '''
    Assets Export Starts Here
    '''
    fileName = config.dataRootFolder + orgName + '_' + stackName + '_assets_export_' + getTime() + '.csv'
    assets = cleanAssets(assets, apiKey, token, region)
    if assets:
        df = pd.DataFrame(assets)
        df.to_csv(fileName, index=False)
        config.logging.info('{}Finished Exporting Assets ({}) to File: {}{}'.format(config.BOLD, orgName, fileName, config.END))
    return True

def exportStacksAndRoles(orgName, stacks, token, region):
    '''
    Exports all Stacks and Users with Roles on those stacks
    '''
    csvList = []
    for stack in stacks['stacks']:
        users = cma.getAllStackUsers(stack['api_key'], token, region)['stack']['collaborators']
        userDict = {}
        for user in users:
            userDict[user['uid']] = user['email']
        csvList.append({'Stack Name': stack['name'], 'Stack API Key': stack['api_key'], 'User': userDict[stack['owner_uid']], 'Role': 'Owner'})
        roles = cma.getAllRoles(stack['api_key'], token, region)['roles']
        for role in roles:
            if 'users' in role:
                for userRole in role['users']:
                    csvList.append({'Stack Name': stack['name'], 'Stack API Key': stack['api_key'], 'User': userDict[userRole], 'Role': role['name']})
    
    fileName = config.dataRootFolder + orgName + '_usersandstackroles_export_' + getTime() + '.csv'
    df = pd.DataFrame(csvList)
    df.to_csv(fileName, index=False)
    config.logging.info('{}Finished Exporting Users and Stack Roles ({}) to File: {}{}'.format(config.BOLD, orgName, fileName, config.END))
