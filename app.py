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

def findStack(orgs, authToken, region, action='EXPORT'):
    '''
    Choosing the org and finding the stack to either export from or import to
    '''
    try:
        orgList = []
        for name, value in orgs.items():
            if value['isOwner']:
                name = name + ' (You are the owner)'
            orgList.append(name)
        orgList = sorted(orgList)
        orgList.append('Cancel and Exit')

        chooseOrg = [
            inquirer.List('chosenOrg',
                          message="{}Choose Organization to work on ({}){}".format(config.BOLD, action, config.END),
                          choices=orgList,
                          ),
        ]
        orgName = inquirer.prompt(chooseOrg)['chosenOrg'].replace(' (You are the owner)', '')
        if orgName == 'Cancel and Exit':
            return None, None
        orgUid = orgs[orgName]['uid']
        stacks = cma.getAllStacks(cma.constructAuthTokenHeader(authToken), orgUid, region)
        stacks = restructureExportStacks(stacks)
        if action == 'EXPORT' or action == 'IMPORT CONTENT':
            stackList = []
        elif action == 'IMPORT':
            stackList = ['Create a new stack']
        unsortedList = []
        for name, _ in stacks.items():
            unsortedList.append(name)
        stackList = stackList + sorted(unsortedList) + ['Cancel and Exit']
        chooseStack = [
            inquirer.List('chosenStack',
                          message="{}Choose Stack to work on ({}){}".format(config.BOLD, action, config.END),
                          choices=stackList,
                          ),
        ]
        stackName = inquirer.prompt(chooseStack)['chosenStack']
        if stackName == 'Cancel and Exit':
            return None, None
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
                          message="{}Choose Action:{}".format(config.BOLD, config.END),
                          choices=['Export Content to CSV', 'Exit'],
                          ),
        ]
        answer = inquirer.prompt(action)['action']
        return answer
    except TypeError:
        exitProgram()

def findItemInArr(arr, question):
    '''
    Chosen content type and language
    '''
    action = [
        inquirer.List('action',
                      message="{}{}{}".format(config.BOLD, question, config.END),
                      choices=arr,
                      ),
    ]
    answer = inquirer.prompt(action)['action']
    return answer


if __name__ == '__main__':
    '''
    Everything starts here
    '''
    try:
        print('''
        {yellow}Export Entries to CSV{end}
        {cyan}- Single content type and language{end}

        {bold}First! Answer a few questions.{end}
        '''.format(yellow=config.YELLOW, cyan=config.CYAN, blue=config.BLUE, bold=config.BOLD, end=config.END))

        '''
        Login starts
        '''
        region, userInfo, liveUserInfo, token = login.startup()
        config.logging.info('Logged in as: {}'.format(userInfo['username']))
        orgs = restructureOrgs(liveUserInfo) # Making the org output simpler
        '''
        Login finished - Lets ask the user what he/she wants to do
        '''
        config.checkDir(config.dataRootFolder)
        startupAction = ''
        while 'Exit' not in startupAction and startupAction is not None:
            startupAction = startupQuestion()
            stackName, stack = findStack(orgs, token, region)
            try:
                apiKey = stack['uid']
            except (AttributeError, KeyError):
                apiKey = None
            ctArr = []
            contentTypes = cma.getAllContentTypes(apiKey, token, region)
            for contentType in contentTypes['content_types']:
                ctArr.append(contentType['uid'])
            contentType = findItemInArr(ctArr, 'Choose Content Type')
            languages = cma.getAllLanguages(apiKey, token, region)
            langArr = []
            for language in languages['locales']:
                langArr.append(language['code'])
            language = findItemInArr(langArr, 'Choose Language')
            config.logging.info('Exporting entries of content type {bold}{ct}{end} and language {bold}{lang}{end}.'.format(bold=config.BOLD, ct=contentType, lang=language, end=config.END))
            stackInfo = {
                'apiKey': apiKey,
                'region': region
            }
            entries = cma.getAllEntries(stackInfo, contentType, language, token)
            csvExport.export(entries, contentType, language, apiKey, token, region)
        exitProgram()
    except KeyboardInterrupt:
        exitProgram()
