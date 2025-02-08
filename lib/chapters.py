import copy
from lib import frame_utils
import os

class Chapters:
    def __init__(self, conversations, scenes, frames):
        self.video_asset_dir = frames.video_asset_dir()
        self.chapters = self.align_scenes_in_chapters(conversations, scenes, frames)
        
        
        
    def align_scenes_in_chapters(self, conversations, scenes, frames):
        scenes = copy.deepcopy(scenes)
    
        chapters = []
        for conversation in conversations:
            start_ms = conversation['start_ms']
            end_ms = conversation['end_ms']
            text = conversation['reason']

            # find all the frames that align with the conversation topic
            stack = []
            while len(scenes) > 0:
                scene = scenes[0]
                frame_start = scene['start_ms']
                frame_end = scene['end_ms']
    
                if frame_start > end_ms:
                    break
    
                # scenes before any conversation starts
                if frame_end < start_ms:
                    chapter = Chapter(len(chapters), [scene], frames).__dict__
                    chapters.append(chapter)
                    scenes.pop(0)
                    continue
    
                stack.append(scene)
                scenes.pop(0)
    
            if stack:
                chapter = Chapter(len(chapters), stack, frames, text).__dict__
                chapters.append(chapter)
    
        ## There could be more scenes without converations, append them
        for scene in scenes:
            chapter = Chapter(len(chapters), [scene], frames).__dict__
            chapters.append(chapter)
    
        return chapters

class Chapter:
    def __init__(self, chapter_id, scenes, frames, text = ''):
        self.scene_ids = [scene['id'] for scene in scenes]
        self.start_frame_id = scenes[0]['start_frame_id']
        self.end_frame_id = scenes[-1]['end_frame_id']
        self.start_ms = scenes[0]['start_ms']
        self.end_ms = scenes[-1]['end_ms']
        self.id = chapter_id
        self.text = text
        #self.composite_images = self.create_composite_images(frames.frames[self.start_frame_id:self.end_frame_id+1], frames.video_asset_dir())
        self.composite_images = frames.create_composite_images(frames.frames[self.start_frame_id:self.end_frame_id+1], frames.video_asset_dir())
        return 

    def create_composite_images(self, frames, video_asset_dir):
        folder = os.path.join(video_asset_dir, 'chapters')
        os.makedirs(folder, exist_ok=True) 
        composite_images = frame_utils.create_composite_images(
                frames,
                output_dir = folder,
                prefix = 'chapter_',
                max_dimension = (1568, 1568),
                burn_timecode = False
                )
        return composite_images