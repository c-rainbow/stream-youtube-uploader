import time
from datetime import datetime
import streamlink
from typing import Tuple
from youtube import YoutubeService

import m3u8
import json
import requests



def generate_playlist(sequence, segment):
  return '\n'.join([
    '#EXTM3U',
    '#EXT-X-VERSION:3',
    '#EXT-X-MEDIA-SEQUENCE:%d' % sequence,
    '#EXT-X-TARGETDURATION:5',
    '#EXTINF:%d' % segment.duration,
    '%d.ts' % sequence
  ])


class LivestreamRelay:
  
  def __init__(self, username: str):
    self.username = username
    
  # TODO: use quality parameters
  def check(self, sleep_duration_seconds: float=5.0):
    while True:
      try:
        streams = streamlink.streams('https://twitch.tv/%s' % self.username)
        if streams:
          playlist_url = streams['best'].url
          print('Stream found for', self.username)
          print('Source media playlist URL:', playlist_url)
          self.start_livestream_relay(playlist_url)
        else:
          print('No stream of', self.username, 'as of', datetime.now())
      except Exception as e:
        print('Error:', e)
      time.sleep(sleep_duration_seconds)

  def start_livestream_relay(self, playlist_url: str):
    current_time = str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    youtube = YoutubeService()
    broadcast = youtube.start_live_broadcast('Broadcast ' + current_time)
    livestream = youtube.start_livestream('Livestream ' + current_time)
    bind = youtube.bind_broadcast_to_livestream(broadcast['id'], livestream['id'])
    
    ingestion_url = livestream['cdn']['ingestionInfo']['ingestionAddress']
    
    sequence = 0
    segment_uris = set()
    while True:
      try:
        source_playlist = m3u8.load(playlist_url)
        for segment in source_playlist.segments:
          if segment.uri in segment_uris:  # Skip seen segment URIs
            continue
          segment_uris.add(segment.uri)
          
          if 'Amazon' in segment.title:  # Skip ads
            print('Skipping ads..')
            continue

          # TODO: error handling
          media_playlist = generate_playlist(sequence, segment)
          requests.post(ingestion_url + 'master.m3u8', data=media_playlist)
          print('uploaded playlist')
          
          response = requests.get(segment.uri)
          requests.post(ingestion_url + ('%d.ts' % sequence), data=response.content)
          print('uploaded segment of length', len(response.content))
          
          sequence += 1   
      except Exception as e:
        print('Error getting playlist or segment:', e)
      time.sleep(2)
    
    
if __name__ == '__main__':
  relay = LivestreamRelay('')  # Add streamer's username
  relay.check()
  