import csv
import datetime
import glob
import json
import logging
import os
import re
import sys
import time
from hashlib import md5

from mailgun.client import MailgunClient
from mailgun.result import MailgunWriter

from keboola.component.base import ComponentBase, sync_action
import requests
from keboola.component.exceptions import UserException

APP_VERSION = '0.1.5'
LOG_LEVEL = 'INFO'
MAX_MESSAGE_SIZE = 24.9 * 1024 ** 2

KEY_API_TOKEN = '#apiToken'
KEY_DOMAIN_NAME = 'domainName'
KEY_DOMAIN_REGION = 'domainRegion'
KEY_FROM_NAME = 'fromName'
KEY_FROM_EMAIL = 'fromEmail'

MANDATORY_PARAMETERS = [KEY_API_TOKEN, KEY_DOMAIN_NAME, KEY_DOMAIN_REGION]

MESSAGES_FIELDS = ['message_id', 'timestamp', 'specification',
                   'html_file_used', 'attachments_sent']
MESSAGES_PK = ['message_id']
ERRORS_FIELDS = ['request_id', 'timestamp', 'specification',
                 'error', 'error_message']
ERRORS_PK = ['request_id']

REQUIRED_COLUMNS_HTML = ['email', 'subject', 'html_file']
REQUIRED_COLUMNS_TEXT = ['email', 'subject', 'text']


class MailgunMessage:
    def __init__(self):
        pass


