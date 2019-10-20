Mailgun is a leading platform for sending transactional emails. This component builds on Mailgun's powerful API and allows anybody to send transactional emails with attachments from sandbox/production domains.

Basic requirements are:

  * Mailgun account;
  * a domain.

This component takes as input a table of email addresses and names, to which an email is sent. In the table, other attributes can be added, which will then be used to fill in the html body (e.g. date of birth, etc.).
**The input table needs to contain following columns: `email`, `subject` and one of `html_file` or `text`. All other columns are optional.**