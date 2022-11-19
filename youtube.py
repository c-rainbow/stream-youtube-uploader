#!/usr/bin/python
# This file is modified from the sample code of Youtube Data API.

import http.client
import httplib2
import json
import random
import time
import datetime
import google.oauth2.credentials
import googleapiclient.discovery

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (
  IOError,
  httplib2.HttpLib2Error, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine,
)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

OAUTH_TOKEN_FILE = 'token.json'

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = [
  'https://www.googleapis.com/auth/youtube',
  'https://www.googleapis.com/auth/youtube.force-ssl',
  'https://www.googleapis.com/auth/youtube.readonly',
  'https://www.googleapis.com/auth/youtube.upload',
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

DEFAULT_PRIVACY_STATUS = 'unlisted'


def save_json_to_file(filename, jsonData):
  with open(filename, 'w') as f:
    json.dump(jsonData, f)


def credentials_to_dict(credentials):
  return {
    'token': credentials.token,
    'refresh_token': credentials.refresh_token,
    'token_uri': credentials.token_uri,
    'client_id': credentials.client_id,
    'client_secret': credentials.client_secret,
    'scopes': credentials.scopes,
  }


class YoutubeService:
  def __init__(self, token_file=OAUTH_TOKEN_FILE):
    self.token_file = token_file
    self.youtube = self._get_youtube_service()

  def _get_youtube_service(self):    
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
        self.token_file)
    original_creds_dict = credentials_to_dict(credentials)

    youtube = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    # Save credentials back to the token JSON file in case access token was refreshed.
    new_credentials_dict = credentials_to_dict(credentials)
    if original_creds_dict != new_credentials_dict:
      save_json_to_file(self.token_file, new_credentials_dict)
    
    return youtube
  
  def list_live_broadcasts(self):
    request = self.youtube.liveBroadcasts().list(
      part='id,snippet,contentDetails,status',
      mine=True,
    )
    broadcasts = request.execute()
    print('Live Broadcasts:', broadcasts)
    return broadcasts
  
  def list_live_streams(self):
    request = self.youtube.liveStreams().list(
      part='id,cdn,snippet,status',
      mine=True,
    )
    livestreams = request.execute()
    print('Live Streams:', livestreams)
    return livestreams
  
  def start_live_broadcast(self, title, privacyStatus=DEFAULT_PRIVACY_STATUS):
    scheduled_start_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
    body = {
      'snippet': {
        'title': title,
        'scheduledStartTime': scheduled_start_time.isoformat() + 'Z',
      },
      'status': {
        'privacyStatus': privacyStatus,
      },
      'contentDetails': {
        'enableAutoStart': True,
        'enableAutoStop': True,
      },
    }
    broadcast_request = self.youtube.liveBroadcasts().insert(
        part='id,snippet,contentDetails,status',
        body=body,
    )
    
    # Response type
    # https://developers.google.com/youtube/v3/live/docs/liveBroadcasts#resource
    broadcast = broadcast_request.execute()
    return broadcast
    
  def start_livestream(self, title):
    body = {
      'snippet': {
        'title': title,
      },
      'cdn': {
        'frameRate': 'variable',
        'ingestionType': 'hls',
        'resolution': 'variable'
      },
    }
    
    request = self.youtube.liveStreams().insert(
        part='id,snippet,cdn,contentDetails,status',
        body=body,
    )
    
    # Response type
    # https://developers.google.com/youtube/v3/live/docs/liveStreams#resource
    livestream = request.execute()
    return livestream
  
  def bind_broadcast_to_livestream(self, broadcast_id, livestream_id):
    # Bind the broadcast to the stream
    bind_request = self.youtube.liveBroadcasts().bind(
        id=broadcast_id,
        part='id,snippet',
        streamId=livestream_id
    )
    
    # Response type
    # https://developers.google.com/youtube/v3/live/docs/liveBroadcasts#resource
    bind_response = bind_request.execute()
    return bind_response
  
  def transition_to_live(self, broadcast_id):
    request = self.youtube.liveBroadcasts().transition(
      broadcastStatus='live',
      id=broadcast_id,
      part='id,snippet,contentDetails,status'
    )
    
    # Response type
    # https://developers.google.com/youtube/v3/live/docs/liveBroadcasts#resource
    response = request.execute()
    return response
  
    
  def upload(self, filepath, title=None, privacyStatus=DEFAULT_PRIVACY_STATUS):
    body = {
      'snippet': {
        'title': title,
      },
      'status': {
        'privacyStatus': privacyStatus
      },
    }

    # Call the API's videos.insert method to create and upload the video.
    insert_request = self.youtube.videos().insert(
      part=','.join(list(body.keys())),
      body=body,
      # Setting 'chunksize' equal to -1 in the code below means that the entire
      # file will be uploaded in a single HTTP request. (If the upload fails,
      # it will still be retried where it left off.)
      media_body=MediaFileUpload(filepath, chunksize=-1, resumable=True)
    )

    self.resumable_upload(insert_request)

  # This method implements an exponential backoff strategy to resume a
  # failed upload.
  def resumable_upload(self, insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
      try:
        print('Uploading file...')
        status, response = insert_request.next_chunk()
        if response is not None:
          if 'id' in response:
            print('Video id "%s" was successfully uploaded.' % response['id'])
          else:
            exit('The upload failed with an unexpected response: %s' % response)
      except HttpError as e:
        if e.resp.status in RETRIABLE_STATUS_CODES:
          error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                              e.content)
        else:
          raise
      except RETRIABLE_EXCEPTIONS as e:
        error = 'A retriable error occurred: %s' % e

      if error is not None:
        print(error)
        retry += 1
        if retry > MAX_RETRIES:
          exit('No longer attempting to retry.')

        max_sleep = 2 ** retry
        sleep_seconds = random.random() * max_sleep
        print('Sleeping %f seconds and then retrying...' % sleep_seconds)
        time.sleep(sleep_seconds)

'''
if __name__ == '__main__':
  argparser.add_argument('--file', required=True, help='Video file to upload')
  argparser.add_argument('--title', help='Video title', default='Test Title')
  argparser.add_argument('--description', help='Video description',
    default='Test Description')
  argparser.add_argument('--category', default='22',
    help='Numeric video category. ' +
      'See https://developers.google.com/youtube/v3/docs/videoCategories/list')
  argparser.add_argument('--keywords', help='Video keywords, comma separated',
    default='')
  argparser.add_argument('--privacyStatus', choices=VALID_PRIVACY_STATUSES,
    default=VALID_PRIVACY_STATUSES[0], help='Video privacy status.')
  args = argparser.parse_args()

  if not os.path.exists(args.file):
    exit('Please specify a valid file using the --file= parameter.')

  youtube = get_youtube_service(args)
  try:
    initialize_upload(youtube, args)
  except HttpError as e:
    print('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))
'''