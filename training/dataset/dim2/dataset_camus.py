import os
import torch
import numpy as np
from torch.utils.data import Dataset
import SimpleITK as sitk
import yaml
import random
from tqdm import tqdm

# from training import augmentation


class CAMUSDataset(Dataset):
    def __init__(self, args, mode="train", k_fold=5, k=0, seed=0):

        self.mode = mode
        self.args = args

        assert mode in ["train", "test"]

        with open(os.path.join(args['data_root'], "list", "dataset.yaml"), "r") as f:
            img_name_list = yaml.load(f, Loader=yaml.SafeLoader)

        random.Random(seed).shuffle(img_name_list)

        length = len(img_name_list)
        print(f"The len of the patient list is {length}")
        test_name_list = img_name_list[:10]
        train_name_list = list(set(img_name_list) - set(test_name_list))

        self.train_length = len(train_name_list)
        print(f"The len of the training list is {self.train_length}")

        if mode == "train":
            img_name_list = train_name_list
        else:
            img_name_list = test_name_list

        print("start loading %s data" % self.mode)

        path = args['data_root']

        img_list = []
        lab_list = []
        spacing_list = []
        idx = ["_2CH_ED.mhd", "_2CH_ES.mhd", "_4CH_ED.mhd", "_4CH_ES.mhd"]

        for name in tqdm(img_name_list):
            for id in idx:

                img_name = name + id
                lab_name = name + id.replace(".", "_gt.")
                itk_img = sitk.ReadImage(os.path.join(path, img_name))
                itk_lab = sitk.ReadImage(os.path.join(path, lab_name))
                spacing = np.array(itk_lab.GetSpacing()).tolist()
                spacing_list.append(spacing[::-1])

                assert itk_img.GetSize() == itk_lab.GetSize()

                img, lab = self.preprocess(itk_img, itk_lab)

                img_list.append(img)
                lab_list.append(lab)

        self.img_slice_list = []
        self.lab_slice_list = []
        if self.mode == "train":
            for i in range(len(img_list)):
                tmp_img = img_list[i]
                tmp_lab = lab_list[i]

                z, x, y = tmp_img.shape

                for j in range(z):
                    self.img_slice_list.append(tmp_img[j])
                    self.lab_slice_list.append(tmp_lab[j])

        else:
            self.img_slice_list = img_list
            self.lab_slice_list = lab_list
            self.spacing_list = spacing_list

        print("load done, length of dataset:", len(self.img_slice_list))

    def __len__(self):
        return len(self.img_slice_list)

    def shape(self):
        print(f"shape: {self.img_slice_list[0].shape}")
        print(f"shape: {self.img_slice_list[1].shape}")

    def preprocess(self, itk_img, itk_lab):

        img = sitk.GetArrayFromImage(itk_img)
        lab = sitk.GetArrayFromImage(itk_lab)

        max98 = np.percentile(img, 98)
        img = np.clip(img, 0, max98)

        z, y, x = img.shape
        if x < self.args['training_size'][0]:
            diff = (self.args['training_size'][0] + 10 - x) // 2
            img = np.pad(img, ((0, 0), (0, 0), (diff, diff)))
            lab = np.pad(lab, ((0, 0), (0, 0), (diff, diff)))
        if y < self.args['training_size'][1]:
            diff = (self.args['training_size'][1] + 10 - y) // 2
            img = np.pad(img, ((0, 0), (diff, diff), (0, 0)))
            lab = np.pad(lab, ((0, 0), (diff, diff), (0, 0)))

        img = img[:, :256, :256]
        lab = lab[:, :256, :256]

        img = img / max98

        img = img.astype(np.float32)
        lab = lab.astype(np.uint8)

        tensor_img = torch.from_numpy(img).float()
        tensor_lab = torch.from_numpy(lab).long()

        return tensor_img, tensor_lab

    def __getitem__(self, idx):
        tensor_img = self.img_slice_list[idx]
        tensor_lab = self.lab_slice_list[idx]
        # return (tensor_img,tensor_lab)

        if self.mode == "train":
            tensor_img = tensor_img.unsqueeze(0).unsqueeze(0)
            tensor_lab = tensor_lab.unsqueeze(0).unsqueeze(0)
            tensor_img, tensor_lab = tensor_img.squeeze(0), tensor_lab.squeeze(0)
        else:
            tensor_img, tensor_lab = self.center_crop(tensor_img, tensor_lab)

        assert tensor_img.shape == tensor_lab.shape

        if self.mode == "train":
            return tensor_img, tensor_lab
        else:
            return tensor_img, tensor_lab, np.array(self.spacing_list[idx])

    def center_crop(self, img, label):
        D, H, W = img.shape

        diff_H = H - self.args['training_size'][0]
        diff_W = W - self.args['training_size'][1]

        rand_x = diff_H // 2
        rand_y = diff_W // 2

        croped_img = img[
            :,
            rand_x : rand_x + self.args['training_size'][0],
            rand_y : rand_y + self.args['training_size'][0],
        ]
        croped_lab = label[
            :,
            rand_x : rand_x + self.args['training_size'][1],
            rand_y : rand_y + self.args['training_size'][1],
        ]

        return croped_img, croped_lab
