#!/usr/bin/env python
from __future__ import print_function
import httplib2
import os
from apiclient import discovery
from google.oauth2 import service_account
import gspread
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from apiclient.http import MediaFileUpload
import pickle
import datetime

def create_spreadsheet():
#Scopes that we are using for the APIs
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
#Credentials
    secret_file = os.path.join(os.getcwd(), 'credentials.json')
    credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)
# Destination Folder
    folder_id = '10wm-laVa5QfzGschhCyi9CwFN2Q4Uehp'
    title = 'S3Buckets-' + datetime.datetime.now().strftime('%Y/%m/%d')
# Starting service + Creating a spreadsheet
    service = discovery.build('drive', 'v3', credentials=credentials)
    file_metadata = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id]
        }
    file = service.files().create(body=file_metadata).execute()
    print(file)

def main():
    with open ('bucketOfPickles', 'rb') as bop:
        buckets = pickle.load(bop)
    print(buckets)
# Running my create spreadsheet function
    create_spreadsheet()

if __name__ == '__main__':
    main()
