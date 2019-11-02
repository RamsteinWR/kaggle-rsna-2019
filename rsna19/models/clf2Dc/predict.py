import json

import albumentations
import cv2
import numpy as np
import os
import pandas as pd
import torch
torch.multiprocessing.set_sharing_strategy('file_system')
from torch.nn import functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from rsna19.data.dataset_2dc import IntracranialDataset
from rsna19.models.clf2Dc.classifier2dc import Classifier2DC

TTA_TRANSFORMS = {
    None: None,
    'hflip': [albumentations.HorizontalFlip(True)],
    'vflip': [albumentations.VerticalFlip(True)],
    'lrotate': [albumentations.Rotate((-30, -30), interpolation=cv2.INTER_LINEAR, border_mode=cv2.BORDER_CONSTANT,
                                      value=0, always_apply=True)],
    'rrotate': [albumentations.Rotate((-30, -30), interpolation=cv2.INTER_LINEAR, border_mode=cv2.BORDER_CONSTANT,
                                      value=0, always_apply=True)]
}


def predict(checkpoint_path, device, subset, tta_variant=None):
    assert subset in ['train', 'val', 'test']
    assert tta_variant in TTA_TRANSFORMS

    train_dir = os.path.join(os.path.dirname(checkpoint_path), '..')
    config_path = os.path.join(train_dir, 'version_0/config.json')

    checkpoint_name = os.path.basename(checkpoint_path).split('.')[0]
    if tta_variant is None:
        df_out_path = os.path.join(train_dir, f'results/{checkpoint_name}_{subset}.csv')
    else:
        df_out_path = os.path.join(train_dir, f'results/{checkpoint_name}_{subset}_{tta_variant}.csv')
    os.makedirs(os.path.dirname(df_out_path), exist_ok=True)

    with open(config_path, 'r') as f:
        config_dict = json.load(f)
        if 'dropout' not in config_dict:
            config_dict['dropout'] = 0
        config = type('config', (), config_dict)

    with torch.cuda.device(device):
        checkpoint = torch.load(checkpoint_path, map_location=torch.device(device))

        model = Classifier2DC(config)
        model.load_state_dict(checkpoint['state_dict'])
        model.on_load_checkpoint(checkpoint)
        model.cuda()

        model.eval()
        model.freeze()

        if subset == 'train':
            folds = config.train_folds
        elif subset == 'val':
            folds = config.val_folds
        else:
            folds = None

        mode = 'test' if subset == 'test' else 'train'
        dataset = IntracranialDataset(config, folds, mode=mode, augment=False,
                                      transforms=TTA_TRANSFORMS[tta_variant])

        all_paths = []
        all_study_id = []
        all_slice_num = []
        all_gt = []
        all_pred = []

        batch_size = 128
        data_loader = DataLoader(dataset, batch_size=batch_size, num_workers=4)
        for bix, batch in tqdm(enumerate(data_loader), total=len(dataset) // batch_size):
            y_hat = F.sigmoid(model(batch['image'].cuda()))
            all_pred.append(y_hat.cpu().numpy())
            all_paths.extend(batch['path'])
            all_study_id.extend(batch['study_id'])
            all_slice_num.extend(batch['slice_num'])

            if subset != 'test':
                y = batch['labels']
                all_gt.append(y.numpy())

    pred_columns = ['pred_epidural', 'pred_intraparenchymal', 'pred_intraventricular', 'pred_subarachnoid',
                    'pred_subdural', 'pred_any']
    gt_columns = ['gt_epidural', 'gt_intraparenchymal', 'gt_intraventricular', 'gt_subarachnoid', 'gt_subdural',
                  'gt_any']

    if subset == 'test':
        all_pred = np.concatenate(all_pred)
        df = pd.DataFrame(all_pred, columns=pred_columns)
    else:
        all_pred = np.concatenate(all_pred)
        all_gt = np.concatenate(all_gt)
        df = pd.DataFrame(np.hstack((all_gt, all_pred)), columns=gt_columns + pred_columns)

    df = pd.concat((df, pd.DataFrame({
        'path': all_paths, 'study_id': all_study_id, 'slice_num': all_slice_num})), axis=1)
    df.to_csv(df_out_path, index=False)


if __name__ == '__main__':
    checkpoint_paths = [
        '/kolos/m2/ct/models/classification/rsna/0014_384/0123/models/_ckpt_epoch_2.ckpt',
        '/kolos/m2/ct/models/classification/rsna/0014_384/0124/models/_ckpt_epoch_2.ckpt',
        '/kolos/m2/ct/models/classification/rsna/0014_384/0134/models/_ckpt_epoch_4.ckpt',
        '/kolos/m2/ct/models/classification/rsna/0014_384/0234/models/_ckpt_epoch_4.ckpt',
        '/kolos/m2/ct/models/classification/rsna/0014_384/1234/models/_ckpt_epoch_4.ckpt'
    ]

    predict(checkpoint_paths[0], 0, 'val', 'hflip')
