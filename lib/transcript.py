import os
import boto3
import time
import json
from pathlib import Path
#from urllib.request import urlretrieve
from termcolor import colored
import requests
from lib import util

class Transcript():
    def __init__(self, video_file, bucket, force=False):

        # start transcription job
        self.video_file = video_file
        self.object = util.upload_object(bucket, self.video_stem(), video_file)
        self.transcript, self.vtt_file, self.transcript_file = self.transcribe(video_file, self.object)
        self.sentences, self.sentences_file = self.make_sentences(self.transcript)
    
    def url_retrieve(self, url: str, outfile: Path):
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        with open(outfile,'wb') as f:
            f.write(r.content)

    def transcribe(self, video_file, object, media_format="mp4", language_code="en-US", verbose=True):
        """
        Extracts the transcription from the given video file using Amazon Transcribe.
        Visit here: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/transcribe/client/start_transcription_job.html for more information about the API.
        
        Args:
           video_file - source video file 
           object - S3 location path for the video file
           media_format - format of the given video file
           language_code - the language code to guide the transcription
           verbose - verbose output from the 
           
        """
        vtt_file = os.path.join(self.video_asset_dir(), 'transcript.vtt')
        transcript_file = os.path.join(self.video_asset_dir(), 'transcript.json')
        transcript = {}
        
        # check to see if transcript already exists
        if os.path.exists(vtt_file) and os.path.exists(transcript_file):
            print(f"Transcript already exists for {video_file} use force=True to force regeneration... SKIPPING")
            
            with open(os.path.join(self.video_asset_dir(), 'transcript.json'), encoding="utf-8") as f:
                transcript = json.load(f)
            return (transcript, vtt_file, transcript_file)

        # start transcription job
        transcribe_response = self.start_transcription_job(
            object["Bucket"],
            object["Key"],
            video_file, media_format, language_code)

        # wait for completion
        transcribe_response = self.wait_for_transcription_job(
            transcribe_response['TranscriptionJob']['TranscriptionJobName'], 
            verbose)
        
        vtt_file = self.download_vtt(transcribe_response, self.video_asset_dir())
        transcript, transcript_file = self.download_transcript(transcribe_response, self.video_asset_dir()) 
        
        return (transcript, vtt_file, transcript_file)


    def start_transcription_job(self, bucket, key, file, media_format="mp4", language_code="en-US"):

        # create a random job name
        job_name = '-'.join([
            Path(file).stem,
            os.urandom(4).hex(),
        ])

        transcribe_client = boto3.client('transcribe')

        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode=language_code,
            MediaFormat=media_format,
            Media={
                'MediaFileUri': f"s3://{bucket}/{key}",
            },
            Subtitles={
                'Formats': [
                    'vtt',
                ],
            },
        )
        
        return response

    def wait_for_transcription_job(self, job_name, verbose=True):
        transcribe_client = boto3.client('transcribe')
    
        while True:
            try:
                response = transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                transcription_job_status = response['TranscriptionJob']['TranscriptionJobStatus']
                if verbose: 
                    print(f"wait_for_transcription_job: status = {transcription_job_status}")
                if transcription_job_status in ['COMPLETED', 'FAILED']:
                    return response
                # Sleep for polling loop
                # nosemgrep Rule ID: arbitrary-sleep Message: time.sleep() call; did you mean to leave this in?
                time.sleep(4)
            except Exception as e:
                print(f"Error fetching transcription job status: {e}")
                raise

        return response

    # NOTE - sentence tokenization is tricky.  This function does not work for: 
    # - languages that don't follow English-language punctuation style.
    # - sentences that contain abbreviations with a period in them
    # tried several variations of NLTK tokenizers, none were better for English, so went with simplicity for this sample
    def make_sentences(self, transcript):
        """
        Processes the given trascription into sentences. 

        Args: 
           transcript - source transcription to process
        Returns:
           sentences and the corresponding sentence file
        """
        sentences_file = os.path.join(self.video_asset_dir(), 'sentences.json')
        sentences = []

        sentence = {}
        sentence['items'] = []
        sentence['text'] = ""

        for i, item in enumerate(transcript['results']['items']):
            
            if item['type'] == "pronunciation":
                sentence['items'].append(item)
                sentence['text'] = sentence['text'] + ' ' + item['alternatives'][0]['content']
                sentence['end_ms'] = item['end_time']
                if 'start_ms' not in sentence:
                    sentence['start_ms'] = item['start_time']

                last_content = item['alternatives'][0]['content']
            else:
                
                sentence['items'].append(item)
                sentence['text'] = sentence['text'] + item['alternatives'][0]['content']
                punctuation = item['alternatives'][0]['content']

                # Check for end of sentence 
                # not an Acronym with periods
                if (punctuation == '.' and last_content and not last_content.isupper()) \
                    or punctuation in ['?', '!']:
                    # Check for acronyms with periods
                    # Does not handle abbreviations with periods - it will treat them as sentences. 
                    sentences.append(sentence)
                    sentence = {}
                    sentence['items'] = []
                    sentence['text'] = ""
                    last_content = None

        sentences_file = self.download_sentences(sentences, self.video_asset_dir())

        return sentences, sentences_file

    def estimate_transcribe_cost(self, duration_ms):
        transcribe_batch_per_min = 0.02400
    
        transcribe_cost = round(transcribe_batch_per_min * (duration_ms / 60000), 4)
    
    
        return {
            'cost_per_min': transcribe_batch_per_min,
            'duration': round(duration_ms / 1000, 2),
            'estimated_cost': transcribe_cost,
        }

    def display_transcription_cost(self, duration_ms):
        transcribe_cost = estimate_transcribe_cost(duration_ms)
    
        print('\nEstimated cost to Transcribe video:', colored(f"${transcribe_cost['estimated_cost']}", 'green'), f"in us-east-1 region with duration: {transcribe_cost['duration']}s")
        
        return transcribe_cost

    def url_retrieve(self, url: str, outfile: Path):
    
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        with open(outfile,'wb') as f:
          f.write(r.content)

        return r.content

    def download_vtt(self, response, output_dir = ''):

        output_file = os.path.join(output_dir, 'transcript.vtt')
        if os.path.exists(output_file):
            return output_file
    
        subtitle_uri = response['TranscriptionJob']['Subtitles']['SubtitleFileUris'][0]
        self.url_retrieve(subtitle_uri, output_file)
    
        return output_file

    def download_transcript(self, response, output_dir = ''):
    
        output_file = os.path.join(output_dir, 'transcript.json')
        #if os.path.exists(output_file):
         #   with open(output_file, 'r', encoding="utf-8") as f:
         #       transcript = json.loads(f.read())
         #       return transcript
    
        transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript = json.loads(self.url_retrieve(transcript_uri, output_file))

        return transcript, output_file

    def download_sentences(self, sentences, output_dir = ''):
        """
        Saves the given sentences into a file.
        Args:
           sentences - sentences to write to a file
           output_dir - the directory where the sentence file is written to.
        Returns:
            the sentence output file. 
        """

        for file, data in [
            ('sentences.json', sentences)
        ]:
            output_file = os.path.join(output_dir, file)
            util.save_to_file(output_file, data)

        return output_file

    def video_stem(self):
        return Path(self.video_file).stem

    def video_dir(self):
        return Path(self.video_file).parent

    def video_asset_dir(self):
        return os.path.join(self.video_dir(), self.video_stem())

