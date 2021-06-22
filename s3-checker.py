#!/usr/bin/env python

import boto3
import datetime
import json
from botocore.exceptions import ClientError

def get_acl(s3client, buckets):
    for bucket in buckets:
        try:
            policy = s3client.get_bucket_policy_status(Bucket=bucket['name'])
            bucket['isPublic'] = policy['PolicyStatus']['IsPublic']
        except s3client.exceptions.from_code('NoSuchBucketPolicy'):
            bucket['isPublic'] = 'No Policy Set'
        acl = s3client.get_bucket_acl(Bucket=bucket['name'])
        bucket['owner'] = acl['Owner']['DisplayName']
        bucket['grants'] = []
        for grant in acl['Grants']:
            bucket['grants'].append({'grantee': grant['Grantee']['DisplayName'], 'type': grant['Grantee']['Type'], 'permission': grant['Permission']})

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

def main():
    # Get access keys and secrets !! NOTE: will change to using aws secrets manager
    with open('accounts') as acc:
        accounts = json.load(acc)
    
    buckets = {}
    for account, token in accounts.items():
        s3client = boto3.client( 's3', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'])
        buckets[account] = get_buckets(s3client)

    for account, token in accounts.items():
        s3client = boto3.client( 's3', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'])
        get_acl(s3client, buckets[account])
    print(buckets)

if __name__ == '__main__':
    main()
