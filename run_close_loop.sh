#!/bin/bash

######################################################################
################ OLD DATASET #########################################
#####################################################################

BEGIN=0
END=100
MODEL=resnet
LOAD_MODEL=00002
SPLIT_PATH=data_split/old_dataset/rand_split/test_scenes.txt
DATA_PATH=/home/nemodrive/workspace/roberts/UPB_dataset/old_dataset
SIM_DIR=simulation

python close_loop.py \
	--begin $BEGIN \
	--end $END \
	--load_model $LOAD_MODEL \
	--split_path $SPLIT_PATH \
	--data_path $DATA_PATH \
	--sim_dir $SIM_DIR \
	--use_speed \
	--use_old \
	
###################################################################
####################### NEW DATASET ###############################
###################################################################

# LOAD_MODEL=00001
# DATA_PATH=/home/nemodrive/workspace/roberts/NemodriveFinalSplit/chunks
# SIM_DIR=simulation

# python close_loop.py \
# 	--load_model $LOAD_MODEL \
# 	--data_path $DATA_PATH \
# 	--sim_dir $SIM_DIR \
# 	--use_speed \
