import csv
import json
import os


class MailgunWriter:

    def __init__(self, dataPath, tableName, tableFields, primaryKeys, incremental=True):

        self.paramDataPath = dataPath
        self.paramTableName = tableName
        self.paramTableFields = tableFields
        self.paramPK = primaryKeys
        self.paramIncremental = incremental

        self.run()

    def createManifest(self):

        _template = {'incremental': self.paramIncremental,
                     'primary_key': self.paramPK}

        _manPath = self.varTablePath + '.manifest'
        with open(_manPath, 'w') as manFile:

            json.dump(_template, manFile)

    def createWriter(self):

        self.varTablePath = os.path.join(
            self.paramDataPath, 'out', 'tables', self.paramTableName) + '.csv'

        self.writer = csv.DictWriter(open(self.varTablePath, 'w'), fieldnames=self.paramTableFields,
                                     restval='', extrasaction='ignore', quotechar='\"',
                                     quoting=csv.QUOTE_ALL)

        self.writer.writeheader()

    def run(self):

        self.createWriter()
        self.createManifest()

    def writerow(self, writeDict):

        self.writer.writerow(writeDict)
