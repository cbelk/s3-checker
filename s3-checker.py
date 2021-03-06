#!/usr/bin/env python

import boto3
import datetime
import json
import math
import os
import pygsheets
import requests
import sys
from botocore.exceptions import ClientError
from google.oauth2 import service_account

def convert_size(size_bytes):
    if size_bytes == 0:
        return '0B'
    size_name = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return '%s %s' % (s, size_name[i])

def create_sheet(gc, buckets):
    folder_id = gc.drive.get_folder_id(name='S3 Buckets') 
    sheet_name='S3Buckets-' + datetime.datetime.now().strftime('%Y/%m/%d')
    spreadsheet = gc.create(title=sheet_name, folder=folder_id)
    worksheet = spreadsheet.sheet1
    titles = [['Account', 'Bucket Name', 'Created By', 'Date Created', 'Project', 'Owner', 'Average Size', 'Encryption', 'Is Public', 'Permission Grants']]
    worksheet.update_values(crange='A1:J1', values=titles)
    headers = worksheet.range(crange='A1:J1')
    for header in headers[0]:
        header.set_text_format('bold', True)
        header.set_horizontal_alignment(pygsheets.custom_types.HorizontalAlignment.CENTER)
        header.color = (.698, .698, .694, 1.0)
    worksheet.frozen_rows = 1
    i = 2
    for account, bucks in buckets.items():
        for bucket in bucks:
            perms = ''
            for grant in bucket['grants']:
                perms += 'grantee: ' + grant['grantee'] + ' | type: ' + grant['type'] + ' | permission: ' + grant['permission'] + '\n'
            if bucket['averageSize'] == -1:
                avg = 'Data not available'
            else:
                avg = bucket['averageSize']
            row = [[account, bucket['name'], bucket['createdBy'], bucket['creationDate'], bucket['project'], bucket['owner'], avg, bucket['encryption'], bucket['isPublic'], perms]]
            worksheet.update_values(crange='A'+str(i)+':J'+str(i), values=row)
            if bucket['isPublic'] == 'True':
                worksheet.cell('I'+str(i)).color = (1.0, 0.0, 0.0, 1.0)
            markReview = False
            markDanger = False
            for grant in bucket['grants']:
                if grant['type'] == 'Group':
                    markReview = True
                    if grant['URI'] == 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers' or grant['URI'] == 'http://acs.amazonaws.com/groups/global/AllUsers':
                        markDanger = True
                elif grant['type'] == 'AmazonCustomerByEmail':
                    markReview = True
                elif grant['type'] == 'CanonicalUser':
                    if grant['grantee'] != bucket['owner']:
                        markReview = True
            if markReview:
                worksheet.cell('J'+str(i)).color = (1.0, 1.0, 0.0, 1.0)
            if markDanger:
                worksheet.cell('J'+str(i)).color = (1.0, 0.0, 0.0, 1.0)
            i += 1
    worksheet.adjust_column_width(1, 10)
    return sheet_name, worksheet.url

def clean_up(gc, days_old):
    sheets = gc.drive.list(corpora='user')
    datelimit = datetime.datetime.today() - datetime.timedelta(days=days_old)
    for sheet in sheets:
        if sheet['mimeType'] == 'application/vnd.google-apps.spreadsheet' and 'S3Buckets' in sheet['name']:
            if 'KEEP' in sheet['name']:
                continue
            d = sheet['name'].split('-')[1].split('/')
            date = datetime.datetime(int(d[0]), int(d[1]), int(d[2]))
            if date < datelimit:
                gc.drive.delete(sheet['id'])

def get_acl(s3client, buckets):
    for bucket in buckets:
        try:
            policy = s3client.get_bucket_policy_status(Bucket=bucket['name'])
            if policy['PolicyStatus']['IsPublic']:
                bucket['isPublic'] = 'True'
            else:
                bucket['isPublic'] = 'False'
        except s3client.exceptions.from_code('NoSuchBucketPolicy'):
            bucket['isPublic'] = 'No Policy Set'
        acl = s3client.get_bucket_acl(Bucket=bucket['name'])
        bucket['owner'] = acl['Owner']['DisplayName']
        bucket['grants'] = []
        for grant in acl['Grants']:
            bucket['grants'].append({'grantee': grant['Grantee']['DisplayName'], 'type': grant['Grantee']['Type'], 'permission': grant['Permission']})

def get_average_size(cwclient, buckets):
    seconds_in_a_day = 86400
    for bucket in buckets:
        metric = cwclient.get_metric_statistics(
            Namespace='AWS/S3',
            Dimensions=[{'Name': 'BucketName', 'Value': bucket['name']}, {'Name': 'StorageType', 'Value': 'StandardStorage'}],
            MetricName='BucketSizeBytes',
            StartTime=datetime.datetime.now() - datetime.timedelta(days=7),
            EndTime=datetime.datetime.now(),
            Period=seconds_in_a_day,
            Statistics=['Average'],
            Unit='Bytes'
        )
        if not metric['Datapoints']:
            # If no datapoints returned set to -1
            bucket['averageSize'] = -1.0
        else:
            total=0.0
            for point in metric['Datapoints']:
                total += point['Average']
            avg = total / len(metric['Datapoints'])
            bucket['averageSize'] = convert_size(avg)

