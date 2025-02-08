# Experimental - using moviepy instead of ffmpeg
# TODO - get frame dimensions to match frame.py outputs
import os
import time
import json
import glob
import subprocess
import shlex
#from PIL import Image, ImageDraw, ImageFont
import imagehash
import numpy as np
from matplotlib import pyplot as plt 
from pathlib import Path
from urllib.parse import urlparse
from lib import util
from lib.frame import Frame
import re
from moviepy.editor import *

config = {
   "FRAME_PATH": "frames",
   "LAPLACIAN_PATH": "laplacian",
   "LAPLACIAN_THRESHOLD": 0.2,
   "LAPLACIAN_SIZE": 18,
   "LAPLACIAN_DISTANCE": 0.2,
   "PHASH_THRESHOLD": 0.2,
   "PHASH_SIZE": 18,
   "PHASH_DISTANCE": 4
}

class Video():
  #def __init__(self, filename, target_resolution=(750, 500), sample_fps=1):
  def __init__(self, filename, target_resolution=(500, 750), sample_fps=1):
    
    self.frames = []
    self.video_file = filename
    self.video_stem = Path(self.video_file).stem
    self.video_dir = Path(self.video_file).parent
    self.video_asset_dir = os.path.join(self.video_dir, self.video_stem)
    self.frame_dir = os.path.join( self.video_asset_dir, config["FRAME_PATH"])
    self.stream_info = self.get_stream_info(self.video_file)
    self.sample_fps = sample_fps
    self.target_resolution = target_resolution
    self.extract_frames()   

  def get_stream_info(self, force = False):
    
    stream_info_file = os.path.join(self.video_asset_dir, 'stream_info.json')

    # check to see if stream info already exists
    if os.path.exists(stream_info_file) and force == False:
        with open(stream_info_file, 'r', encoding="utf-8") as f:
            stream_info = json.loads(f.read())
        print(f"  get_stream_info: stream_info.json already exists. Use force=True to if you want to overwrite the existing stream_info. SKIPPING...")
        return stream_info
    
    video = urlparse(self.video_file)

    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(self.video_file):
        raise Exception('input video does not exist')
        
    util.mkdir(self.video_asset_dir)
    util.mkdir(self.frame_dir)

    command_string = f'ffprobe -v quiet -print_format json -show_format -show_streams {shlex.quote(self.video_file)}'
    
    # shlex.quote will place harmful input in quotes so it can't be executed by the shell
    # nosemgrep Rule ID: dangerous-subprocess-use-audit
    child_process = subprocess.Popen(
        shlex.split(command_string),
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = child_process.communicate()

    stream_info = json.loads(str(stdout, 'utf-8'))
    stream_info['format']['filename'] = self.video_file

    # parse video_info
    video_stream = list(filter(lambda x: (x['codec_type'] == 'video'), stream_info['streams']))[0]

    progressive = bool('field_order' not in video_stream or video_stream['field_order'] == 'progressive')
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    duration_ms = int(float(video_stream['duration']) * 1000)
    num_frames = int(video_stream['nb_frames'])
    framerate = util.to_fraction(video_stream['r_frame_rate'])
    sample_aspect_ratio = util.to_fraction(video_stream['sample_aspect_ratio'])
    display_aspect_ratio = util.to_fraction(video_stream['display_aspect_ratio'])
    display_width = int((width * sample_aspect_ratio.numerator) / sample_aspect_ratio.denominator)

    stream_info['video_stream'] = {
        'duration_ms': duration_ms,
        'num_frames': num_frames,
        'framerate': (framerate.numerator, framerate.denominator),
        'progressive': progressive,
        'sample_aspect_ratio': (sample_aspect_ratio.numerator, sample_aspect_ratio.denominator),
        'display_aspect_ratio': (display_aspect_ratio.numerator, display_aspect_ratio.denominator),
        'encoded_resolution': (width, height),
        'display_resolution': (display_width, height),
    }

    util.save_to_file(stream_info_file, stream_info)

    return stream_info
  
  def extract_frames(self, max_res=(750, 500), sample_rate_fps=1, force=False):
    """
    Extract individual frames from a video file as JPEG images.

    Args:
        max_res (tuple, optional): The maximum resolution for the extracted frames. Defaults to (750, 500).
        sample_rate_fps (int, optional): The desired frame rate (frames per second) for the extracted frames.
            Defaults to 1.

    Sets:
        self.frames[]: A list of file paths for the extracted JPEG frames.

    Raises:
        Exception: If the input video URL is not a valid local file path or HTTPS URL.
        Exception: If the input video file does not exist (for local file paths).

    Description:
        This function extracts individual frames from a video file and saves them as JPEG images
        in a 'frames' directory within the same directory as the video file.

        The function takes the video URL, the previously extracted stream_info (from the probe_stream function),
        an optional max_res parameter to specify the maximum resolution for the extracted frames, and an optional
        sample_rate_fps parameter to specify the desired frame rate for the extracted frames.

        If the video is interlaced, the function applies deinterlacing using the 'yadif' filter from FFmpeg.
        It then downscales the frames to the specified max_res using the 'scale' filter.

        The extracted frames are saved with sequential filenames (e.g., frames.0000001.jpg, frames.0000002.jpg, etc.)
        in the 'frames' directory. If the 'frames' directory already exists, the function skips the extraction process
        and returns the existing JPEG files.

        The function performs input validation to ensure that the provided video URL is a valid local file path
        or HTTPS URL, and that the file exists if it's a local file path.
    """
    video = urlparse(self.video_file)
    video_path = video.path
    video_dir = self.video_dir
    
    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(self.video_file):
        raise Exception('input video does not exist')
    
    frame_dir = self.frame_dir
    # Can't skip becasue we need the timestamps from the ffmpage command even if we have frames 
    #if len(self.frames) > 0 and force == False:
    #   print(f"  extract_frames: found frames. SKIPPING... Use the force=True option to regenerate frames")
    
    t0 = time.time()
    video_filters = []
    video_stream = self.stream_info['video_stream']

    clip = VideoFileClip(filename, target_resolution=self.target_resolution, audio=False)
    self.frames = []
    for t,frame in clip.iter_frames(fps=self.sample_fps, with_times=True):
        timestamp_millis = int(t * 1000)
        frame_filename = os.path.join(self.frame_dir, f"frame_{timestamp_millis}.jpeg")
        clip.save_frame(frame_filename,t=t)
        self.frames.append(Frame(frame_filename, timestamp_millis))
    
    t1 = time.time()
    print(f"  extract_frames: elapsed {round(t1 - t0, 2)}s")
    
    return 
  
  