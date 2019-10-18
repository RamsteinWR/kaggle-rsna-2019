import argparse
import os
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
import numpy as np
import pandas as pd

from rsna19.data import dataset
from rsna19.configs.base_config import BaseConfig
from rsna19.models.clf2D.experiments import MODELS
from rsna19.models.clf2D.train import build_model_str
import albumentations
import albumentations.pytorch


def predict(model_name, fold, epoch, is_test, df_out_path, mode='normal', run=None):
    model_str = build_model_str(model_name, fold, run)
    model_info = MODELS[model_name]

    checkpoints_dir = f'{BaseConfig.checkpoints_dir}/{model_str}'
    print('\n', model_name, '\n')

    model = model_info.factory(**model_info.args)

    dataset_valid = dataset.IntracranialDataset(
        csv_file='test.csv' if is_test else '5fold.csv',
        folds=[fold],
        preprocess_func=albumentations.pytorch.ToTensorV2(),
        return_labels=False,
        is_test=is_test,
        **model_info.dataset_args
    )

    model.eval()
    checkpoint = torch.load(f'{checkpoints_dir}/{epoch:03}.pt')
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.cuda()

    batch_size = 16

    data_loader = DataLoader(dataset_valid,
                             shuffle=False,
                             num_workers=16,
                             batch_size=batch_size)

    all_paths = []
    all_study_id = []
    all_slice_num = []
    all_gt = []
    all_pred = []

    data_iter = tqdm(enumerate(data_loader), total=len(data_loader))
    for iter_num, batch in data_iter:
        with torch.set_grad_enabled(False):
            y_hat = torch.sigmoid(model(batch['image'].float().cuda()))
            all_pred.append(y_hat.cpu().numpy())
            all_paths.extend(batch['path'])
            all_study_id.extend(batch['study_id'])
            all_slice_num.extend(batch['slice_num'])

            if not is_test:
                y = batch['labels']
                all_gt.append(y.numpy())

    pred_columns = ['pred_epidural', 'pred_intraparenchymal', 'pred_intraventricular', 'pred_subarachnoid',
                    'pred_subdural', 'pred_any']
    gt_columns = ['gt_epidural', 'gt_intraparenchymal', 'gt_intraventricular', 'gt_subarachnoid', 'gt_subdural',
                  'gt_any']

    if is_test:
        all_pred = np.concatenate(all_pred)
        df = pd.DataFrame(all_pred, columns=pred_columns)
    else:
        all_pred = np.concatenate(all_pred)
        all_gt = np.concatenate(all_gt)
        df = pd.DataFrame(np.hstack((all_gt, all_pred)), columns=gt_columns + pred_columns)

    df = pd.concat((df, pd.DataFrame({
        'path': all_paths, 'study_id': all_study_id, 'slice_num': all_slice_num})), axis=1)
    df.to_csv(df_out_path, index=False)


def predict_test(model_name, fold, epoch, mode='normal', run=None):
    run_str = '' if not run else f'_{run}'
    prediction_dir = f'{BaseConfig.prediction_dir}/test/{model_name}{run_str}'
    os.makedirs(prediction_dir, exist_ok=True)
    df_out_path = f'{prediction_dir}/fold_{fold}_ch{epoch}_{mode}.csv'
    predict(model_name=model_name, fold=fold, epoch=epoch, is_test=True, df_out_path=df_out_path, mode=mode, run=run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', type=str, default='check')
    parser.add_argument('--model', type=str, default='')
    parser.add_argument('--run', type=str, default='')
    parser.add_argument('--fold', type=int, default=-1)
    parser.add_argument('--weights', type=str, default='')
    parser.add_argument('--epoch', type=int, default=-1)

    parser.add_argument('--resume_weights', type=str, default='')
    parser.add_argument('--resume_epoch', type=int, default=-1)

    args = parser.parse_args()
    action = args.action

    if action == 'predict_test':
        predict_test(model_name=args.model, run=args.run, fold=args.fold, epoch=args.epoch)
