# -*- coding: utf-8 -*-
"""our_model_revise.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ninlgsAoc9jBn2J3OUjmTw3dxYEXKYvr
"""

# mount drive https://datascience.stackexchange.com/questions/29480/uploading-images-folder-from-my-system-into-google-colab
# login with your google account and type authorization code to mount on your google drive.
import os

# 학습 코드
import numpy as np
import json
import PIL
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torchvision import transforms, utils
from skimage import io, transform
import matplotlib.pyplot as plt
import time
import os
import copy
import random
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from efficientnet_pytorch import EfficientNet

device = 'cuda' if torch.cuda.is_available() else 'cpu'


class Mydataset(Dataset):
    def __init__(self, csvfile, root_dir, transform=None):
        self.landmarks_frame = pd.read_csv(csvfile)
        self.root_dir = root_dir
        self.transform = transform
        self.diagnose_dict = {"melanoma": 0, "nevus": 1}

    def __len__(self):
        return len(self.landmarks_frame)

    def one_hot_sex(self, sex):
        if sex == "male":
            return [1, 0]
        else:
            return [0, 1]

    def one_hot_age(self, age):
        arr = [0] * 10
        arr[int(age/10)] = 1
        return arr

    def one_hot_site(self, site):
        if site == "head/neck":
            return [1, 0, 0, 0, 0, 0]
        elif site == "upper extremity":
            return [0, 1, 0, 0, 0, 0]
        elif site == "lower extremity":
            return [0, 0, 1, 0, 0, 0]
        elif site == "torso":
            return [0, 0, 0, 1, 0, 0]
        elif site == "palms/soles":
            return [0, 0, 0, 0, 1, 0]
        elif site == "oral/genital":
            return [0, 0, 0, 0, 0, 1]
        else:
            assert(0)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        img_name = os.path.join(
            self.root_dir, self.landmarks_frame.iloc[idx, 0])
        image = io.imread(img_name+".jpg")
        image = transforms.ToTensor()(image)
        if self.transform:
            image = self.transform(image)

        # sample = image
        try:
            diagnose = self.diagnose_dict[self.landmarks_frame.iloc[idx, 5]]
        except:
            diagnose = 1

        sex = self.landmarks_frame.iloc[idx, 2]
        sex = self.one_hot_sex(sex)

        age = self.landmarks_frame.iloc[idx, 3]
        age = self.one_hot_age(age)

        site = self.landmarks_frame.iloc[idx, 4]
        site = self.one_hot_site(site)

        metadata = np.array(sex + age + site).astype(np.float32)
        metadata = torch.from_numpy(metadata)

        image = image.to(device)
        metadata = metadata.to(device)
        diagnose = torch.tensor(diagnose, dtype=torch.long)
        diagnose = diagnose.to(device)

        # landmarks = landmarks.astype('float').reshape(-1, 2)
        sample = {'image': image, 'metadata': metadata, 'diagnose': diagnose}
        # sample = np.array([image, image])

        return sample


class MyNetwork(nn.Module):
    def __init__(self):
        super(MyNetwork, self).__init__()
        cnn_model_name = 'efficientnet-b1'
        self.cnn_model = EfficientNet.from_pretrained(
            cnn_model_name, num_classes=2).to(device)
        print(EfficientNet.get_image_size(cnn_model_name))
        self.cnn = nn.Sequential(
            nn.Linear(1280, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),
        )

        self.meta = nn.Sequential(
            nn.Linear(18, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(128, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(128, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),
        )

        self.post = nn.Sequential(
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(128, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(p=0.3),
            nn.Linear(32, 2),
        )

        ################################

    def forward(self, image, metadata):
        image = self.cnn_model.extract_features(image)
        image = nn.AdaptiveAvgPool2d(output_size=(1, 1))(image)
        image = torch.squeeze(image, -1)
        image = torch.squeeze(image, -1)
        img_out = self.cnn(image)
        meta_out = self.meta(metadata)
        output = self.post(torch.cat((img_out, meta_out), dim=1))
        #######################################################################
        return output
