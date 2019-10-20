# Mailgun application for Keboola Connection

## Overview

Mailgun is a leading platform for sending transactional emails. This component builds on Mailgun's powerful API and allows anybody to send transactional emails with attachments from sandbox/production domains.

Basic requirements are:

  * Mailgun account;
  * a domain.

This component takes as input a table of email addresses and names, to which an email is sent. In the table, other attributes can be added, which will then be used to fill in the html body (e.g. date of birth, etc.).
**The input table needs to contain following columns: `email`, `subject` and one of `html_file` or `text`. All other columns are optional.**

### Inputs
Mailgun component takes the following parameters and table as inputs.

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

### Example

As an example, the following input table is created, serving as a mailing list.

|email|name|html_file|subject|attachments|delivery|weather|degrees_celsius|amount_spent|prize|percentage_votes|
|---|---|---|---|---|---|---|---|---|---|---|---|
|john@doe.com|John Doe|example_1.html|Weather for London||2019-01-04 09:00:00 +0000|sunny|24||||
|johnny.bravo@besthair.com|Johnny Bravo|example_1.html|Weather for Seattle||2019-02-28 10:00:00 +0900|rainy|9||||
|testy@mctestface.com|Testy McTestface|example_2.html|Today's spending|12345678_attachment.pdf||||$2500|||
|albert.einstein@emc2.edu|Albert Einstein|example_3.html|You won it!||||||Scientist of the Century|94.2|

In the table, there are 4 unique recipients. To 2 of them, the same email is sent with weather information, to another one a spending report is sent along
and to the last one a letter of congratulations is sent. Three different email bodies are sent, their specification and outcome is below.

#### Recipients 1 & 2 - scheduled delivery of an email

Both emails are scheduled for delivery in two different time-zones.

##### example_1.html

```
<!DOCTYPE html>
<html>
<body>
<p>Hello %(name)s,</p>
<p>The weather will be %(weather)s, the temperature will reach %(degrees_celsius)s&#8451.</p>

</body>
</html>
```

This specification will result in two emails being sent:

##### Email 1
```
  From: From Name <postmaster@domain.com>
  To: John Doe <john@doe.com>
  Subject: Weather for London
  Delivered: 2019-01-04 09:00:02 +0000
  
  Body:
  
  Hello John Doe,
  The weather will be sunny, the temperature will reach 24°C.
```

##### Email 2
```
  From: From Name <postmaster@domain.com>
  To: Johnny Bravo <johnny.bravo@besthair.com>
  Subject: Weather for Seattle
  Delivered: 2019-02-28 10:00:03 +0900
  
  Body:
  
  Hello Johnny Bravo,
  The weather will be rainy, the temperature will reach 9°C.
```

#### Recipient 3 - sending an attachment

The email to the recipient will include attachment, with a bank statement from his account. Since no delivery time is specified, the email
will be sent straight-away.

##### example_2.html

```
<!DOCTYPE html>
<html>
<body>
<p>Hello %(name)s,</p>
<p>You've spent $%(amount_spent)s today, so far. Attached is a bank statement.</p>

</body>
</html>
```

##### Email 3

```
  From: From Name <postmaster@domain.com>
  To: Testy McTestface <testy@mctestface.com>
  Subject: Today's spending
  
  Body:
  Hello Testy McTestface,
  You've spend $2500 today, so far. Attached is a bank statement.
  
  Attachments:
  12345678_attachment.pdf
```

Note that the number before the attachment is a KBC storage ID, which can be found in files section in storage area.


#### Recipient 4 - usage of percentage in an email

If, in any case, a percentage sign is needed in the body of an email, in raw .html file, it needs to be doubled, i.e. `%%` instead of `%`. 
This is due to the fact, that Python treats single `%` as a string handler and will try to input a value as a replacement. 

##### Bad .html

Input:
```
<p>The share is 75%.</p>
```
Output: 
ValueError

##### Good .html

Input:
```
<p>The share is 75%%.</p>
```
Output:
The share is 75%.


##### example_3.html

```
<!DOCTYPE html>
<html>
<body>
<h1>CONGRATULATIONS!</h1>
<p>You won %(prize)s award, with %(percentage_votes)s%% share of votes.</p>

</body>
</html>
```

##### Email 4

```
  From: From Name <postmaster@domain.com>
  To: Albert Einstein <albert.einstein@emc2.edu>
  Subject: You won it!
  
  Body:
  CONGRATULATIONS!
  You won Scientist of the Century award, with 94.2% share of votes.
```
