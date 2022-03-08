# S3 bucket checker

### Description
Python script for pulling information about the organization's S3 buckets and writing it to a Google Sheet. For each S3 bucket the script attempts to pull the following:
* Name
* Creation date
* Tags
* Owner
* Average size
* Encryption
* Policy
* ACLs

The bucket's policies and ACLs are then used to determine if the bucket is considered public as described in [AWS documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html#access-control-block-public-access-policy-status). If the bucket is public the "Is Public" cell for that bucket in the sheet is highlighted red and ACL grants that should be reviewed are highlighted yellow.

The script will put the information gathered into a Google Sheet titled "S3Buckets-YYYY/MM/DD". It will also delete sheets in the folder whose name indicates they are older than a specified time frame (default 70 days), unless "KEEP" has been added to the sheet's name.

Although this script can be run locally it was designed to run in AWS Lambda. When running in Lambda the keys and tokens for AWS and Google are stored in the AWS Secrets Manager. The script can also post a link to the latest run in a specified Slack chennel if the appropriate webhook is provided.

### Installation and Configuration
#### Deploying in Lambda
This script depends on two libraries that are not in the Lambda runtime environment, so they will need to be packaged and deployed with the Lambda function as decribed [here](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-update-venv). They are [pygsheets](https://pygsheets.readthedocs.io/en/stable/) and [requests](https://docs.python-requests.org/en/master/). 

To get the bucket information, you will need access keys and tokens for each account that you want to monitor. These will need to be associated with an account that has read access to S3 and CloudWatch. Store each key/secret in the [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/tutorials_basic.html#tutorial-basic-step1). For the secret name use: s3-bucket-checker/\<name\>, where <name> differentiates the accounts you are wanting to monitor (eg <name> could be the names of the different accounts you are monitoring). For the key/value pairs for each secret you will need to store:
  
  key: \<access-key-id\>
  
  secret: \<access-key-secret\>

To write the information to a Google Sheet in Drive, create a [service account](https://developers.google.com/workspace/guides/create-credentials#service-account) that has access to your Drive. Store the Oauth2 information in Secrets Manager using the name s3-bucket-checker/oauth2 and the key/value pairs:
  
  type: service account
  
  project_id: \<project-id\>
  
  private_key_id: \<private-key-id\>
  
  private_key: \<private-key\>
  
  client_email: \<service-account-email\>
  
  client_id: \<service-account-id\>
  
  auth_uri: \<google-oauth-url\>
  
  token_uri: \<google-token-url\>
  
  auth_provider_x509_cert_url: \<google-api-oauth-cert-url\>
  
  client_x509_cert_url: \<google-api-service-account-x509-cert-url\>
  
To notify a Slack channel after a run with a link to the Google Sheet, create a Slack app with an [incoming webhook](https://api.slack.com/messaging/webhooks). Store the webhook information in Secrets Manager using the name s3-bucket-checker/slack_webhook and the key/value pair:
  
  channel: \<channel_name\>
  
  webhook: \<webhook-url\>

The following envrionment variables are used for configuration:
  
  CLOUD_ACCOUNTS - This is a list of AWS accounts that are being monitored. These will be the names used when you created the secrets for the AWS access keys/tokens in Secrets Manager. The names are seperated by semi-colons (eg account1;account2;account3).
  
  DAYS_OLD - Sheets older than this number that don't have "KEEP" in the name will be deleted when the Lambda function runs. If not provided, the default is 70 days.
