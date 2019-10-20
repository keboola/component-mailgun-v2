import csv
import datetime
import glob
import json
import logging
import os
import re
import sys
from kbc.env_handler import KBCEnvHandler
from mailgun.client import MailgunClient
from mailgun.result import MailgunWriter


KEY_API_TOKEN = '#apiToken'
KEY_DOMAIN_NAME = 'domainName'
KEY_DOMAIN_REGION = 'domainRegion'
KEY_FROM_NAME = 'fromName'
KEY_FROM_EMAIL = 'fromEmail'

MANDATORY_PARAMETERS = [KEY_API_TOKEN,
                        KEY_DOMAIN_NAME, KEY_DOMAIN_REGION, KEY_FROM_NAME]

MESSAGES_FIELDS = ['message_id', 'date', 'specification',
                   'html_file_used', 'attachments_sent']
MESSAGES_PK = ['message_id']
ERRORS_FIELDS = ['date', 'specification', 'error', 'error_message']
ERRORS_PK = []

REQUIRED_COLUMNS_HTML = ['email', 'subject', 'html_file']
REQUIRED_COLUMNS_TEXT = ['email', 'subject', 'text']


class MailgunMessage:

    def __init__(self):

        pass


class MailgunApp(KBCEnvHandler):

    def __init__(self):

        super().__init__(MANDATORY_PARAMETERS)
        self.validate_config(MANDATORY_PARAMETERS)

        self.paramToken = self.cfg_params[KEY_API_TOKEN]
        self.paramDomain = self.cfg_params[KEY_DOMAIN_NAME]
        self.paramRegion = self.cfg_params[KEY_DOMAIN_REGION]
        self.paramFromName = self.cfg_params[KEY_FROM_NAME]
        self.paramFromEmail = self.cfg_params.get(KEY_FROM_EMAIL, 'postmaster')

        self.files_in_path = os.path.join(self.data_path, 'in', 'files')

        self.checkParameters()
        self.checkInputTablesAndFiles()

        self.client = MailgunClient(paramToken=self.paramToken, paramDomain=self.paramDomain,
                                    paramFromName=self.paramFromName, paramRegion=self.paramRegion,
                                    paramFromEmail=self.paramFromEmail)
        self.writerMessages = MailgunWriter(dataPath=self.data_path, tableName='messages', tableFields=MESSAGES_FIELDS,
                                            primaryKeys=MESSAGES_PK, incremental=True)
        self.writerErrors = MailgunWriter(dataPath=self.data_path, tableName='errors', tableFields=ERRORS_FIELDS,
                                          primaryKeys=ERRORS_PK, incremental=False)

    def checkParameters(self):

        if 'sandbox' in self.paramDomain:

            logging.warn(' '.join(["Using sandbox domain. Please, make sure all of the recipients are registered as",
                                   "authorized recipients. For more information, please, refer to",
                                   "https://help.mailgun.com/hc/en-us/articles/217531258-Authorized-Recipients."]))

        LOCAL_PART_REGEX = r"[^\w\.!#$%&'*+-/=?^_`{\|}~]|[.]{2,}"
        localPartRgx = re.findall(LOCAL_PART_REGEX, self.paramFromEmail)

        if len(localPartRgx) != 0:

            logging.error(
                "Unsupported characters in local part of email: %s" % localPartRgx)
            sys.exit(1)

    def checkInputTablesAndFiles(self):

        globTables = os.path.join(self.tables_in_path, '*.csv')
        globFiles = os.path.join(self.files_in_path, '*')
        inputTables = glob.glob(globTables)
        inputFiles = [os.path.basename(pathName)
                      for pathName in glob.glob(globFiles)]

        self.varMailingLists = [pathName for pathName in inputTables
                                if not os.path.basename(pathName).startswith('_tableattachment_')]
        self.varTableAttachments = [os.path.basename(pathName) for pathName in inputTables
                                    if os.path.basename(pathName).startswith('_tableattachment_')]

        self.varFiles = [os.path.basename(pathName) for pathName in inputFiles
                         if not os.path.basename(pathName).endswith('.manifest')]

        for tablePath in self.varMailingLists:

            manifestPath = tablePath + '.manifest'
            with open(manifestPath) as manFile:

                tableColumns = json.load(manFile)['columns']

            setDiffHtml = set(REQUIRED_COLUMNS_HTML) - set(tableColumns)
            setDiffText = set(REQUIRED_COLUMNS_TEXT) - set(tableColumns)

            if setDiffHtml != set() and setDiffText != set():

                logging.error(' '.join(["Missing mandatory columns",
                                        "in the mailing input table \"%s\"." % os.path.basename(
                                            tablePath),
                                        "Required columns are ['email', 'subject'] and at least",
                                        "one of ['html_file', 'text']"]))

                sys.exit(1)

    def getLatestFile(self, files):

        maxFilename = ''
        maxTimestamp = '0'

        for filePath in files:

            manifestPath = filePath + '.manifest'
            with open(manifestPath) as manFile:

                creationDate = json.load(manFile)['created']

                if creationDate > maxTimestamp:

                    maxTimestamp = creationDate
                    maxFilename = filePath

        return maxFilename

    def getHtmlTemplate(self, htmlFileName):

        if htmlFileName in self.varFiles:

            return os.path.join(self.files_in_path, htmlFileName)

        else:

            globHtml = os.path.join(self.files_in_path, '*') + htmlFileName
            matchedHtml = glob.glob(globHtml)

            if len(matchedHtml) == 1:

                return matchedHtml[0]

            elif len(matchedHtml) == 0:

                return ''

            elif len(matchedHtml) > 1:

                return self.getLatestFile(matchedHtml)

    def getAttachment(self, attachmentName):

        if attachmentName in self.varFiles:

            return os.path.join(self.files_in_path, attachmentName)

        else:

            globAttachment = os.path.join(
                self.files_in_path, '*') + attachmentName
            matchedAttachment = glob.glob(globAttachment)

            if len(matchedAttachment) == 1:

                return matchedAttachment[0]

            elif len(matchedAttachment) == 0:

                return ''

            elif len(matchedAttachment) > 1:

                return self.getLatestFile(matchedAttachment)

    def getUtcTime(self):

        return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S +0000')

    def getTableAttachment(self, tableAttachmentName):

        if tableAttachmentName in self.varTableAttachments:

            return os.path.join(self.tables_in_path, tableAttachmentName)

        else:

            return ''

    def composeMessage(self, rowDict):

        msg = MailgunMessage()
        msg.email = rowDict['email']
        msg.subject = rowDict['subject']
        msg.text = rowDict.get('text', '').strip()

        if rowDict.get('delivery_time', '').strip() != '':
            msg.delivery_time = rowDict['delivery_time']
        else:
            msg.delivery_time = None

        if rowDict.get('tags', '').strip() != '':
            msg.tags = [t.strip()
                        for t in rowDict['tags'].split(',') if t.strip() != '']
        else:
            msg.tags = []

        if rowDict.get('bcc', '').strip() != '':
            msg.bcc = rowDict['bcc']
        else:
            msg.bcc = None

        if rowDict.get('cc', '').strip() != '':
            msg.cc = rowDict['cc']
        else:
            msg.cc = None

        if rowDict.get('html_file', '').strip() != '':

            htmlFile = rowDict['html_file']
            pathHtml = self.getHtmlTemplate(htmlFile)

            if pathHtml == '':

                logging.warn("Could not locate html teplate %s." % htmlFile)
                self.writerErrors.writerow({'date': self.getUtcTime(),
                                            'specification': json.dumps(rowDict),
                                            'error': 'TEMPLATE_NOT_FOUND_ERROR',
                                            'error_message': "Could not locate html file %s." % htmlFile})

                return None

            else:

                htmlString = open(pathHtml).read()
                for key in rowDict:
                    htmlString = htmlString.replace(
                        f'{{{{{key}}}}}', rowDict[key])

                msg.html = htmlString
                msg.html_file = pathHtml

        else:

            msg.html_file = ''
            msg.html = ''

        if rowDict.get('attachments', '').strip() != '':

            attachmentsString = rowDict['attachments'].strip()
            attachmentsSplit = [
                att.strip() for att in attachmentsString.split(',') if att.strip() != '']

            attachmentsPaths = []

            for att in attachmentsSplit:

                if '_tableattachment_' in att:

                    attachmentsPaths += [self.getTableAttachment(att)]

                else:

                    attachmentsPaths += [self.getAttachment(att)]

            if '' in attachmentsPaths:

                idx = attachmentsPaths.index('')
                attName = attachmentsSplit[idx]
                logging.warn("Could not locate file %s." % attName)
                self.writerErrors.writerow({'date': self.getUtcTime(),
                                            'specification': json.dumps(rowDict),
                                            'error': 'ATTACHMENT_NOT_FOUND_ERROR',
                                            'error_message': 'Could not locate attachment %s.' % attName})

                return None

            else:

                msg.attachments = attachmentsPaths

        else:

            msg.attachments = []

        return msg

# attachments

    def run(self):

        for table in self.varMailingLists:

            with open(table) as mailingList:

                reader = csv.DictReader(mailingList)
                for row in reader:

                    msg = self.composeMessage(row)

                    if msg is None:
                        continue

                    sc, js = self.client.sendMessage(msg)

                    if sc == 200:

                        toWrite = {}

                        toWrite['message_id'] = js['id'].replace('<', '').replace('>', '')
                        toWrite['date'] = datetime.datetime.strptime(toWrite['message_id'].split('.')[0],
                                                                     '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S') \
                            + ' +0000'
                        toWrite['specification'] = json.dumps(row)
                        toWrite['html_file_used'] = msg.html_file
                        toWrite['attachments_sent'] = msg.attachments

                        self.writerMessages.writerow(toWrite)

                    else:

                        self.writerErrors.writerow({'date': self.getUtcTime(),
                                                    'specification': json.dumps(row),
                                                    'error': 'SEND_ERROR',
                                                    'error_message': js['message']})
