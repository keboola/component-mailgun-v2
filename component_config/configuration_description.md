* **Token** - Password or API key for Mailgun.
* **Domain** - Domain, from which the mail should be sent. See [How to send mail](https://documentation.mailgun.com/en/latest/quickstart-sending.html#how-to-start-sending-email).
* **Region** - one of US/EU.
* **From** - Specifiec in whose name should the mail be sent.
* **Input Table** with records of emails. Each row will be sent as separate email, to separate address, name, body, etc. specified in the input table. Table **must include** following columns:
    * `email` - Email address to which an email will be sent.
    * `name` - Name of the person. Will be used in creating an email handle. Can be left blank.
    * `html_file` - Name of the file in KBC storage to be used as html body, in format `KBCID_filename.ext`, where `KBCID` is ID of the file in KBC storage, `filename.ext` is the name and extension of given file. If no file matches the specification,
    * `subject` - Subject of an email.
    * `attachments` - String separated names of files in KBC storage to be attached to the email. Error is raised, if files are not inputted correctly or are not in the folder. Attachments must be in format `KBCID_filename.ext`, where `KBCID` is ID of the file in KBC storage, `filename.ext` is the name and extension of given file.
    * `delivery` - Scheduled delivery time in format `YYYY-MM-DD HH:MM:SS ±ZZZZ` (e.g. `2019-02-28 16:00:00 +0000` or `2018-03-17 09:00:00 -0900`). If inputted correctly, an email will be delivered at this time. Otherwise, an email will be delivered straightaway.
    * `**kwargs` - Other columns. Each of these columns can be used to fill in the html body using standard Python string handlers. For example, if the html body has `Weather is %(weather)s, %(name)s.` in it, the handles `%(weather)s` and `%(name)s` will be replaced by their respective values in column `weather` and `name` from the input table, thus producing (e.g.) `Weather is nice, John. See more information in example below.`