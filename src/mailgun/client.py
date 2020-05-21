import os
import logging
import sys
from kbc.client_base import HttpClientBase


SUPPORTED_REGIONS = ['US', 'EU']


class MailgunClient(HttpClientBase):

    def __init__(self, paramToken, paramDomain, paramFromName, paramRegion, paramFromEmail='postmaster'):

        if paramRegion not in SUPPORTED_REGIONS:

            logging.error(f"Unknown region {paramRegion}. Allowed values are: {SUPPORTED_REGIONS}.")
            sys.exit(1)

        else:

            if paramRegion == 'US':
                BASE_URL = os.path.join('https://api.mailgun.net/v3', paramDomain)

            elif paramRegion == 'EU':
                BASE_URL = os.path.join('https://api.eu.mailgun.net/v3', paramDomain)

            else:
                pass

        super().__init__(BASE_URL, auth=('api', paramToken))
        self._validateAuthentication()

        if paramFromName is None:
            self.paramFromId = f'{paramFromEmail}@{paramDomain}'

        else:
            self.paramFromId = ' '.join([paramFromName, f'<{paramFromEmail}@{paramDomain}>'])

    def _validateAuthentication(self):

        reqUrl = os.path.join(self.base_url, 'events')
        reqHeaders = {'accept': 'application/json'}
        reqParams = {'limit': 1}

        validationRequest = self.get_raw(reqUrl, headers=reqHeaders, params=reqParams)
        _valSc, _valJs = validationRequest.status_code, validationRequest.json()

        if _valSc == 200:

            logging.info("Authentication successful.")

        else:

            logging.error("Authentication was not successful. Please check the credentials.")
            logging.error("Response received: %s - %s." % (_valSc, _valJs['message']))
            sys.exit(1)

    def sendMessage(self, msgObject):

        reqBody = {
            'from': self.paramFromId,
            'to': msgObject.email,
            'subject': msgObject.subject,
            'html': msgObject.html,
            'text': msgObject.text
        }

        if msgObject.delivery_time is not None:
            reqBody['o:deliverytime'] = msgObject.delivery_time

        if msgObject.cc is not None:
            reqBody['cc'] = msgObject.cc

        if msgObject.bcc is not None:
            reqBody['bcc'] = msgObject.bcc

        if msgObject.tags != []:
            reqBody['o:tag'] = msgObject.tags

        if msgObject.custom_fields is not None:
            reqBody = {**msgObject.custom_fields, **reqBody}

        logging.debug("Body:")
        logging.debug(reqBody)

        reqFiles = []
        for path in msgObject.attachments:

            reqFiles += [('attachment', (os.path.basename(path).replace('_tableattachment_', ''),
                                         open(path, 'rb').read()))]

        # logging.debug("Attachments:")
        # logging.debug(reqFiles)

        reqUrl = os.path.join(self.base_url, 'messages')
        reqSendMessage = self.post_raw(url=reqUrl, files=reqFiles, data=reqBody)
        messageSc, messageJs = reqSendMessage.status_code, reqSendMessage.json()

        logging.debug("Message response:")
        logging.debug(messageJs)

        return messageSc, messageJs
