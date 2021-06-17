#!/usr/bin/env python

import boto3
import datetime
import json
from botocore.exceptions import ClientError

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
        except ClientError:
            buckets[i]['project'] = 'Tag N/A'
            buckets[i]['createdBy'] = 'Tag N/A'
            i += 1
    return buckets

def main():
    # Get access keys and secrets !! NOTE: will change to using aws secrets manager
    with open('accounts') as acc:
        accounts = json.load(acc)
    
    for account, token in accounts.items():
        s3client = boto3.client( 's3', aws_access_key_id=token['key'], aws_secret_access_key=token['secret'])
        buckets = get_buckets(s3client)
        print(buckets)

if __name__ == '__main__':
    main()
