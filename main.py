import time
import subprocess
from datetime import datetime
import streamlink
from typing import Tuple
import threading
from youtube import YoutubeService

COMMAND = 'streamlink twitch.tv/{username} {qualities} -o {filename} --twitch-disable-ads --twitch-disable-hosting'


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

def upload_to_youtube(filename: str):
  youtube = YoutubeService()
  youtube.upload(filename, title='Test Title')


    
if __name__ == '__main__':
  check('c_rainbow_test2')