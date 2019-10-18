class BaseConfig:
    nb_folds = 5
    train_dir = '/mnt/data_fast/RSNA_Intracranial_Hemorrhage_Detection/stage_1_train_images'
    test_dir = '/mnt/data_fast/RSNA_Intracranial_Hemorrhage_Detection/stage_1_test_images'
    labels_path = "/mnt/data_fast/RSNA_Intracranial_Hemorrhage_Detection/stage_1_train.csv"

    data_root = "/mnt/data_fast_local/RSNA_Intracranial_Hemorrhage_Detection/"

    checkpoints_dir = "/home/dmytro/ml/kaggle-rsna-2019/output/checkpoints"
    tensorboard_dir = "/home/dmytro/ml/kaggle-rsna-2019/output/tensorboard"
    oof_dir = "/home/dmytro/ml/kaggle-rsna-2019/output/oof"
    prediction_dir = "/home/dmytro/ml/kaggle-rsna-2019/output/prediction"

    n_classes = 6
    csv_root_dir = None
