import sys
from time import sleep
import inquirer
import cma
import config
import login
import csvExport

def restructureOrgs(auth):
    '''
    Restructuring the org payload to something easier
    '''
    orgDict = {}
    for org in auth['user']['organizations']:
        if org['enabled']: # No point in adding disabled orgs to this variable
            orgDict[org['name']] = {
                'uid': org['uid'],
            }
            if 'is_owner' in org:
                orgDict[org['name']]['isOwner'] = True
            else:
                orgDict[org['name']]['isOwner'] = False
    return orgDict

def restructureExportStacks(stacks):
    stackDict = {}
    for stack in stacks['stacks']:
        stackDict[stack['name']] = {
            'org': stack['org_uid'],
            'uid': stack['api_key'],
            'masterLocale': stack['master_locale']
        }
    return stackDict

def restructureCreatedStack(stack):
    stackDict = {
        'org': stack['stack']['org_uid'],
        'uid': stack['stack']['api_key'],
        'masterLocale': stack['stack']['master_locale']
    }
    return stackDict

def findOrg(orgObj):
    '''
    Choose Org
    '''
    try:
        orgList = []
        for name, value in orgObj.items():
            if value['isOwner']:
                name = name + ' (You are the owner)'
            orgList.append(name)
        orgList = sorted(orgList)
        orgList.append(config.cancelString)

        chooseOrg = [
            inquirer.List('chosenOrg',
                          message="{}Choose Organization to work on{}".format(config.BOLD, config.END),
                          choices=orgList,
                          ),
        ]
        orgName = inquirer.prompt(chooseOrg)['chosenOrg'].replace(' (You are the owner)', '')
        if orgName == config.cancelString:
            exitProgram()
        return orgObj[orgName]['uid'], orgName
    except TypeError:
        exitProgram()

def findStack(orgUid, authToken, region, action='EXPORT'):
    '''
    Choosing the org and finding the stack to either export from or import to
    '''
    try:
        stacks = cma.getAllStacks(cma.constructAuthTokenHeader(authToken), orgUid, region)
        stacks = restructureExportStacks(stacks)
        if action == 'EXPORT' or action == 'IMPORT CONTENT':
            stackList = []
        elif action == 'IMPORT':
            stackList = ['Create a new stack']
        unsortedList = []
        for name, _ in stacks.items():
            unsortedList.append(name)
        stackList = stackList + sorted(unsortedList) + [config.cancelString]
        chooseStack = [
            inquirer.List('chosenStack',
                          message="{}Choose Stack to work on ({}){}".format(config.BOLD, action, config.END),
                          choices=stackList,
                          ),
        ]
        stackName = inquirer.prompt(chooseStack)['chosenStack']
        if stackName == config.cancelString:
            exitProgram()
        return stackName, stacks[stackName]
    except TypeError:
        exitProgram()

def exitProgram():
    sleep(0.3)
    config.logging.info('Exiting...')
    sleep(0.3)
    sys.exit()

def startupQuestion():
    try:
        action = [
            inquirer.List('action',
                          message="{}Choose Action{}".format(config.BOLD, config.END),
                          choices=['Export Entries to CSV', 'Export Assets to CSV', 'Export Organization Users to CSV', 'Export Organization Users with Stack Roles to CSV', 'Exit'],
                          ),
        ]
        answer = inquirer.prompt(action)['action']
        if answer == 'Exit':
            exitProgram()
        return answer
    except TypeError:
        exitProgram()

def findItemInArr(arr, question):
    '''
    Chosen content type and language
    '''
    try:
        action = [
            inquirer.List('action',
                          message="{}{}{}".format(config.BOLD, question, config.END),
                          choices=arr,
                          ),
        ]
        answer = inquirer.prompt(action)['action']
        return answer
    except TypeError:
        exitProgram()

def sortLanguages(langArr, masterLocale):
    '''
    Sorts list of languages alphabetically - except it puts the masterLocale in front
    '''
    langArr.remove(masterLocale)
    langArr = sorted(langArr)
    langArr.insert(0, masterLocale)
    return langArr

