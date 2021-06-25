#!/usr/bin/env python

import boto3
import datetime
import json
import math
import pygsheets
from botocore.exceptions import ClientError

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
    spreadsheet = gc.create(title='S3Buckets-' + datetime.datetime.now().strftime('%Y/%m/%d'), folder=folder_id)
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
                perms += 'grantee: ' + grant['grantee'] + ' type: ' + grant['type'] + ' permission: ' + grant['permission'] + '\n'
            if bucket['averageSize'] == -1:
                avg = 'Data not available'
            else:
                avg = bucket['averageSize']
            row = [[account, bucket['name'], bucket['createdBy'], bucket['creationDate'], bucket['project'], bucket['owner'], avg, bucket['encryption'], bucket['isPublic'], perms]]
            worksheet.update_values(crange='A'+str(i)+':J'+str(i), values=row)
            i += 1
    worksheet.adjust_column_width(1, 10)

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
                # NOTE: replace with logging when moving to lambda
                print('Response code of ' + str(res['ResponseMetadata']['HTTPStatusCode']) + ' for bucket ' + bucket['Name'])
                buckets[i]['project'] = 'Tag N/A'
                buckets[i]['createdBy'] = 'Tag N/A'
                i += 1
                break
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
            bucket['encryption'] = encryption['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
        except s3client.exceptions.from_code('ServerSideEncryptionConfigurationNotFoundError'):
            bucket['encryption'] = 'Default encryption not configured'

def main():
    # Get access keys and secrets !! NOTE: will change to using aws secrets manager
    with open('accounts') as acc:
        accounts = json.load(acc)
    
    buckets = {}
    for account, token in accounts.items():
        s3client = boto3.client( 's3', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'])
        buckets[account] = get_buckets(s3client)
        get_acl(s3client, buckets[account])
        get_encryption(s3client, buckets[account])
        cwclient = boto3.client( 'cloudwatch', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'], region_name='us-east-1')
        get_average_size(cwclient, buckets[account])

    print(buckets)

    gc = pygsheets.authorize(service_file='credentials.json')
    create_sheet(gc, buckets)

if __name__ == '__main__':
    main()
