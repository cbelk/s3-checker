#!/usr/bin/env python
from __future__ import print_function
import httplib2
import os # need
from apiclient import discovery #need
from google.oauth2 import service_account # need
import gspread # need
import os.path # need
#from googleapiclient.discovery import build
#from google_auth_oauthlib.flow import InstalledAppFlow
#from google.auth.transport.requests import Request
#from google.oauth2.credentials import Credentials
from apiclient.http import MediaFileUpload # need
import pickle # need
import datetime # need
import pandas as pd #need
import numpy as np #nned


def populate_spreadsheet():
    #passing in created spreadsheet id from create_spreadsheet function
    #Scopes that we are using for the APIs TODO: make an auth function
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    #Credentials
    secret_file = os.path.join(os.getcwd(), 'credentials.json')
    credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    gc = gspread.service_account(filename=secret_file)
    #opening the created spreadsheet
    worksheet = gc.open_by_key(id).get_worksheet(0)
    with open ('bucketOfPickles', 'rb') as bop:
        buckets = pickle.load(bop)
    #print(buckets)
    df=np.array(buckets)
    worksheet.update(df.tolist())
    print(worksheet)

def create_spreadsheet():
    #Scopes that we are using for the APIs
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
          #Credentials
    secret_file = os.path.join(os.getcwd(), 'credentials.json')
    credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
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
    global id
    id = file['id']
    #print(file)
    print(id)

def main():
    # Running my create spreadsheet function
    create_spreadsheet()
    populate_spreadsheet()

if __name__ == '__main__':
    main()
