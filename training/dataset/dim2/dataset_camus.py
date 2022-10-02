import os
import torch
import numpy as np
from torch.utils.data import Dataset
import SimpleITK as sitk
import yaml
import random
from tqdm import tqdm
from training import augmentation


class CAMUSDataset(Dataset):
    def __init__(self, args, mode="train", seed=0, augmentation=False, only_quality=True):

        assert mode in ["train", "test"]
        self.mode = mode
        self.augmentation = augmentation
        self.only_quality = only_quality
        self.args = args
        self.img_slice_list_train = []
        self.lab_slice_list_train = []
        self.img_slice_list_test = []
        self.lab_slice_list_test = []

        with open(os.path.join(args["data_root"], "list", "dataset.yaml"), "r") as f:
            img_name_list = yaml.load(f, Loader=yaml.SafeLoader)

        random.Random(seed).shuffle(img_name_list)

        quality_patients_2CH = []
        quality_patients_4CH = []
        if only_quality:
            for patient in img_name_list:
                with open(os.path.join(args["data_info"], patient, "Info_2CH.cfg")) as info2:
                    i2 = yaml.safe_load(info2)
                    if i2['ImageQuality'] == 'Good' or i2['ImageQuality'] == 'Medium':
                        quality_patients_2CH.append(patient)
                with open(os.path.join(args["data_info"], patient, "Info_4CH.cfg")) as info4:
                    i4 = yaml.safe_load(info4)
                    if i4['ImageQuality'] == 'Good' or i4['ImageQuality'] == 'Medium':
                        quality_patients_4CH.append(patient)

        length = len(img_name_list)
        print(f"The length of the patient list is {length}")
        if only_quality:
            print(f"It will include {len(quality_patients_2CH)*2 + len(quality_patients_4CH)*2} good quality samples")
        else:
            print(f"It will include {length * 4} samples")
        test_name_list = img_name_list[: args["test_size"]]
        train_name_list = list(set(img_name_list) - set(test_name_list))
        print("start loading data")

        path = args["data_root"]

        img_list_train = []
        lab_list_train = []
        spacing_list_train = []
        idx = ["_2CH_ED.mhd", "_2CH_ES.mhd", "_4CH_ED.mhd", "_4CH_ES.mhd"]

        # Load training
        for name in tqdm(train_name_list):
            selected_images = []
            if only_quality:
                if name in quality_patients_2CH:
                    selected_images += idx[:2]
                if name in quality_patients_4CH:
                    selected_images += idx[2:]
            else:
                selected_images = idx

            for id in selected_images:

                img_name = name + id
                lab_name = name + id.replace(".", "_gt.")
                itk_img = sitk.ReadImage(os.path.join(path, img_name))
                itk_lab = sitk.ReadImage(os.path.join(path, lab_name))
                spacing = np.array(itk_lab.GetSpacing()).tolist()
                spacing_list_train.append(spacing[::-1])

                assert itk_img.GetSize() == itk_lab.GetSize()

                img, lab = self.preprocess(itk_img, itk_lab)

                img_list_train.append(img)
                lab_list_train.append(lab)

        for i in range(len(img_list_train)):
            tmp_img = img_list_train[i]
            tmp_lab = lab_list_train[i]

            z, x, y = tmp_img.shape

            for j in range(z):
                self.img_slice_list_train.append(tmp_img[j])
                self.lab_slice_list_train.append(tmp_lab[j])
        print("Train done, length of dataset:", len(self.img_slice_list_train))

        img_list_test = []
        lab_list_test = []
        spacing_list_test = []

        # Load tests
        for name in tqdm(test_name_list):
            selected_images = []
            if only_quality:
                if name in quality_patients_2CH:
                    selected_images += idx[:2]
                if name in quality_patients_4CH:
                    selected_images += idx[2:]
            else:
                selected_images = idx

            for id in selected_images:
                img_name = name + id
                lab_name = name + id.replace(".", "_gt.")
                itk_img = sitk.ReadImage(os.path.join(path, img_name))
                itk_lab = sitk.ReadImage(os.path.join(path, lab_name))
                spacing = np.array(itk_lab.GetSpacing()).tolist()
                spacing_list_test.append(spacing[::-1])

                assert itk_img.GetSize() == itk_lab.GetSize()

                img, lab = self.preprocess(itk_img, itk_lab)

                img_list_test.append(img)
                lab_list_test.append(lab)

        for i in range(len(img_list_test)):
            tmp_img = img_list_test[i]
            tmp_lab = lab_list_test[i]

            z, x, y = tmp_img.shape

            for j in range(z):
                self.img_slice_list_test.append(tmp_img[j])
                self.lab_slice_list_test.append(tmp_lab[j])
        print("Test done, length of dataset:", len(self.img_slice_list_test))
        print(
            "load done, length of dataset:",
            len(self.img_slice_list_test) + len(self.img_slice_list_train),
        )

    def __len__(self):
        if self.mode == "train":
            return len(self.img_slice_list_train)
        else:
            return len(self.img_slice_list_test)

    def preprocess(self, itk_img, itk_lab):

        img = sitk.GetArrayFromImage(itk_img)
        lab = sitk.GetArrayFromImage(itk_lab)

        max98 = np.percentile(img, 98)
        img = np.clip(img, 0, max98)

        z, y, x = img.shape

        if x < self.args["training_size"][0]:
            diff = int(np.ceil((self.args["training_size"][0] - x) / 2))
            img = np.pad(img, ((0, 0), (0, 0), (diff, diff)))
            lab = np.pad(lab, ((0, 0), (0, 0), (diff, diff)))
        if y < self.args["training_size"][1]:
            diff = int(np.ceil((self.args["training_size"][1] - y) / 2))
            img = np.pad(img, ((0, 0), (diff, diff), (0, 0)))
            lab = np.pad(lab, ((0, 0), (diff, diff), (0, 0)))

        # if x < self.args["training_size"][0]:
        #     diff = (self.args["training_size"][0] + 10 - x) // 2
        #     img = np.pad(img, ((0, 0), (0, 0), (diff, diff)))
        #     lab = np.pad(lab, ((0, 0), (0, 0), (diff, diff)))
        # if y < self.args["training_size"][1]:
        #     diff = (self.args["training_size"][1] + 10 - y) // 2
        #     img = np.pad(img, ((0, 0), (diff, diff), (0, 0)))
        #     lab = np.pad(lab, ((0, 0), (diff, diff), (0, 0)))

        img = img[:, :256, :256]
        lab = lab[:, :256, :256]

        img = img / max98

        # img = img.astype(np.float32)
        # lab = lab.astype(np.uint8)

        tensor_img = torch.from_numpy(img).float()
        tensor_lab = torch.from_numpy(lab).long()

        return tensor_img, tensor_lab

    def __getitem__(self, idx):
        if self.mode == "train":
            tensor_img = self.img_slice_list_train[idx]
            tensor_lab = self.lab_slice_list_train[idx]
            tensor_img = tensor_img.unsqueeze(0).unsqueeze(0)
            tensor_lab = tensor_lab.unsqueeze(0).unsqueeze(0)

            if self.augmentation == True:
                # Gaussian Noise
                tensor_img = augmentation.gaussian_noise(
                    tensor_img, std=self.args.gaussian_noise_std
                )
                # Additive brightness
                tensor_img = augmentation.brightness_additive(
                    tensor_img, std=self.args.additive_brightness_std
                )
                # gamma
                tensor_img = augmentation.gamma(
                    tensor_img, gamma_range=self.args.gamma_range, retain_stats=True
                )

                tensor_img, tensor_lab = augmentation.random_scale_rotate_translate_2d(
                    tensor_img,
                    tensor_lab,
                    self.args.scale,
                    self.args.rotate,
                    self.args.translate,
                )
                tensor_img, tensor_lab = augmentation.crop_2d(
                    tensor_img, tensor_lab, self.args.training_size, mode="random"
                )

                tensor_img, tensor_lab = tensor_img.squeeze(0), tensor_lab.squeeze(0)

        else:
            tensor_img = self.img_slice_list_test[idx]
            tensor_lab = self.lab_slice_list_test[idx]
            tensor_img = tensor_img.unsqueeze(0).unsqueeze(0)
            tensor_lab = tensor_lab.unsqueeze(0).unsqueeze(0)
            tensor_img, tensor_lab = tensor_img.squeeze(0), tensor_lab.squeeze(0)
        assert tensor_img.shape == tensor_lab.shape

        return tensor_img, tensor_lab

    def test(self):
        self.mode = 'test'

    def train(self):
        self.mode = 'train'

    def center_crop(self, img, label):
        D, H, W = img.shape

        diff_H = H - self.args["training_size"][0]
        diff_W = W - self.args["training_size"][1]

        rand_x = diff_H // 2
        rand_y = diff_W // 2

        croped_img = img[
            :,
            rand_x : rand_x + self.args["training_size"][0],
            rand_y : rand_y + self.args["training_size"][0],
        ]
        croped_lab = label[
            :,
            rand_x : rand_x + self.args["training_size"][1],
            rand_y : rand_y + self.args["training_size"][1],
        ]

        return croped_img, croped_lab
