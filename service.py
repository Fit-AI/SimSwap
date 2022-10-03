import io
import os
import sys
import uuid
import time
import json
import shutil
import logging
logging.basicConfig(level=logging.DEBUG)

import httpx
import socket
import requests
import httpcore
from PIL import Image
from flask import (
        Flask,
        Response,
        request,
        jsonify
        )
import storage3
from supabase import (
        create_client,
        Client
        )
from munch import munchify

import cv2
import torch
import torch.nn.functional as F
from torchvision import transforms
from util.videoswap import video_swap
from models.models import create_model
from insightface_func.face_detect_crop_single import Face_detect_crop

transformer_Arcface = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

def storage_for_bucket(bucket:str):
    client : Client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    return client.storage().get_bucket(bucket)

def upload_to_supabase(storage, key, target):
    assert key
    assert os.path.isfile(target)
    logging.debug(f'Uploading video {target} to {key}')

    MAX_TRIES = 10
    while MAX_TRIES >= 0:
        try:
            storage.upload(key, target, {'content-type': 'video/mp4'})
            return storage.create_signed_url(key, sys.maxsize)['signedURL']
        except storage3.utils.StorageException as e:
            code = e.args[0]['statusCode']
            message = e.args[0]['message']
            if code == 400 and message.find('duplicate key value') != -1:
                return storage.create_signed_url(key, sys.maxsize)['signedURL']
            else:
                logging.error(f'Uploading {target} -> {key} failed: [{e}]')
                continue
        except socket.timeout as e:
            logging.error(f'Timed out! {e}')
            MAX_TRIES -= 1
            time.sleep(1)
            continue
        except httpx.ReadTimeout as e:
            logging.error(f'Supabase timed out uploading! {e}')
            MAX_TRIES -= 1
            time.sleep(1)
            continue
        except httpcore.ReadTimeout as e:
            logging.error(f'Other timed out?? {e}')
            MAX_TRIES -= 1
            time.sleep(1)
            continue

class Swapper(object):

    INPUT_IMAGE = 'inputs/input_image.jpg'
    INPUT_VIDEO = 'inputs/input_video.mp4'
    TEMP_PATH = 'temp/input_video.mp4'

    def __init__(self):
        with open('default_configuration.json') as handle:
            opt = munchify(json.load(handle))
        opt.pic_a_path = Swapper.INPUT_IMAGE
        opt.video_path = Swapper.INPUT_VIDEO
        opt.temp_path = Swapper.TEMP_PATH
        self.opt = opt

        start_epoch, epoch_iter = 1, 0
        self.crop_size = self.opt.crop_size
        torch.nn.Module.dump_patches = True
        if self.crop_size == 512:
            self.opt.which_epoch = 550000
            self.opt.name = '512'
            mode = 'ffhq'
        else:
            mode = 'None'

        # Create sim-swap
        self.model = create_model(self.opt)
        self.model.eval()
        # Create face-detection
        self.app = Face_detect_crop(name='antelope', root='./insightface_func/models')
        self.app.prepare(ctx_id= 0, det_thresh=0.6, det_size=(640,640),mode=mode)

    def simswap(self)-> dict:
        assert os.path.isfile(Swapper.INPUT_IMAGE)
        assert os.path.isfile(Swapper.INPUT_VIDEO)
        shutil.rmtree('temp', ignore_errors=True)
        os.makedirs('temp')
        shutil.rmtree('outputs', ignore_errors=True)
        os.makedirs('outputs')

        with torch.no_grad():
            pic_a = Swapper.INPUT_IMAGE
            assert os.path.isfile(pic_a)
            img_a = Image.open(pic_a).convert('RGB')
            img_a_whole = cv2.imread(pic_a)
            img_a_align_crop, _ = self.app.get(img_a_whole, self.crop_size)
            img_a_align_crop_pil = Image.fromarray(cv2.cvtColor(img_a_align_crop[0], cv2.COLOR_BGR2RGB))
            img_a = transformer_Arcface(img_a_align_crop_pil)
            img_id = img_a.view(-1, img_a.shape[0], img_a.shape[1], img_a.shape[2])
            img_id = img_id.cuda()
            # Latent ID
            img_id_downsample = F.interpolate(img_id, size=(112,112))
            latend_id = self.model.netArc(img_id_downsample)
            latend_id = F.normalize(latend_id, p=2, dim=1)
            # Swap
            video_swap(self.opt.video_path,
                       latend_id,
                       self.model,
                       self.app,
                       self.opt.output_path,
                       temp_results_dir=self.opt.temp_path,
                       no_simswaplogo=self.opt.no_simswaplogo,
                       use_mask=self.opt.use_mask,
                       crop_size=self.crop_size)

            storage = storage_for_bucket('dev-simswap')
            key = str(uuid.uuid4())
            result_url = upload_to_supabase(storage,
                                            key,
                                            'results/result.mp4')
            return {'result': result_url}

def download_video(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def download_image(url):
    return Image.open(io.BytesIO(requests.get(url).content))

swapper = Swapper()

app = Flask('simswap-api')

@app.route('/livez', methods=['GET', 'POST'])
def livez():
    return Response("{}", status=200)

@app.route('/simswap', methods=['GET', 'POST'])
def simswap():
    content_type = request.headers.get('Content-Type')
    video_url = request.json['video']
    target_url = request.json['image']
    logging.info(f'Running simswap {target_url} on {video_url}')
    shutil.rmtree('inputs', ignore_errors=True)
    os.makedirs('inputs')
    shutil.rmtree('results', ignore_errors=True)
    os.makedirs('results')
    download_video(video_url, Swapper.INPUT_VIDEO)
    download_image(target_url).save(Swapper.INPUT_IMAGE)
    return jsonify(swapper.simswap())
