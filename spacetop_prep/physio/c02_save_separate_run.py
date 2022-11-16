#!/usr/bin/env python
""" 
save_seperate_run.py
Separates acq into runs and saves as bids format. 
This script reads the acquisition file collected straight from our biopac PC

Parameters
------------------
operating: str
    options: 'local' vs. 'discovery'
slurm_id: int
    if operating on discovery, it would be the job array id
stride: int
    how many participants to batch per jobarray (i.e. slurm)id
zeropad: int
    how many zeros are padded for BIDS subject id
task: str
    specify task name (e.g., 'task-social', 'task-fractional' 'task-alignvideos', 'task-faces', 'task-shortvideos')
run_cutoff: int
    threshold for determining "kosher" runs versus not. 
    for instance, task-social is 398 seconds long. I use the threshold of 300 as a threshold. 
    Anything shorter than that is discarded and not converted into a run

"""

# %% libraries _______________________________________________________________________________________________
import neurokit2 as nk
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import itertools
import os
import sys
import shutil
import glob
from pathlib import Path
import json
from itertools import compress
import datetime
from os.path import join
import logging
import argparse

pwd = os.getcwd()
main_dir = Path(pwd).parents[0]
sys.path.append(os.path.join(main_dir))
sys.path.insert(0, os.path.join(main_dir))
print(sys.path)

from . import utils
from .utils import preprocess
from .utils import preprocess, initialize

__author__ = "Heejung Jung"
__copyright__ = "Spatial Topology Project"
__credits__ = ["Heejung"] # people who reported bug fixes, made suggestions, etc. but did not actually write the code.
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Heejung Jung"
__email__ = "heejung.jung@colorado.edu"
__status__ = "Development"

sub_zeropad = 4

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--operating",
                    choices=['local', 'discovery'],
                    help="specify where jobs will run: local or discovery")
parser.add_argument("-sid", "--slurm_id", type=int,
                    help="specify slurm array id")
parser.add_argument("--stride", help="how many participants to batch per jobarray")
parser.add_argument("-z", "--zeropad", help="how many zeros are padded for BIDS subject id")
parser.add_argument("-t", "--task",
                    type=str, help="specify task name (e.g. task-alignvideos)")
parser.add_argument("-c", "--run-cutoff", type=int, help="specify cutoff threshold for distinguishing runs (in seconds)")
args = parser.parse_args()

operating = args.operating # 'local', 'discovery'
slurm_id = args.slurm_id # e.g. 1, 2
stride = args.stride # e.g. 5, 10, 20, 1000
zeropad = args.zeropad # sub-0016 -> 4
task = args.task # e.g. 'task-social' 'task-fractional' 'task-alignvideos'
run_cutoff = args.run_cutoff # e.g. 300

# spacetop
dict_task = {'task-social':'task-cue'}
dict_column = {
    'fMRI Trigger - CBLCFMA - Current Feedba':'trigger_mri',
    'TSA2 TTL - CBLCFMA - Current Feedback M':'trigger_heat',
    'Skin Conductance (EDA) - EDA100C-MRI':'physio_eda',
    'Pulse (PPG) - PPG100C':'physio_ppg',
    'trigger': 'event_experimentduration',
    'fixation': 'event_fixation',
    'cue': 'event_cue',
    'expect': 'event_expectrating',
    'administer': 'event_stimuli',
    'actual': 'event_actualrating',
}
# %% 
if operating == 'discovery':
    spacetop_dir = '/dartfs-hpc/rc/lab/C/CANlab/labdata/projects/spacetop_projects_social'
    physio_dir = '/dartfs-hpc/rc/lab/C/CANlab/labdata/data/spacetop_data/physio'
    source_dir = join(physio_dir, 'physio02_sort')
    if dict_task:
        save_dir = join(physio_dir, 'physio03_bids', dict_task[task])
    else:
        save_dir = join(physio_dir, 'physio03_bids', task)
    log_savedir = os.path.join(physio_dir, 'log')

elif operating == 'local':
    spacetop_dir = '/Volumes/spacetop_projects_social'
    physio_dir = '/Volumes/spacetop_data/physio'
    source_dir = join(physio_dir, 'physio02_sort')
    if dict_task:
        save_dir = join(physio_dir, 'physio03_bids', dict_task[task])
    else:
        save_dir = join(physio_dir, 'physio03_bids', task)
    log_savedir = join(physio_dir, 'log')

Path(save_dir).mkdir(parents=True,exist_ok=True )
Path(log_savedir).mkdir(parents=True,exist_ok=True )
print(spacetop_dir)
print(physio_dir)
print(save_dir)

# set up logger ______________________________________________________________________________________________
runmeta = pd.read_csv(
    join(spacetop_dir, "data/spacetop_task-social_run-metadata.csv"))
#TODO: come up with scheme to update logger files
ver = 1
logger_fname = os.path.join(
    log_savedir, f"biopac_flaglist_{task}_{datetime.date.today().isoformat()}_ver-4.txt")
f = open(logger_fname, "w")
logger = utils.initialize._logger(logger_fname, "physio")


# %% NOTE: 1. glob acquisition files _________________________________________________________________________
# filename ='../spacetop_biopac/data/sub-0026/SOCIAL_spacetop_sub-0026_ses-01_task-social_ANISO.acq'
remove_sub = [1, 2, 3, 4, 5, 6]
sub_list = utils.initialize._sublist(source_dir, remove_sub, slurm_id, stride=10, sub_zeropad=4)

acq_list = []
logger.info(sub_list)
for sub in sub_list:
    acq = glob.glob(os.path.join(source_dir, sub, "**", f"*{task}*.acq"),
                     recursive=True)
    acq_list.append(acq)
