import os
import logging
from keboola.http_client import HttpClient
from keboola.component.exceptions import UserException
from requests.exceptions import JSONDecodeError


REGION_URLS = {
    'US': 'https://api.mailgun.net/v3',
    'EU': 'https://api.eu.mailgun.net/v3'
}


class AuthenticationError(Exception):
    pass


class MailgunClientException(Exception):
    pass


class MailgunClient(HttpClient):

    def __init__(self, param_token, param_domain, param_from_name, param_region, param_from_email='postmaster'):
        if param_region not in REGION_URLS:
            raise MailgunClientException(f"Unknown region {param_region}. "
                                         f"Allowed values are: {list(REGION_URLS.keys())}.")

        base_url = os.path.join(REGION_URLS[param_region], param_domain)

        super().__init__(base_url, auth=('api', param_token))
        self._validate_authentication()

        if param_from_name is None:
            self.param_from_id = f'{param_from_email}@{param_domain}'
        else:
            self.param_from_id = ' '.join([param_from_name, f'<{param_from_email}@{param_domain}>'])

    def _validate_authentication(self):

        req_url = os.path.join(self.base_url, 'events')
        req_headers = {'accept': 'application/json'}
        req_params = {'limit': 1}

        validation_request = self.get_raw(req_url, headers=req_headers, params=req_params)
        _val_sc = validation_request.status_code

        try:
            _val_js = validation_request.json()
        except JSONDecodeError as e:
            raise AuthenticationError(f"Cannot authenticate. Details: "
                                      f"{validation_request.text} \n"
                                      f"{e}") from e

        if _val_sc == 200:
            logging.info("Authentication successful.")
        else:
            raise UserException("Authentication was not successful. Please check the credentials.\n"
                                "Response received: %s - %s." % (_val_sc, _val_js))

    def send_message(self, msg_object):

        req_body = {
            'from': self.param_from_id,
            'to': msg_object.email,
            'subject': msg_object.subject,
            'html': msg_object.html,
            'text': msg_object.text
        }

        if msg_object.delivery_time is not None:
            req_body['o:deliverytime'] = msg_object.delivery_time

        if msg_object.cc is not None:
            req_body['cc'] = msg_object.cc

        if msg_object.bcc is not None:
            req_body['bcc'] = msg_object.bcc

        if msg_object.tags:
            req_body['o:tag'] = msg_object.tags

        if msg_object.custom_fields is not None:
            req_body = {**msg_object.custom_fields, **req_body}

        logging.debug(f"Body: {req_body}")

        req_files = []
        for path in msg_object.attachments:
            req_files += [('attachment', (os.path.basename(path).replace('_tableattachment_', ''),
                                          open(path, 'rb').read()))]

        logging.debug(f"Attachments: {req_files}")

        req_url = os.path.join(self.base_url, 'messages')
        req_send_message = self.post_raw(req_url, files=req_files, data=req_body, is_absolute_path=True)
        message_sc, message_js = req_send_message.status_code, req_send_message.json()

        logging.debug("Message response:")
        logging.debug(message_js)

        return message_sc, message_js
