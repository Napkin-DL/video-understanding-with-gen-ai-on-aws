"""
Module: ffmpeg_helper.py

Description:
This module provides utility functions to work with video files using the FFmpeg library.
It allows you to extract metadata, individual frames, audio, and create a low-resolution
version of a video file.

Functions:
- probe_stream(video_url)
- extract_frames(video_url, stream_info, max_res=(750, 500))
- extract_audio(video_url)
- create_lowres_video(video_url, stream_info, max_res=(360, 202))

Dependencies:
- os
- time
- json
- glob
- subprocess
- shlex
- pathlib
- urllib.parse
- lib.util (custom module)

Usage:
1. Import the module: `import ffmpeg_helper`
2. Call the desired function with the appropriate arguments.

Example:
stream_info = ffmpeg_helper.probe_stream('path/to/video.mp4')
frames = ffmpeg_helper.extract_frames('path/to/video.mp4', stream_info)
audio_file = ffmpeg_helper.extract_audio('path/to/video.mp4')
lowres_video = ffmpeg_helper.create_lowres_video('path/to/video.mp4', stream_info)
"""

import os
import time
import json
import glob
import subprocess
import shlex
from pathlib import Path
from urllib.parse import urlparse
from lib import util
import re

def probe_stream(video_url):
    """
    Probe a video file and extract metadata information.

    Args:
        video_url (str): The URL or local file path of the video file.

    Returns:
        dict: A dictionary containing the extracted metadata information.

    Raises:
        Exception: If the input video URL is not a valid local file path or HTTPS URL.
        Exception: If the input video file does not exist (for local file paths).

    Description:
        This function uses the FFprobe command from the FFmpeg library to extract
        metadata information about a video file, such as duration, frame rate,
        resolution, and aspect ratio.

        The extracted metadata is saved in a JSON file named 'stream_info.json'
        in the same directory as the video file. If the 'stream_info.json' file
        already exists, the function skips the probing process and returns the
        existing metadata.

        The function performs input validation to ensure that the provided video
        URL is a valid local file path or HTTPS URL, and that the file exists if
        it's a local file path.
    """
    video = urlparse(video_url)
    video_file = video.path
    video_dir = Path(video_file).stem
    stream_info_file = os.path.join(video_dir, 'stream_info.json')

    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(video_file):
        raise Exception('input video does not exist')
        
    util.mkdir(video_dir)

    # check to see if wav file already exists
    if os.path.exists(stream_info_file):
        with open(stream_info_file, 'r', encoding="utf-8") as f:
            stream_info = json.loads(f.read())
        print(f"  probe_stream: found stream_info.json. SKIPPING...")
        return stream_info

    command_string = f'ffprobe -v quiet -print_format json -show_format -show_streams {shlex.quote(video_url)}'
    
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
    stream_info['format']['filename'] = video_file

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

