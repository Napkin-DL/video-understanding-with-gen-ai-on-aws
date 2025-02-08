from lib import frame_utils
from PIL import Image, ImageDraw, ImageFont
import boto3
import time
import os
from functools import cmp_to_key
from lib import util
from lib import frame_utils

class Scenes():
    def __init__(self, frames, shots, min_similarity = 0.80, max_interval = 30):
        self.scenes = []
        self.detect_scenes(frames, shots, min_similarity, max_interval)
        self.video_asset_dir = frames.video_asset_dir()
        

    def detect_scenes(self, frames, shots, min_similarity = 0.80, max_interval = 30):
        """
        Constructs scenes from the given frames and shots.
        This function finds the similar frames within each shot, then group the shots with similar frames
        into a collection of shots. It then perform similar steps to group similar shots 
        together into a scene object. This function writes the scene, frame and shot level details into
        a corresponding JSON file.

        Args:
           frames - video frames
           shots - shots represent a group of similar frames

        Return:
           None
        """
        # find similar shots by comparing to frames in other shots 
        for shot in shots:
            shot['similar_frames'] = frames.collect_similar_frames(shot['start_frame_id'], shot['end_frame_id'], min_similarity, max_interval)
            shot['similar_shots'] = frames.collect_related_shots(shot['similar_frames'])
        
        # group shot into scenes using similar shot information
        grouped_shots = self.group_shots_in_scenes(shots)
        
        # initializethe scene and store scene_id to frames and shots 
        for scene in grouped_shots:
            scene_id = scene['id']
            shot_min, shot_max = scene['shot_ids']
            print(f"Scene #{scene_id}: {shot_min} - {shot_max} ({shot_max - shot_min + 1})")
            # update json files
            for shot_id in range(shot_min, shot_max + 1):
                shots[shot_id]['scene_id'] = scene_id
                for frame_id in range(shots[shot_id]['start_frame_id'], shots[shot_id]['end_frame_id']+1) :
                    frames.frames[frame_id]['scene_id'] = scene_id

            newScene = Scene(scene_id, frames, shots, shot_min, shot_max, shots[shot_min]['start_frame_id'], shots[shot_max]['end_frame_id'])
            sceneDict = newScene.__dict__
            self.scenes.append(sceneDict)

        self.start_frame_id = self.scenes[0]['id']
        self.end_frame_id = self.scenes[-1]['id']
        
        # update the json files
        # save to json file
        for file, data in [
            ('scenes.json', self.scenes),
            ('frames.json', frames.frames),
            ('shots.json', shots)
        ]:
            output_file = os.path.join(frames.video_asset_dir(), file)
            util.save_to_file(output_file, data)
            
        return 
    
    def group_shots_in_scenes(self, shots):
        """
        Creates a collection of scenes that made up of similar shots.
        Args:
           shots - Unique shots within a video
           
        Returns:
           collection of scenes with corresponding shot_ids
        """
        scenes = [
            [
                min(shot['similar_shots']),
                max(shot['similar_shots']),
            ] for shot in shots
        ]
        
        scenes = sorted(scenes, key=cmp_to_key(self.cmp_min_max))
        
        stack = [scenes[0]]
        for i in range(1, len(scenes)):
            prev = stack[-1]
            cur = scenes[i]
            prev_min, prev_max = prev
            cur_min, cur_max = cur
        
            if cur_min >= prev_min and cur_min <= prev_max:
                new_scene = [
                    min(cur_min, prev_min),
                    max(cur_max, prev_max),
                ]
                stack.pop()
                stack.append(new_scene)
                continue
                
            stack.append(cur)
        
        return [{
            'id': i,
            'shot_ids': stack[i],
        } for i in range(len(stack))]
    

    def cmp_min_max(self, a, b):
        if a[0] < b[0]:
            return -1
        if a[0] > b[0]:
            return 1
        return b[1] - a[1]

class Scene():
    def __init__(self, id, frames, shots, shot_min, shot_max, start_frame_id, end_frame_id):
        self.id = id
        self.start_frame_id = start_frame_id
        self.end_frame_id = end_frame_id
        self.start_shot_id = shot_min
        self.end_shot_id = shot_max
        self.start_ms = shots[shot_min]['start_ms']
        self.end_ms = shots[shot_max]['end_ms']
        self.duration_ms = self.end_ms - self.start_ms
        self.video_asset_dir = frames.video_asset_dir()
        self.create_composite_images(frames.frames[start_frame_id:end_frame_id+1])
    
    def create_composite_images(self, frames):
        folder = os.path.join(self.video_asset_dir, 'scenes')
        os.makedirs(folder, exist_ok=True) 
        self.composite_images = frame_utils.create_composite_images(
                frames,
                output_dir = folder,
                prefix = 'scene_',
                max_dimension = (1568, 1568),
                burn_timecode = False
                )
        return