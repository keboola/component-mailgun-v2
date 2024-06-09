import csv
import json
import os


class MailgunWriter:

    def __init__(self, data_path, table_name, table_fields, primary_keys, incremental=True):

        self.writer = None
        self.var_table_path = None
        self.param_data_path = data_path
        self.param_table_name = table_name
        self.param_table_fields = table_fields
        self.param_pk = primary_keys
        self.param_incremental = incremental

        self.run()

    def run(self):
        self.create_writer()
        self.create_manifest()

    def create_manifest(self):

        _template = {'incremental': self.param_incremental,
                     'primary_key': self.param_pk}

        _man_path = self.var_table_path + '.manifest'

        with open(_man_path, 'w') as man_file:
            json.dump(_template, man_file)

    def create_writer(self):

        self.var_table_path = os.path.join(
            self.param_data_path, self.param_table_name) + '.csv'

        self.writer = csv.DictWriter(open(self.var_table_path, 'w'), fieldnames=self.param_table_fields,
                                     restval='', extrasaction='ignore', quotechar='\"',
                                     quoting=csv.QUOTE_ALL)

        self.writer.writeheader()

    def writerow(self, write_dict):
        self.writer.writerow(write_dict)