def extract_frames(video_url, stream_info, max_res=(750, 500), sample_rate_fps=1):
    """
    Extract individual frames from a video file as JPEG images.

    Args:
        video_url (str): The URL or local file path of the video file.
        stream_info (dict): A dictionary containing the metadata information of the video file.
        max_res (tuple, optional): The maximum resolution for the extracted frames. Defaults to (750, 500).
        sample_rate_fps (int, optional): The desired frame rate (frames per second) for the extracted frames.
            Defaults to 1.

    Returns:
        list: A list of file paths for the extracted JPEG frames.

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
    video = urlparse(video_url)
    video_file = video.path
    video_dir = Path(video_url).stem
    
    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(video_file):
        raise Exception('input video does not exist')
    
    frame_dir = os.path.join(video_dir, 'frames')
    #if os.path.exists(frame_dir):
    #    jpeg_frames = sorted(glob.glob(f"{frame_dir}/*.jpg"))
    #    print(f"  extract_frames: found {len(jpeg_frames)} frames. SKIPPING...")
        
    util.mkdir(frame_dir)
    
    t0 = time.time()
    video_filters = []
    video_stream = stream_info['video_stream']
    
    # This is a video filter option that sets the frame rate to the specified frames per second. 
    # The fps filter adjusts the frame rate by duplicating or dropping frames as necessary. 
    video_filters.append(f"fps={sample_rate_fps},showinfo")
    
    # need deinterlacing
    progressive = video_stream['progressive']
    if not progressive:
        video_filters.append('yadif')
    
    # downscale image
    dw, dh = video_stream['display_resolution']
    factor = max((max_res[0] / dw), (max_res[1] / dh))
    w = round((dw * factor) / 2) * 2
    h = round((dh * factor) / 2) * 2
    video_filters.append(f"scale={w}x{h}")

    command = [
        'ffmpeg',
        #'-v',
        #'quiet',
        '-i',
        shlex.quote(video_url),
        # DEBUG: Just get the first 60 seconds
        #'-t',
        #str(60),
        '-vf',
        f"{','.join(video_filters)}",
        '-r',
        str(sample_rate_fps),
        '-f',
        'image2',
        f"{shlex.quote(frame_dir)}/frames%07d.jpg"
    ]
    
    print(f"  Resizing: {dw}x{dh} -> {w}x{h} (Progressive? {progressive})")
    print(f"  Command: {command}")
    
    frame_timestamps = []
    try:
        # user input is wrapped in shlex above
        # nosemgrep: dangerous-subprocess-use-audit
        result = subprocess.run(command, shell=False, stdout=subprocess.PIPE, 
                                stderr=subprocess.STDOUT, universal_newlines=True, check=True)
        
        jpeg_frames = sorted(glob.glob(f"{frame_dir}/*.jpg"))
        
        index = 0
        for line in result.stdout.splitlines():
            if "pts_time" in line:
                timestamp = float(line.split("pts_time:")[1].split()[0])
                frame_timestamps.append({
                    'file': jpeg_frames[index],
                    'timestamp_milliseconds': timestamp * 1000
                })
                index+=1
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stdout}")
    
    t1 = time.time()
    print(f"  extract_frames: elapsed {round(t1 - t0, 2)}s")
    
    return frame_timestamps

def extract_audio(video_url):
    """
    Extract the audio stream from a video file and save it as a WAV file.

    Args:
        video_url (str): The URL or local file path of the video file.

    Returns:
        str: The file path of the extracted audio file (WAV format).

    Raises:
        Exception: If the input video URL is not a valid local file path or HTTPS URL.
        Exception: If the input video file does not exist (for local file paths).

    Description:
        This function extracts the audio stream from a video file and saves it as a WAV file
        in the same directory as the video file, with the filename 'audio.wav'.

        The function takes the video URL as input and performs the following steps:

        1. Parse the video URL to extract the file path and directory.
        2. Check if the input video URL is a valid local file path or HTTPS URL.
        3. Check if the input video file exists (for local file paths).
        4. Check if the 'audio.wav' file already exists in the same directory as the video file.
           If it exists, the function skips the extraction process and returns the existing file path.
        5. If the 'audio.wav' file does not exist, the function runs the FFmpeg command to extract
           the audio stream from the video file and save it as a WAV file with the following settings:
           - Bitrate: 96k
           - Sampling rate: 16000 Hz
           - Number of channels: 1 (mono)
           - Audio codec: pcm_s16le (Signed 16-bit Little-Endian PCM)

        The function prints the FFmpeg command being executed and the elapsed time for the extraction process.

        Note: The function uses the `shlex.quote` function to properly escape and quote the video URL,
        ensuring that any harmful input is safely handled when executing the FFmpeg command.
    """
    t0 = time.time()
    
    video = urlparse(video_url)
    video_file = video.path
    video_dir = Path(video_file).stem
    
    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(video_file):
        raise Exception('input video does not exist')

    audio_dir = Path(urlparse(video_url).path).stem
    wav_file = os.path.join(audio_dir, 'audio.wav')

    # check to see if wav file already exists
    if os.path.exists(wav_file):
        print(f"  extract_audio: found audio.wav. SKIPPING...")
        return wav_file

    # run ffmpeg to extract audio
    bitrate = '96k'
    sampling_rate = 16000
    channel = 1
    command = [
        'ffmpeg',
        '-i',
         shlex.quote(video_url),
        '-vn',
        '-c:a',
        'pcm_s16le',
        '-ab',
        bitrate,
        '-ar',
        str(sampling_rate),
        '-ac',
        str(channel),
        wav_file
    ]
    print(command)
    
    # shlex.quote will place harmful input in quotes so it can't be executed by the shell
    # nosemgrep Rule ID: dangerous-subprocess-use-audit
    subprocess.run(
        command,
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    t1 = time.time()
    print(f"  extract_audio: elapsed {round(t1 - t0, 2)}s")
    return wav_file

def create_lowres_video(video_url, stream_info, max_res=(360, 202)):
    """
    Create a low-resolution version of a video file.

    Args:
        video_url (str): URL or local file path to the input video file.
        stream_info (dict): Dictionary containing information about the video stream,
            including the video stream index, display resolution, and whether the
            video is progressive or interlaced.
        max_res (tuple, optional): Maximum resolution (width, height) for the
            low-resolution video. Defaults to (360, 202).

    Returns:
        str: Local file path to the created low-resolution video file.

    Raises:
        Exception: If the input video URL is not a valid file path or HTTPS URL,
            or if the input video file does not exist (for local file paths).

    This function creates a low-resolution version of the input video file by
    downscaling the resolution and applying deinterlacing if necessary. The
    low-resolution video is saved as an MP4 file in the same directory as the
    original video file, with the filename 'lowres_video.mp4'.

    If the 'lowres_video.mp4' file already exists, the function skips the
    downscaling process and returns the existing file path.
    """

    video = urlparse(video_url)
    video_file = video.path
    video_dir = Path(video_file).stem
    
    # input check: video is a file or https 
    if video.scheme not in ['https', 'file', '']:
        raise Exception('input video must be a local file path or use https')
    
    # input check: file scheme video exists
    if video.scheme == 'file' and not os.path.exists(video_file):
        raise Exception('input video does not exist')
    
    low_res_video_file = os.path.join(video_dir, 'lowres_video.mp4')

    # check to see if video file already exists
    if os.path.exists(low_res_video_file):
        print(f"  create_lowres_video: found lowres_video.mp4. SKIPPING...")
        return low_res_video_file

    util.mkdir(video_dir)

    video_stream = stream_info['video_stream']

    video_filters = []
    # need deinterlacing
    progressive = video_stream['progressive']
    if not progressive:
        video_filters.append('yadif')

    # downscale image
    dw, dh = video_stream['display_resolution']
    factor = max((max_res[0] / dw), (max_res[1] / dh))
    w = round((dw * factor) / 2) * 2
    h = round((dh * factor) / 2) * 2
    video_filters.append(f"scale={w}x{h}")

    # ffmpeg -ss 588 -i f"{video_url}" -vf "yadif,scale=iw*sar:ih" -frames:v 1 test2.jpg
    command = [
        'ffmpeg',
        '-v',
        'quiet',
        '-i',
        shlex.quote(video_url),
        '-vf',
        f"{','.join(video_filters)}",
        '-ac',
        str(2),
        '-ab',
        '64k',
        '-ar',
        str(44100),
        f"{low_res_video_file}"
    ]

    print(f"  Downscaling: {dw}x{dh} -> {w}x{h} (Progressive? {progressive})")
    print(f"  Command: {command}")

    t0 = time.time()
    
    # shlex.quote will place harmful input in quotes so it can't be executed by the shell
    # nosemgrep Rule ID: dangerous-subprocess-use-audit
    subprocess.run(
        command,
        shell=False,
        stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL
    )

    t1 = time.time()
    print(f"  downscale_video: elapsed {round(t1 - t0, 2)}s")

    return low_res_video_file
