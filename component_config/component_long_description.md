# Mailgun

Mailgun is an email automation service. It offers a complete cloud-based email service for sending, receiving and tracking email sent through your websites and applications. This component allows to connect Mailgun with Keboola platform, for sending automation.

To successfully operate the component, following parameters are required:

- a private API key for Mailgun,
- a Mailgun domain.

If you're unsure on where to find the API key, follow the steps mentioned in the [documentation](https://help.mailgun.com/hc/en-us/articles/203380100-Where-Can-I-Find-My-API-Key-and-SMTP-Credentials-) on how to obtain the API key. When it comes to Mailgun domains, upon registering each user is provisioned a sandbox domain. The sandbox domain can only send email to [**authorized recipients**](https://help.mailgun.com/hc/en-us/articles/217531258-Authorized-Recipients). The limit is 5 authorized recipients per sandbox domain. It is therefore highly recommended to [register your own domain with Mailgun](https://help.mailgun.com/hc/en-us/articles/202256730-How-do-I-pick-a-domain-name-for-my-Mailgun-account-) to not be limited by sandbox restrictions.

##### Pricing

Note that Mailgun is a paid service and is subject to [Mailgun's Terms Of Service](https://www.mailgun.com/terms/). By default, each domain can send up to 10 000 emails per month for free. For more information about pricing, please visit [Mailgun's pricing explorer](https://www.mailgun.com/pricing).

## Changes from previous version

With a new version of Mailgun component, there were some changes, which make this version non-backwards compatible and hence some effort is required to migrate. Major changes include:

1. A region can be specified in the configuration (see [Parameters](https://bitbucket.org/kds_consulting_team/kds-team.app-mailgun-v2/src/master/README.md#markdown-header-parameters))
2. Changed column names for input table and support of more Mailgun features (see [Mailing list](https://bitbucket.org/kds_consulting_team/kds-team.app-mailgun-v2/src/master/README.md#markdown-header-mailing-list))
3. Sending tabular attachments straight from Keboola storage (see [Table input mapping](https://bitbucket.org/kds_consulting_team/kds-team.app-mailgun-v2/src/master/README.md#markdown-header-table-input-mapping))
4. Improved specification of attachments and templates and automatic selection of latest available file (see [Path specification to template or file attachment](https://bitbucket.org/kds_consulting_team/kds-team.app-mailgun-v2/src/master/README.md#markdown-header-path-specification-to-template-or-file-attachment))
5. Subject, plain-text or html template are now customized using `{{COLUMN_NAME}}` tags, instead of `%(COLUMN_NAME)s` as before (see [Email customization](https://bitbucket.org/kds_consulting_team/kds-team.app-mailgun-v2/src/master/README.md#markdown-header-email-customization))