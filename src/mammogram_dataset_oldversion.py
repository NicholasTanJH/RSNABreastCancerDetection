import pandas as pd
from PIL import Image
import torch
import torchvision
from torchvision import transforms
from torch.utils.data.dataset import Dataset
import numpy as np
import io

# # Google cloud
# # *********************
# import sys
# sys.path.append('/opt/miniconda3/lib/python3.12/site-packages')
# from google.cloud import storage

# # # from IPython.display import Image
# # from io import BytesIO
# # from PIL import Image

# import os
# os.environ["GCLOUD_PROJECT"] = "dataming_processed_data"

# client = storage.Client()
# # https://console.cloud.google.com/storage/browser/[bucket-id]/
# bucket = client.get_bucket('dataming_processed_data')
# # # Then do other things...
# # # blob = bucket.get_blob('1000049233.png')
# # # blob.content_type = 'image/png' # This one is the important

# # # img = Image.open(BytesIO(blob.download_as_bytes()))

# #**********************

# site_id,patient_id,image_id,laterality,view,age,cancer,biopsy,invasive,BIRADS,implant,density,machine_id,difficult_negative_case
# site_id,patient_id,image_id,laterality,view,age,implant,machine_id,prediction_id

class MammogramDataset(Dataset):
    # individual = True if you want to get the individual images
    # get_cancer = True if you want to get the cancer value vs difficult case value
    def __init__(self, csv_path:str, data_path:str='processed_data/', transform=None, individual=False, get_cancer=True, tile=False, return_meta=False):
        tile = True # make tile always true so we can use pretrained
        self.transform = transform
        self.df = pd.read_csv(csv_path)
        self.data_len = len(self.df)
        self.data_path = data_path
        self.individual = individual
        self.get_cancer = get_cancer
        self.tile = tile
        self.return_meta = return_meta
        if not individual:
            self.data_len = self.df['patient_id'].nunique()
            self.patient_list = self.df['patient_id'].unique()

    def get_bias(self):
        bias = self.df['cancer'].mean()
        return float(bias/(1-bias))
    
    def get_weights(self):
        bias = self.df['cancer'].mean()
        return float(1/(1-bias)), float(1/bias)

    def _get_meta(self, meta, row):
        exclude_cols = ['patient_id', 'image_id', 'cancer', 'biopsy', 'invasive', 'difficult_negative_case', 'BIRADS', 'density', 'implant']
        if self.return_meta:
            X = row.drop(exclude_cols).astype(float)
            meta.append(torch.tensor(X.values, dtype=torch.float32))
        return None

    def __getitem__(self, index):
        if torch.is_tensor(index):
            index = index.tolist()
        imgs = None
        target_name = 'cancer'
        meta = []
        if self.individual:
            patient_id, image_id, target = self.df.loc[index, ['patient_id', 'image_id', target_name]]
            if not self.get_cancer:
                target = max(target, int(self.df.loc[index, 'difficult_negative_case']))
                
            # image_location = str(self.data_path) + "/" + str(int(patient_id)) + "_" + str(int(image_id)) + ".png"
            image_location = str(int(image_id)) + ".png"
            
            # Google cloud
            blob = bucket.get_blob(image_location)
            blob.content_type = 'image/png' # This one is the important
            print(blob) 
            # img = Image.open(BytesIO(blob.download_as_bytes()))
            img = Image.open(io.BytesIO(blob.download_as_bytes()))
                
            # imgs = Image.open(image_location)
            if self.transform:
                imgs =  self.transform(image=np.array(imgs))
                imgs = imgs['image']
                if self.tile:
                    imgs = torch.cat((imgs, imgs, imgs), dim=0)
                    imgs = imgs.expand(3, -1, -1)
            self._get_meta(meta, self.df.loc[index])
            if self.return_meta:
                meta = meta[0]
        else:
            selected_patient = self.patient_list[index]
            relevant_rows = self.df.loc[self.df['patient_id'] == selected_patient]
            imgs = []
            for row in relevant_rows.iterrows():
                image_id = int(row.iloc['image_id'])
                target = row.iloc[target_name]
                if not self.get_cancer:
                    target = max(target, int(row.iloc[index, 'difficult_negative_case']))
                # img = Image.open(self.data_path + "/" + selected_patient  + "_" + image_id + ".png")
                
                # Google cloud
                blob = bucket.get_blob(image_id + ".png")
                blob.content_type = 'image/png' # This one is the important
                # img = Image.open(BytesIO(blob.download_as_bytes()))
                img = Image.open(io.BytesIO(blob.download_as_bytes()))
                
                if self.transform:
                    img = self.transform(image=np.array(img))
                    img = img['image']
                    if self.tile:
                        img = torch.cat((img, img, img), dim=0)
                        img = img.expand(3, -1, -1)
                    imgs.append(img)
                self._get_meta(meta, row)
        if self.return_meta:
            return imgs, int(target), meta
        return imgs, int(target)
    
    # def __getitem__(self, index):
    #     # all_blobs = {}
    #     # client = storage.Client.from_service_account_json(
    #     #     '/Users/nicholastan/RSNACancerDetection-main/src/generated-mote-428217-s3-8230d2d4d100.json')
        

    #     bucket_name = "dataming_processed_data"

    #     bucket = client.bucket(bucket_name=bucket_name)

    #     blobs = bucket.list_blobs()

    #     # for blob in blobs:
    #     #     all_blobs[blob.name] = blob

    #     if torch.is_tensor(index):
    #         index = index.tolist()
    #     imgs = None
    #     target_name = 'cancer'
    #     meta = []
    #     if self.individual:
    #         patient_id, image_id, target = self.df.loc[index, ['patient_id', 'image_id', target_name]]
    #         if not self.get_cancer:
    #             target = max(target, int(self.df.loc[index, 'difficult_negative_case']))

    #         # using the blobs
    #         image_nm = str(int(image_id)) + ".png"
    #         # image_blob = all_blobs[image_nm]
    #         image_blob = bucket.blob(image_nm)
    #         image_data = image_blob.download_as_bytes()
    #         imgs = Image.open(io.BytesIO(image_data))

    #         # image_location = str(self.data_path) + "/" + str(int(image_id)) + ".png"
    #         # imgs = Image.open(image_location)
    #         if self.transform:
    #             imgs = self.transform(image=np.array(imgs))
    #             imgs = imgs['image']
    #             if self.tile:
    #                 imgs = torch.cat((imgs, imgs, imgs), dim=0)
    #                 imgs = imgs.expand(3, -1, -1)
    #         self._get_meta(meta, self.df.loc[index])
    #         if self.return_meta:
    #             meta = meta[0]
    #     else:
    #         selected_patient = self.patient_list[index]
    #         relevant_rows = self.df.loc[self.df['patient_id'] == selected_patient]
    #         imgs = []
    #         for row in relevant_rows.iterrows():
    #             image_id = int(row.iloc['image_id'])
    #             target = row.iloc[target_name]
    #             if not self.get_cancer:
    #                 target = max(target, int(row.iloc[index, 'difficult_negative_case']))
    #             img = Image.open(self.data_path + "/" + selected_patient + "_" + image_id + ".png")
    #             if self.transform:
    #                 img = self.transform(image=np.array(img))
    #                 img = img['image']
    #                 if self.tile:
    #                     img = torch.cat((img, img, img), dim=0)
    #                     img = img.expand(3, -1, -1)
    #                 imgs.append(img)
    #             self._get_meta(meta, row)
    #     if self.return_meta:
    #         return imgs, int(target), meta
    #     return imgs, int(target)
    

    def __len__(self):
        return self.data_len