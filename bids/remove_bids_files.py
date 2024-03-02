#!/usr/bin/env python3
"""
the purpose of this script is to automate the "removing-dup" process in datalad. 
Once a duplicate file is confirmed and removed, we need to update 3 sources
- Datalad remove and save duplicate files
- Update file in *.scans.tsv
- Update in IntendedFor field in the fieldmap .json files
This script is to update the IntendedFor field in the fieldmap jsons
"""
from heudiconv.utils import load_json
from heudiconv.utils import save_json
import os, time, sys, glob
from os.path import join
import json
from pathlib import Path
import pandas as pd

# example file dir
# /dartfs-hpc/rc/lab/C/CANlab/labdata/data/spacetop/dartmouth/sub-0085/ses-01/func/sub-0085_ses-01_task-alignvideo_acq-mb8_run-01_bold__dup-01.nii.gz'
# {main_dir}/{sub}/{ses}/func
fpattern = sys.argv[1]
bids_dir = sys.argv[2] # reason for this: script is in preprocessing git repo. BIDS repo is in a totally different directory, not parent or child.
# 1. get list of dup names _____________________________________________________________
current_dir = os.getcwd()
main_dir = Path(current_dir).parents[1]
save_dir = join(main_dir, 'log')

dup_glob = glob.glob(join(bids_dir, fpattern))
flaglist = []
flaglist.append(f"This file keeps track of dup file and fieldmap mismatches.\nTwo erroneous cases:\n 1) IntendedFor field does not exist from the get go [IntendedFor X] \n 2) IntendedFor field exists. However, Duplicate file does not exist within this key [IntendedFor O; Dup X]")
for ind, dup_fpath in enumerate(dup_glob):
    fmap_dir = os.path.join(Path( os.path.dirname(dup_fpath)).parents[0], 'fmap')
    fmap_glob = '*-run-'
    dup_fname = os.path.basename(dup_fpath)
    # TODO: make it flexible to handle DWI and T1 .jsonl.
    # currently, we're just going to feed in epi images and update epi.jsons. 
    # dictionary: 
    # - DWI: acq-96dirX6b0Xmb
    # - BOLD: acq-mb8
# 2. open fieldmap .json with corresponding .dup files _____________________________________________________________
    for fmap_ind, fmap_fname in enumerate(join(fmap_dir, '*')):
        sidecar = load_json(fmap_fname)
        # 2-1. check if "IntendedFor" field exists within json
        if 'IntendedFor' in sidecar:
            copy_list = sidecar['IntendedFor']
            print(copy_list)
            # 2-2. find "IntendedFor" field and if dup_fname exists, pop item
            dup_index = [i for i, s in enumerate(copy_list) if dup_fname in s]
            if dup_index:
                copy_list.pop(dup_index[0])
                sidecar['IntendedFor'] = copy_list
                print(f"removed {dup_fname} from list")
                save_json(fmap_fname, sidecar)
# 3. remove files __________________________________________
                os.remove(dup_fpath)
                # TODO: remove all 4 types of files - See if you can remove and datalad save within this script.
                # 1) remove bold__dup-01.json
                # 2) remove bold__dup-01.nii.gz
                # 3) remove sbref__dup-01.json
                # 4) remove sbref__dup-01.nii.gz

# 4. update scans.tsv by removing the dup_fname from entire row
    tsv_fname = glob.glob(join(os.path.dirname(dup_fpath)).parents[0], '*_scans.tsv')[0]
    df = pd.read_csv(tsv_fname, sep = '\t')
    drop_df = df[ df[ 'filename' ].str.contains(dup_fname )==False ]
    drop_df.to_csv(tsv_fname) 
# 5. save filenames with missing intendedfor fields or missing dup filenames __________________________________________
txt_filename = os.path.join(save_dir, 'dup_flaglist.txt')
with open(txt_filename, 'w') as f:
    f.write(json.dumps(flaglist))