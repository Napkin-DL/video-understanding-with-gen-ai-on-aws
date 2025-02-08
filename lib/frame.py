import os
import time
import json
import glob
import subprocess
import shlex
import cv2
from PIL import Image, ImageDraw, ImageFont
import imagehash
import numpy as np
from matplotlib import pyplot as plt 
from pathlib import Path
from urllib.parse import urlparse
from lib import util
from lib import image_utils
import re
import boto3
import faiss
from functools import cmp_to_key
import numpy as np
from numpy import dot
from numpy.linalg import norm

TITAN_MODEL_ID = 'amazon.titan-embed-image-v1'
TITAN_PRICING = 0.00006

config = {
   "LAPLACIAN_PATH": "laplacian",
   "LAPLACIAN_SIZE": 18,
   "LAPLACIAN_DISTANCE": 0.2,
   "PHASH_THRESHOLD": 0.2,
   "PHASH_SIZE": 18,
   "PHASH_DISTANCE": 4
}

class Frame:
    def __init__(self, id, image_file, timestamp_millis):
        self.id = id
        self.image_file = image_file
        self.timestamp_millis = int(timestamp_millis)
        self.laplacian_variance = self.compute_laplacian_variance(ksize=3)
        self.perceptual_hash = self.compute_phash()
        self.make_laplacian_image(self.image_file, ksize=21)
        self.make_titan_multimodal_embedding()

    def compute_laplacian_variance(self, ksize=3):
        """
        Computes laplacian variant for the given image.
        Args: 
             ksize: Aperture size used to compute the second-derivative filters. see (https://docs.opencv.org/3.4/d4/d86/group__imgproc__filter.html#gad78703e4c8fe703d479c1860d76429e6)

        Returns:
             laplacian variant.
        """
        
        image = cv2.imread(self.image_file, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variant = cv2.Laplacian(gray, cv2.CV_64F, ksize).var()

        return round(variant)
    
    def compute_phash(self):
        """
        Compute the perceptual hash for the image file for this object.
        For more information please refer to: https://en.wikipedia.org/wiki/Perceptual_hashing

        """
        with Image.open(self.image_file) as image:
            # imagehash.hex_to_hash(phash)
            phash = str(imagehash.phash(image))
            return phash

        return None

    def make_titan_multimodal_embedding(self):
        """
        Creates an image embedding. This function uses titan multimodal embedding model to create an embedding for the image frame.
        
        Args:
           None
        
        """

        titan_model_id = TITAN_MODEL_ID
        accept = 'application/json'
        content_type = 'application/json'

        bedrock_runtime_client = boto3.client(service_name='bedrock-runtime')

        with Image.open(self.image_file) as image:
            input_image = image_utils.image_to_base64(image)

        model_params = {
            'inputImage': input_image,
            'embeddingConfig': {
                'outputEmbeddingLength': 384 #1024 #384 #256
            }
        }

        body = json.dumps(model_params)

        response = bedrock_runtime_client.invoke_model(
            body=body,
            modelId=titan_model_id,
            accept=accept,
            contentType=content_type
        )
        response_body = json.loads(response.get('body').read())

        self.titan_multimodal_embedding = response_body['embedding']
        self.titan_multimodal_embedding_model_id = titan_model_id
        self.titan_multimodal_embedding_cost = 0.00006

        return

    def make_laplacian_image(self, image_file, ksize=3):
        """
        Creates an laplacian image from the given image file.
        Args:
           image_file: input image
           ksize: Aperture size used to compute the second-derivative filters. See (https://docs.opencv.org/3.4/d4/d86/group__imgproc__filter.html#gad78703e4c8fe703d479c1860d76429e6) for more detail.
        """

        image = cv2.imread(image_file, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variant = cv2.Laplacian(gray, cv2.CV_64F, ksize).var()

        image = cv2.imread(image_file, cv2.IMREAD_COLOR)
        lap_1 = cv2.Laplacian(image, cv2.CV_64F, ksize)
        lap_1_abs = np.uint(np.absolute(lap_1)) 

        # save the laplacian image to the folder for visualization
        image_path = Path(image_file).parent
        util.mkdir(os.path.join(image_path.parent, config["LAPLACIAN_PATH"]))
        laplacian_file = os.path.join(image_path.parent, config["LAPLACIAN_PATH"], os.path.basename(image_file))
        cv2.imwrite(laplacian_file, lap_1_abs)
        self.laplacian_file = laplacian_file

        return

    def display_laplacian(self, ksize=3):
        image = cv2.imread(self.image_file, cv2.IMREAD_COLOR)
        lap_1 = cv2.Laplacian(image, cv2.CV_64F, ksize)
        lap_1_abs = np.uint(np.absolute(lap_1)) 

        titles = ['Original Image', f"Laplacian derivative with ksize={ksize}"]
        images = [image, lap_1_abs]
        plt.figure(figsize=(13,5))
        for i in range(2):
            plt.subplot(1,3, i+1)
            plt.imshow((images[i]).astype(np.uint8), 'gray')
            plt.title(titles[i])
            plt.xticks([])
            plt.yticks([])
        plt.tight_layout()
        plt.show()
        return
