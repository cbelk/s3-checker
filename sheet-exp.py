#!/usr/bin/env python
from __future__ import print_function
import httplib2
import os # need
from apiclient import discovery #need
from google.oauth2 import service_account # need
import gspread # need
import os.path # need
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from apiclient.http import MediaFileUpload # need
import pickle # need
import datetime # need
import pandas as pd #need
import numpy as np #need

def create_spreadsheet():
    #Scopes that we are using for the APIs #TODO: maybe make auth a function?
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
    global id #TODO: make sure this is the best way to set the id variable for use in other function
    id = file['id']
    #print(file) # TODO: delete. using for testing
    print(id) # TODO: can comment out/del this line. using it for testing to track id value

def populate_spreadsheet():
    #passing in created spreadsheet id from create_spreadsheet function
    #TODO: maybe make auth a function?
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
                  'https://www.googleapis.com/auth/drive']
    #Credentials
    secret_file = os.path.join(os.getcwd(), 'credentials.json')
    credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    gc = gspread.service_account(filename=secret_file)
    #opening the created spreadsheet based on id num
    worksheet = gc.open_by_key(id).get_worksheet(0)
    # TODO: Delete use of test data
    with open ('bucketOfPickles', 'rb') as bop:
        buckets = pickle.load(bop)
    #print(buckets)
    # END OF TEST DATA
    # TODO: set up ability to read in the dictionary

    print(worksheet)


def main():
    # Running my create spreadsheet function
    create_spreadsheet()
    populate_spreadsheet()

if __name__ == '__main__':
    main()