def get_buckets(s3client):
    buckets = []
    i = 0
    bucks = s3client.list_buckets()
    for bucket in bucks['Buckets']:
        buckets.append({'name': bucket['Name'], 'creationDate': bucket['CreationDate'].strftime('%b %d, %Y')})
        buckets[i]['project'] = 'Tag N/A'
        buckets[i]['createdBy'] = 'Tag N/A'
        try:
            res = s3client.get_bucket_tagging(Bucket=bucket['Name'])
            if res['ResponseMetadata']['HTTPStatusCode'] != 200:
                print('Response code of ' + str(res['ResponseMetadata']['HTTPStatusCode']) + ' for bucket ' + bucket['Name'])
                buckets[i]['project'] = 'Tag N/A'
                buckets[i]['createdBy'] = 'Tag N/A'
                i += 1
                continue
            for tagset in res['TagSet']:
                if tagset['Key'] == 'Project':
                    buckets[i]['project'] = tagset['Value']
                elif tagset['Key'] == 'CreatedBy':
                    buckets[i]['createdBy'] = tagset['Value']
            i += 1
        except s3client.exceptions.from_code('NoSuchTagSet'):
            i += 1

    return buckets

def get_encryption(s3client, buckets):
    for bucket in buckets:
        try:
            encryption = s3client.get_bucket_encryption(Bucket=bucket['name'])
        except s3client.exceptions.from_code('ServerSideEncryptionConfigurationNotFoundError'):
            bucket['encryption'] = 'Default encryption not configured'
        else:
            bucket['encryption'] = encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']

def get_oauth2(region, name):
    client = boto3.client('secretsmanager', region_name=region)
    secret = {}
    try:
        secret_response = client.get_secret_value(SecretId='s3-bucket-checker/{}'.format(name))
    except ClientError as e:
        print(e)
    else:
        secret = json.loads(secret_response['SecretString'])
    return secret

def get_secrets(region, clouds):
    client = boto3.client('secretsmanager', region_name=region)

    accounts = {}
    for cloud in clouds:
        try:
            secret_response = client.get_secret_value(SecretId='s3-bucket-checker/{}'.format(cloud))
        except ClientError as e:
            print(e)
        else:
            secret = json.loads(secret_response['SecretString'])
            accounts[cloud] = {'key': secret['key'], 'secret': secret['secret']}
    return accounts

def get_slack_webhook(region, name):
    client = boto3.client('secretsmanager', region_name=region)
    channel = {}
    try:
        secret_response = client.get_secret_value(SecretId='s3-bucket-checker/{}'.format(name))
    except ClientError as e:
        print(e)
    else:
        channel = json.loads(secret_response['SecretString'])
    return channel

def post_slack(channel, sheet_name, worksheet_url):
    msg = 'Latest run: <{}|{}>'.format(worksheet_url, sheet_name)
    payload = {'text': msg}
    r = requests.post(channel['webhook'], data=json.dumps(payload), headers={'Content-Type': 'application/json'})
    if r.status_code != 200:
        print('Slack request returned code {}: {}'.format(r.status_code, r.text))

def main(event={}, context={}):
    # Sheets older than days_old will be deleted.
    # If running in lambda this can be set via environment variable DAYS_OLD
    days_old = 70
    channel = {}
    # Test if running in AWS Lambda or local and get keys and tokens
    inLambda = os.environ.get('AWS_EXECUTION_ENV') is not None
    if (inLambda):
        region = 'us-east-1'
        # Set this in the lambda functions CLOUD_ACCOUNTS envrionment variable
        if os.environ.get('CLOUD_ACCOUNTS') is not None:
            clouds = os.environ.get('CLOUD_ACCOUNTS').split(';')
        else:
            sys.exit('s3-bucket-checker: No cloud accounts set in CLOUD_ACCOUNTS variable.')
        # The google oauth2 secret name. Ex. this one is s3-bucket-checker/oauth2
        oauth2_name = 'oauth2'
        accounts = get_secrets(region, clouds)
        if not accounts:
            sys.exit('s3-bucket-checker: No account API keys retrieved.')
        service_account_info = get_oauth2(region, oauth2_name)
        if not service_account_info:
            sys.exit('s3-bucket-checker: No google service account oauth2 information retrieved.')
        SCOPES = ('https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive')
        credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        gc = pygsheets.authorize(custom_credentials=credentials)
        if os.environ.get('DAYS_OLD') is not None:
            days_old = int(os.environ.get('DAYS_OLD'))
        webhook_name = 'slack_webhook'
        channel = get_slack_webhook(region, webhook_name)
    else:
        with open('accounts') as acc:
            accounts = json.load(acc)
        with open('credentials.json') as cred:
            gc = pygsheets.authorize(service_file='credentials.json')
        with open('slack') as slack:
            channel = json.load(slack)

    buckets = {}
    for account, token in accounts.items():
        s3client = boto3.client( 's3', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'])
        buckets[account] = get_buckets(s3client)
        get_acl(s3client, buckets[account])
        get_encryption(s3client, buckets[account])
        cwclient = boto3.client( 'cloudwatch', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'], region_name='us-east-1')
        get_average_size(cwclient, buckets[account])

    sheet_name, worksheet_url = create_sheet(gc, buckets)
    clean_up(gc, days_old)

    if channel is not None:
        post_slack(channel, sheet_name, worksheet_url)

if __name__ == '__main__':
    main()
