#!/usr/bin/env python
# coding: utf-8
import os
import pandas as pd
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=str, help="path to the text file containing training scenes")
    parser.add_argument("--test", type=str, help="path to the text file containing test scenes")
    parser.add_argument("--use_pose", action="store_true", help="use pose estimation dataset")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()

    # read training scenes
    with open(args.train, "rt") as fin:
        train_scenes = fin.read()

    # read testing scenes
    with open(args.test, "rt") as fin:
        test_scenes = fin.read()
   
    train_scenes = train_scenes.split()
    test_scenes = test_scenes.split()

    train_scenes = set(train_scenes)
    test_scenes = set(test_scenes)
    assert train_scenes.intersection(test_scenes) == set(), \
        "There is an overlap between the train and test scenes"

    # define paths
    path = os.path.join("dataset", ("pose" if args.use_pose else "gt") + "_dataset")
    path_img = os.path.join(path, "img_real")
    files = os.listdir(path_img)

    # buffer for train and test files
    train_files = []
    test_files = []

    for file in files:
        # get the scene
        scene, _, _ = file.split(".")

        # add scene to the corresponding buffer
        if scene in train_scenes:
            train_files.append(file[:-4])
        else:
            test_files.append(file[:-4])

    # save as csv
    train_csv = pd.DataFrame(train_files, columns=["name"])
    test_csv = pd.DataFrame(test_files, columns=["name"])

    path_train = os.path.join(path, "train_real.csv")
    path_test = os.path.join(path, "test_real.csv")

    train_csv.to_csv(path_train, index=False)
    test_csv.to_csv(path_test, index=False)
