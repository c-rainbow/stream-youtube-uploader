import time
import subprocess
from datetime import datetime
import streamlink
from typing import Tuple
import threading
from youtube import YoutubeService

import json
import requests
import pprint

COMMAND = 'streamlink twitch.tv/{username} {qualities} -o {filename} --twitch-disable-ads --twitch-disable-hosting'


def generate_playlist(sequence):
  lines = [
    '#EXTM3U',
    '#EXT-X-VERSION:3',
    '#EXT-X-MEDIA-SEQUENCE:%d' % sequence,
    '#EXT-X-TARGETDURATION:5',
  ]
  for i in range(sequence, sequence + 5):
    lines.append('#EXTINF:2.000')
    lines.append('%d.ts' % i)
    
  return '\n'.join(lines)




def check(username: str, qualities: Tuple[str]=('best',), sleep_duration_seconds: float=5.0):
  while True:
    try:
      streams = streamlink.streams('https://twitch.tv/%s' % username)
      current_time = str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
      filename = './%s-%s.ts' % (username, current_time)
      if streams:
        command = COMMAND.format(
          username=username, qualities=','.join(qualities), filename=filename)
        subprocess.call(command.split(' '))
        # Upload to youtube after download is finished
        upload_thread = threading.Thread(target=upload_to_youtube, args=(filename,))
        upload_thread.start()
      else:
        print('No stream as of', current_time)
    except Exception as e:
      print('Error:', e)
    time.sleep(sleep_duration_seconds)

def start_live_broadcast(title: str):
  youtube = YoutubeService()
  response = youtube.start_live_broadcast(title)
  print(response)
  
def start_live_stream():
  youtube = YoutubeService()
  response = youtube.start_livestream('Test title of livestream')
  pretty = json.dumps(response)
  print(pretty)
  
  

FILENAME = '0.ts'

LOCAL_FILENAME = '2022-11-18-ads.ts'
    
if __name__ == '__main__':
  '''
  current_time = str(datetime.now())
  youtube =  YoutubeService()
  broadcast = youtube.start_live_broadcast('Broadcast ' + current_time)
  livestream = youtube.start_livestream('Livestream ' + current_time)
  bind = youtube.bind_broadcast_to_livestream(broadcast['id'], livestream['id'])
  
  address = livestream['cdn']['ingestionInfo']['ingestionAddress']
  print('Broadcast:')
  pprint.pprint(broadcast)
  print('Livestream:')
  pprint.pprint(livestream)
  print('Bind:')
  pprint.pprint(bind)
  '''
  #address = ''
  #m3u8url = ''
  #url = address + 'playlist.m3u8'
  
  #playlist = requests.get(m3u8url).text
  #print(playlist)
  #with open('2022-11-18-720p.m3u8', 'r', encoding='utf-8') as f:
  #  playlist = f.read()
  #response = requests.post(url, data=playlist)
  #print(response.status_code)
  #print(response.text)
  address = ''
  #with open('test-segment.ts', 'rb') as f:
  #  content = f.read()
  #  print('len:', len(content))
    
  
  sequence = 0
  while True:
    playlist = generate_playlist(sequence)
    #print(playlist)
    r = requests.post(address + 'master.m3u8', data=playlist)
    print('Playlist sequence', sequence, ':', r.status_code)
    with open('vod720/%d.ts' % (sequence + 10), 'rb') as f:
        content = f.read()
    r = requests.post(address + ('%d.ts' % sequence), data=content)
    print('Segment sequence', sequence, ':', r.status_code)
    sequence += 1
    time.sleep(2)  
  