flat_acq_list = [item for sublist in acq_list  for item in sublist]

# %%
for acq in sorted(flat_acq_list):
# NOTE: 2. extract information from filenames ________________________________________________________________
    filename = os.path.basename(acq)
    bids_dict = {}
    bids_dict['sub'] = sub  = utils.initialize._extract_bids(filename, 'sub')
    bids_dict['ses'] = ses  = utils.initialize._extract_bids(filename, 'ses')
    bids_dict['task']= task = utils.initialize._extract_bids(filename, 'task')
    if dict_task:
        bids_dict['task'] = dict_task[task]
        task = bids_dict['task']


# NOTE: 3. open physio dataframe (check if exists) ___________________________________________________________
    if os.path.exists(acq):
        main_df, samplingrate = nk.read_acqknowledge(acq)
        logger.info("__________________%s %s __________________", sub, ses)
        logger.info("file exists! -- starting tranformation: ")
        main_df.rename(columns=dict_column, inplace=True)
    else:
        logger.error("no biopac file exists")
        continue
        
# NOTE: 4. create an mr_aniso channel for MRI RF pulse channel ________________________________________________
    try:
        main_df['mr_aniso'] = main_df['trigger_mri'].rolling(
        window=3).mean()
    except:
        logger.error("no MR trigger channel - this was the early days. re run and use the *trigger channel*")
        logger.error(acq)
        continue
# TST: files without trigger keyword in the acq files should raise exception        
    try:
        utils.preprocess._binarize_channel(main_df,
                                        source_col='mr_aniso',
                                        new_col='spike',
                                        threshold=40,
                                        binary_high=5,
                                        binary_low=0)
    except:
        logger.error(f"data is empty - this must have been an empty file or saved elsewhere")
        continue

    dict_spike = utils.preprocess._identify_boundary(main_df, 'spike')
    logger.info("number of spikes within experiment: %d", len(dict_spike['start']))
    main_df['bin_spike'] = 0
    main_df.loc[dict_spike['start'], 'bin_spike'] = 5
    
# NOTE: 5. create an mr_aniso channel for MRI RF pulse channel ________________________________________________
    try:
        main_df['mr_aniso_boxcar'] = main_df['trigger_mri'].rolling(
            window=int(samplingrate)).mean()
        mid_val = (np.max(main_df['mr_aniso_boxcar']) -
                np.min(main_df['mr_aniso_boxcar'])) / 5
        utils.preprocess._binarize_channel(main_df,
                                        source_col='mr_aniso_boxcar',
                                        new_col='mr_boxcar',
                                        threshold=mid_val,
                                        binary_high=5,
                                        binary_low=0)
    except:
        logger.error(f"ERROR:: binarize RF pulse TTL failure - ALTERNATIVE:: use channel trigger instead")
        logger.debug(logger.error)
        continue
    dict_runs = utils.preprocess._identify_boundary(main_df, 'mr_boxcar')
    logger.info("* start_df: %s", dict_runs['start'])
    logger.info("* stop_df: %s", dict_runs['stop'])
    logger.info("* total of %d runs", len(dict_runs['start']))

# NOTE: 6. adjust one TR (remove it!)_________________________________________________________________________
    sdf = main_df.copy()
    sdf.loc[dict_runs['start'], 'bin_spike'] = 0
    sdf['adjusted_boxcar'] = sdf['bin_spike'].rolling(window=int(samplingrate)).mean()
    mid_val = (np.max(sdf['adjusted_boxcar']) -
               np.min(sdf['adjusted_boxcar'])) / 4
    utils.preprocess._binarize_channel(sdf,
                                       source_col='adjusted_boxcar',
                                       new_col='adjust_run',
                                       threshold=mid_val,
                                       binary_high=5,
                                       binary_low=0)
    dict_runs_adjust = utils.preprocess._identify_boundary(sdf, 'adjust_run')
    logger.info("* adjusted start_df: %s", dict_runs_adjust['start'])
    logger.info("* adjusted stop_df: %s", dict_runs_adjust['stop'])

# NOTE: 7. identify run transitions ___________________________________________________________________________
    run_list = list(range(len(dict_runs_adjust['start'])))
    try:
        run_bool = ((np.array(dict_runs_adjust['stop'])-np.array(dict_runs_adjust['start']))/samplingrate) > run_cutoff
    except:
        logger.error("start and stop datapoints don't match")
        logger.debug(logger.error)
        continue
    clean_runlist = list(compress(run_list, run_bool))
    shorter_than_threshold_length = list(compress(run_list, ~run_bool))
    
# NOTE: 8. save identified runs after cross referencing metadata __________________________________________________________
    if len(shorter_than_threshold_length) > 0:
        logger.info(
            "runs shorter than %d sec: %s %s %s - run number in python order", 
            run_cutoff, sub, ses, shorter_than_threshold_length)
    scannote_reference = utils.initialize._subset_meta(runmeta, sub, ses)

    if len(scannote_reference.columns) == len(clean_runlist):
        ref_dict = scannote_reference.to_dict('list')
        run_basename = f"{sub}_{ses}_{task}_CLEAN_RUN-TASKTYLE_recording-ppg-eda_physio.csv"
        # main_df.rename(columns=dict_column, inplace=True)
        main_df_drop = main_df[main_df.columns.intersection(list(dict_column.values()))]
        utils.initialize._assign_runnumber(ref_dict, clean_runlist, dict_runs_adjust, main_df_drop, save_dir,run_basename,bids_dict)
        logger.info("__________________ :+: FINISHED :+: __________________")
    else:
        logger.error(f"number of complete runs do not match scan notes")
        logger.error("clean_runlist: %s, scannote_reference.columns: %s", clean_runlist, scannote_reference.columns)
        
        logger.debug(logger.error)