if __name__ == '__main__':
    '''
    Everything starts here
    '''
    try:
        print('''
        {yellow}Export Entries to CSV{end}
        {cyan}- Single content type and language{end}
        {yellow}Export Organization Users to CSV{end}
        {cyan}- Email addresses, UIDs, User Roles, etc{end}

        {bold}First! Answer a few questions.{end}
        '''.format(yellow=config.YELLOW, cyan=config.CYAN, blue=config.BLUE, bold=config.BOLD, end=config.END))

        '''
        Login starts
        '''
        try:
            region, userInfo, liveUserInfo, token = login.startup()
        except (TypeError, KeyError):
            exitProgram()
        config.logging.info('Logged in as: {}'.format(userInfo['username']))
        orgs = restructureOrgs(liveUserInfo) # Making the org output simpler
        '''
        Login finished
        '''
        config.checkDir(config.dataRootFolder)
        startupAction = ''
        while 'Exit' not in startupAction or startupAction is not None:
            startupAction = startupQuestion()
            orgUid, orgName = findOrg(orgs)
            if any(s in startupAction for s in ('Entries', 'Assets')):
                stackName, stack = findStack(orgUid, token, region) # Choose Org and Stack
                try:
                    apiKey = stack['uid']
                except (AttributeError, KeyError, TypeError):
                    apiKey = None
                stackInfo = {
                        'apiKey': apiKey,
                        'region': region
                    }
                if startupAction == 'Export Entries to CSV':
                    ctArr = []
                    contentTypes = cma.getAllContentTypes(apiKey, token, region)
                    for contentType in contentTypes['content_types']:
                        ctArr.append(contentType['uid'])
                    ctArr = sorted(ctArr)
                    ctArr.append(config.cancelString)
                    contentType = findItemInArr(ctArr, 'Choose Content Type')
                    if contentType == config.cancelString:
                        exitProgram()
                    languages = cma.getAllLanguages(apiKey, token, region)
                    langArr = []
                    for language in languages['locales']:
                        langArr.append(language['code'])
                    langArr = sortLanguages(langArr, stack['masterLocale'])
                    langArr.append(config.cancelString)
                    language = findItemInArr(langArr, 'Choose Language')
                    if language == config.cancelString:
                        exitProgram()
                    config.logging.info('Exporting entries of content type {bold}{ct}{end} and language {bold}{lang}{end}.'.format(bold=config.BOLD, ct=contentType, lang=language, end=config.END))
                    entries = cma.getAllEntries(stackInfo, contentType, language, token)
                    csvExport.exportEntries(entries, contentType, language, apiKey, token, region, orgName, stackName)
                if startupAction == 'Export Assets to CSV':
                    assets = cma.getAllAssets(stackInfo, token, None)
                    csvExport.exportAssets(assets, apiKey, token, region, orgName, stackName)
            else:
                if startupAction == 'Export Organization Users to CSV':
                    config.logging.info('{}NOTE: You will need to have an ADMIN role within the organization to execute this export successfully.{}'.format(config.PURPLE, config.END))
                    config.logging.info('Exporting Org Users')
                    orgUsers = cma.getAllOrgUsers(token, orgUid, region)
                    orgRoles = cma.getAllOrgRoles(token, orgUid, region)
                    csvExport.exportOrgUsers(orgName, orgUsers, orgRoles)
                elif startupAction == 'Export Organization Users with Stack Roles to CSV':
                    config.logging.info('{}NOTE: You will need to have an ADMIN role within the organization and access to all the stacks (With Admin or Developer Role) to execute this export successfully.{}'.format(config.PURPLE, config.END))
                    config.logging.info('Exporting Org Users and Stacks')
                    stacks = cma.getAllStacks(cma.constructAuthTokenHeader(token), orgUid, region) # All stacks that the user has access
                    allStacks = cma.getAllStacksFromOrg(cma.constructAuthTokenHeader(token), orgUid, region) # Fetching all stacks, to log out if the user does not have access to them all
                    csvExport.exportStacksAndRoles(orgName, stacks, allStacks, token, region)


        exitProgram()
    except KeyboardInterrupt:
        exitProgram()
