#!/usr/bin/env python

import boto3
import datetime
import json
import math
from botocore.exceptions import ClientError

def convert_size(size_bytes):
   if size_bytes == 0:
       return '0B'
   size_name = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return '%s %s' % (s, size_name[i])

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
            buckets[i]['project'] = 'Tag N/A'
            buckets[i]['createdBy'] = 'Tag N/A'
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

if __name__ == '__main__':
    main()