class Component(ComponentBase):

    def __init__(self):

        super().__init__()

        logging.info(f"Running component version {APP_VERSION}.")
        self.validate_configuration_parameters(MANDATORY_PARAMETERS)

        self.param_token = self.configuration.parameters[KEY_API_TOKEN]
        self.param_domain = self.configuration.parameters[KEY_DOMAIN_NAME]
        self.param_region = self.configuration.parameters[KEY_DOMAIN_REGION]
        self.param_from_name = self.configuration.parameters.get(KEY_FROM_NAME)
        self.param_from_email = self.configuration.parameters.get(KEY_FROM_EMAIL, 'postmaster') \
            if self.configuration.parameters.get(KEY_FROM_EMAIL, 'postmaster') != '' else 'postmaster'

        self.check_parameters()
        self.check_input_tables_and_files()

        self.client = MailgunClient(param_token=self.param_token, param_domain=self.param_domain,
                                    param_from_name=self.param_from_name, param_region=self.param_region,
                                    param_from_email=self.param_from_email)
        self.writer_messages = MailgunWriter(data_path=self.tables_out_path, table_name='messages',
                                             table_fields=MESSAGES_FIELDS, primary_keys=MESSAGES_PK, incremental=True)
        self.writer_errors = MailgunWriter(data_path=self.tables_out_path, table_name='errors',
                                           table_fields=ERRORS_FIELDS, primary_keys=ERRORS_PK, incremental=True)

    def run(self):

        for table in self.var_mailing_lists:

            with open(table) as mailing_list:

                reader = csv.DictReader(mailing_list)
                for row in reader:

                    logging.info("Starting sending process for %s." % row['email'])
                    msg = self.compose_message(row)
                    msg_size = self.get_message_size(msg)

                    if msg is None:

                        logging.warning("Process for %s exited with errors." % row['email'])
                        continue

                    elif msg_size > MAX_MESSAGE_SIZE:

                        msg_size_mb = msg_size / 1024 ** 2
                        logging.warning("Process for %s exited with errors." % row['email'])
                        _utc = self.get_utc_time()
                        _specification = json.dumps(row)
                        self.writer_errors.writerow({'timestamp': _utc,
                                                     'specification': _specification,
                                                     'error': 'EMAIL_TOO_LARGE_ERROR',
                                                     'error_message': "Email exceeded max. size of 25MB. " +
                                                                      f"Total email size: {msg_size_mb}MB.",
                                                     'request_id': md5('|'.join([_utc, _specification]).encode())
                                                    .hexdigest()})
                        continue

                    sc, js = self.client.send_message(msg)

                    if sc == 200:

                        to_write = {}

                        to_write['message_id'] = js['id'].replace('<', '').replace('>', '')
                        to_write['timestamp'] = int(datetime.datetime.strptime(to_write['message_id'].split('.')[0],
                                                                               '%Y%m%d%H%M%S').timestamp() * 1000)
                        to_write['specification'] = json.dumps(row)
                        to_write['html_file_used'] = msg.html_file
                        to_write['attachments_sent'] = json.dumps(msg.attachments)

                        self.writer_messages.writerow(to_write)

                    else:

                        logging.warning(f"There were some errors sending email to {row['email']}.")

                        _utc = self.get_utc_time()
                        _specification = json.dumps(row)
                        self.writer_errors.writerow({'timestamp': _utc,
                                                     'specification': _specification,
                                                     'error': 'SEND_ERROR',
                                                     'error_message': js['message'],
                                                     'request_id': md5('|'.join([_utc, _specification]).encode())
                                                    .hexdigest()})

    def check_parameters(self):

        if 'sandbox' in self.param_domain:

            logging.warn(' '.join(["Using sandbox domain. Please, make sure all of the recipients are registered as",
                                   "authorized recipients. For more information, please refer to",
                                   "https://help.mailgun.com/hc/en-us/articles/217531258-Authorized-Recipients."]))

        LOCAL_PART_REGEX = r"[^\w\.!#$%&'*+-/=?^_`{\|}~]|[.]{2,}"
        local_part_rgx = re.findall(LOCAL_PART_REGEX, self.param_from_email)

        if len(local_part_rgx) != 0:
            raise UserException(f"Unsupported characters in local part of email: %s" % local_part_rgx)

    def check_input_tables_and_files(self):

        glob_tables = os.path.join(self.tables_in_path, '*.csv')
        glob_files = os.path.join(self.files_in_path, '*')
        input_tables = glob.glob(glob_tables)
        input_files = [os.path.basename(path_name).strip() for path_name in glob.glob(glob_files)]

        if len(input_tables) == 0:
            raise UserException(f"No input tables specified.")

        self.var_mailing_lists = [path_name for path_name in input_tables
                                  if not os.path.basename(path_name).startswith('_tableattachment_')]
        self.var_table_attachments = [os.path.basename(path_name) for path_name in input_tables
                                      if os.path.basename(path_name).startswith('_tableattachment_')]
        self.var_files = [os.path.basename(path_name).strip() for path_name in input_files
                          if not os.path.basename(path_name).endswith('.manifest')]

        for table_path in self.var_mailing_lists:

            manifest_path = table_path + '.manifest'
            with open(manifest_path) as man_file:

                table_columns = json.load(man_file)['columns']

            set_diff_html = set(REQUIRED_COLUMNS_HTML) - set(table_columns)
            set_diff_text = set(REQUIRED_COLUMNS_TEXT) - set(table_columns)

            if set_diff_html != set() and set_diff_text != set():
                raise UserException(' '.join(["Missing mandatory columns",
                                              "in the mailing input table \"%s\"." % os.path.basename(table_path),
                                              "Required columns are ['email', 'subject'] and at least",
                                              "one of ['html_file', 'text']"]))

    def get_latest_file(self, list_of_file_paths):

        max_filename = ''
        max_timestamp = '0'

        for file_path in list_of_file_paths:

            manifest_path = file_path + '.manifest'
            with open(manifest_path) as man_file:

                creation_date = json.load(man_file)['created']

                if creation_date > max_timestamp:

                    max_timestamp = creation_date
                    max_filename = file_path

        return max_filename

    def get_html_template(self, html_file_name):

        if html_file_name.strip() in self.var_files:

            return os.path.join(self.files_in_path, html_file_name.strip())

        else:

            glob_html = os.path.join(self.files_in_path, '*') + html_file_name.strip()
            matched_html = glob.glob(glob_html)

            if len(matched_html) == 1:

                return matched_html[0]

            elif len(matched_html) == 0:

                return ''

            elif len(matched_html) > 1:

                return self.get_latest_file(matched_html)

    def get_attachment(self, attachment_name):

        if attachment_name in self.var_files:

            return os.path.join(self.files_in_path, attachment_name)

        else:

            glob_attachment = os.path.join(self.files_in_path, '*') + attachment_name
            matched_attachment = glob.glob(glob_attachment)

            if len(matched_attachment) == 1:
                return matched_attachment[0]

            elif len(matched_attachment) == 0:
                return ''

            elif len(matched_attachment) > 1:
                return self.get_latest_file(matched_attachment)

    def get_utc_time(self):

        return str(int(time.time() * 1000))

    def get_table_attachment(self, table_attachment_name):

        if table_attachment_name in self.var_table_attachments:
            return os.path.join(self.tables_in_path, table_attachment_name)

        else:
            return ''

    def compose_message(self, row_dict):

        msg = MailgunMessage()
        msg.email = row_dict['email'].strip()
        subject_string = row_dict['subject'].strip()
        text_string = row_dict.get('text', '').strip()

        for key in row_dict:

            text_string = text_string.replace(f'{{{{{key}}}}}', row_dict[key])
            subject_string = subject_string.replace(f'{{{{{key}}}}}', row_dict[key])

        msg.text = text_string
        msg.subject = subject_string

        if row_dict.get('delivery_time', '').strip() != '':
            msg.delivery_time = row_dict['delivery_time']
        else:
            msg.delivery_time = None

        if row_dict.get('tags', '').strip() != '':
            msg.tags = [t.strip()
                        for t in row_dict['tags'].split(',') if t.strip() != '']
        else:
            msg.tags = []

        if row_dict.get('bcc', '').strip() != '':
            msg.bcc = row_dict['bcc']
        else:
            msg.bcc = None

        if row_dict.get('cc', '').strip() != '':
            msg.cc = row_dict['cc']
        else:
            msg.cc = None

        if row_dict.get('html_file', '').strip() != '':

            html_file = row_dict['html_file']
            path_html = self.get_html_template(html_file)

            if path_html == '':

                _utc = self.get_utc_time()
                _specification = json.dumps(row_dict)

                logging.warning(f"Could not locate html template {html_file}.")
                self.writer_errors.writerow({'timestamp': _utc,
                                             'specification': _specification,
                                             'error': 'TEMPLATE_NOT_FOUND_ERROR',
                                             'error_message': f"Could not locate html file {html_file}.",
                                             'request_id': md5('|'.join([_utc, _specification]).encode())
                                            .hexdigest()})

                return None

            elif os.path.splitext(path_html)[1] != '.html':

                _utc = self.get_utc_time()
                _specification = json.dumps(row_dict)

                logging.warning(f"Invalid html template {html_file}.")
                self.writer_errors.writerow({'timestamp': _utc,
                                             'specification': _specification,
                                             'error': 'INVALID_TEMPLATE_ERROR',
                                             'error_message': f"Template {path_html}"
                                                              f" for {html_file} is not an html file.",
                                             'request_id': md5('|'.join([_utc, _specification]).encode())
                                            .hexdigest()})

                return None

            else:

                html_string = open(path_html).read()
                for key in row_dict:
                    html_string = html_string.replace(f'{{{{{key}}}}}', row_dict[key])

                msg.html = html_string
                msg.html_file = path_html

        else:

            msg.html_file = ''
            msg.html = ''

        if row_dict.get('attachments', '').strip() != '':

            attachments_string = row_dict['attachments'].strip()
            attachments_split = [
                att.strip() for att in attachments_string.split(',') if att.strip() != '']

            attachments_paths = []

            for att in attachments_split:

                if '_tableattachment_' in att:

                    attachments_paths += [self.get_table_attachment(att)]

                else:

                    attachments_paths += [self.get_attachment(att)]

            if '' in attachments_paths:

                idx = attachments_paths.index('')
                att_name = attachments_split[idx]
                logging.warn("Could not locate file %s." % att_name)

                _utc = self.get_utc_time()
                _specification = json.dumps(row_dict)
                self.writer_errors.writerow({'timestamp': _utc,
                                             'specification': _specification,
                                             'error': 'ATTACHMENT_NOT_FOUND_ERROR',
                                             'error_message': f'Could not locate attachment {att_name}.',
                                             'request_id': md5('|'.join([_utc, _specification]).encode())
                                            .hexdigest()})

                return None

            else:

                msg.attachments = attachments_paths

        else:

            msg.attachments = []

        if row_dict.get('custom_fields', '').strip() != '':
            try:
                _custom_fields = json.loads(row_dict.get('custom_fields', ''))

                if isinstance(_custom_fields, dict) is False:
                    _custom_fields = {}

            except ValueError:
                _custom_fields = None

            finally:
                msg.custom_fields = _custom_fields

        else:
            msg.custom_fields = None

        return msg

    def get_message_size(self, msg_object):

        total_msg_size = 0

        if msg_object is None:
            return None

        for key, value in vars(msg_object).items():

            if key == 'attachments':
                for path in value:
                    total_msg_size += os.path.getsize(path)

            else:
                total_msg_size += sys.getsizeof(value)

            return total_msg_size

    @sync_action('test_api_key')
    def test_api_key(self):
        region_urls = {
            'US': f'https://api.mailgun.net/v3/{self.param_domain}/events',
            'EU': f'https://api.eu.mailgun.net/v3/{self.param_domain}/events'
        }
        auth = requests.auth.HTTPBasicAuth('api', self.param_token)
        response = requests.get(region_urls[self.param_region], auth=auth)
        if response.ok:
            logging.info("Validation successful")
        else:
            raise UserException("Validation failed")


if __name__ == "__main__":
    try:
        comp = Component()
        comp.execute_action()
    except UserException as exc:
        logging.exception(exc)
        exit(1)
    except Exception as exc:
        logging.exception(exc)
        exit(2)
