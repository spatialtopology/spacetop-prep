#!/usr/bin/env python
# encoding: utf-8

# %% libraries _________________________________________________________________________________________
import argparse
import datetime
import glob
import itertools
import json
import logging
import os
import sys
from os.path import join
from pathlib import Path
from statistics import mean
from tkinter import Variable
from typing import Optional

import matplotlib.pyplot as plt
import neurokit2 as nk
import numpy as np
import pandas as pd

# import spacetop_prep.physio.utils.checkfiles
# import spacetop_prep.physio.utils.initialize
# import spacetop_prep.physio.utils.preprocess
# import spacetop_prep.physio.utils.ttl_extraction
from spacetop_prep.physio import utils

print(utils.checkfiles)
print(utils.checkfiles.glob_physio_bids)

__author__ = "Heejung Jung, Yaroslav Halchenko, Isabel Neumann"
__copyright__ = "Spatial Topology Project"
# people who reported bug fixes, made suggestions, etc. but did not actually write the code.
__credits__ = ["Yaroslav Halchenko"]
__license__ = "MIT"
__version__ = "0.1"
__maintainer__ = "Heejung Jung"
__email__ = "heejung.jung@colorado.edu"
__status__ = "Development"

# %%
def main():
    """
    TODO:
    minimize spaghetti
    - make two separate functions
    1) pain process python function
    2) non pain run process python function

    ENH:
    allow for user to input which channels to use
    main channel (stimuli)
    boundary channel (cue) (rating)
    """

    args = get_args()

    physio_dir = args.input_physiodir
    beh_dir = args.input_behdir
    log_dir = args.output_logdir
    output_savedir = args.output_savedir
    metadata = args.metadata
    dictchannel_json = args.dictchannel
    slurm_id = args.slurm_id  # e.g. 1, 2
    stride = args.stride  # e.g. 5, 10, 20, 1000
    zeropad = args.zeropad  # sub-0016 -> 4
    task = args.task  # e.g. 'task-social' 'task-fractional' 'task-alignvideos'
    samplingrate = args.samplingrate  # e.g. 2000
    SCR_epoch_start = args.scr_epochstart
    SCR_epoch_end = args.scr_epochend
    ttl_index = args.ttl_index
    remove_subject_int = args.exclude_sub

    # %% NOTE: local test
    # sub 73
    # ses 1
    # run 5
    # beh_fname = '/Users/h/Dropbox/projects_dropbox/spacetop-prep/spacetop_prep/physio/utils/tests/sub-0081_ses-01_task-social_run-01-pain_beh.csv'
    # physio_fpath = '/Users/h/Dropbox/projects_dropbox/spacetop-prep/spacetop_prep/physio/utils/tests/sub-0081_ses-01_task-cue_run-01-pain_recording-ppg-eda-trigger_physio.tsv'
    # meta_fname = '/Users/h/Dropbox/projects_dropbox/spacetop-prep/spacetop_prep/physio/utils/tests/spacetop_task-social_run-metadata.csv'
    # dictchannel_json = '/Users/h/Dropbox/projects_dropbox/spacetop-prep/spacetop_prep/physio/p01_channel.json'
    # beh_df = pd.read_csv(beh_fname)
    # physio_df = pd.read_csv(physio_fpath, sep='\t')
    # runmeta = pd.read_csv(meta_fname)
    # samplingrate = 2000
    # ttl_index = 2
    # tonic_epoch_end = 20
    # tonic_epoch_start = -1

    # %%
    dict_channel = json.load(open(dictchannel_json))

    plt.rcParams['figure.figsize'] = [15, 5]  # Bigger images
    plt.rcParams['font.size'] = 14

    # %% set parameters
    sub_list = []
    # remove_subject_int = [1, 2, 3, 4, 5, 6]
    sub_list = utils.initialize.sublist(
        physio_dir, remove_subject_int, slurm_id, stride=stride, sub_zeropad=zeropad)
    ses_list = [1, 3, 4]
    run_list = [1, 2, 3, 4, 5, 6]
    sub_ses = list(itertools.product(sorted(sub_list), ses_list, run_list))


    # set up logger _______________________________________________________________________________________
    runmeta = pd.read_csv(metadata)
    logger_fname = os.path.join(
    log_dir, f"data-physio_step-03-groupanalysis_{datetime.date.today().isoformat()}.txt")
    f = open(logger_fname, "w")
    logger = utils.initialize.logger(logger_fname, "physio")

    # %%____________________________________________________________________________________________________
    flag = []
    for i, (sub, ses_ind, run_ind) in enumerate(sub_ses):

        # NOTE: open physio dataframe (check if exists) __________________________________________________________

        ses = f"ses-{ses_ind:02d}"
        run = f"run-{run_ind:02d}"
        logger.info(
            "__________________%s %s %s__________________", sub, ses, run)
        physio_flist = utils.checkfiles.glob_physio_bids(
            physio_dir, sub, ses, task, run)
        try:
            physio_fpath = physio_flist[0]
            logger.info(physio_fpath)
        except: #  IndexError:
            logger.error(
                "\t* missing physio file - %s %s %s DOES NOT exist", sub, ses, run)
            continue
        physio_fname = os.path.basename(physio_fpath)
        sub = utils.initialize.extract_bids(physio_fname, 'sub')
        ses = utils.initialize.extract_bids(physio_fname, 'ses')
        task = utils.initialize.extract_bids(physio_fname, 'task')
        run = f"run-{run_ind:02d}"

    # NOTE: identify physio file for corresponding sub/ses/run _______________________________________________
        physio_fname = os.path.basename(physio_fpath)
        logger.info({physio_fname})
        task = [match for match in physio_fname.split('_') if "task" in match][0]
        physio_df = pd.read_csv(physio_fpath, sep='\t')


    # NOTE: identify behavioral file for corresponding sub/ses/run ____________________________________
        beh_fpath = join(beh_dir, sub, ses,
                 f"{sub}_{ses}_task-social_{run}*_beh.csv")
        beh_fname = utils.initialize.check_beh_exist(beh_fpath)
        logger.info("beh_fpath: %s", beh_fpath)
        logger.info("beh_fname: %s", beh_fname)
        if beh_fname is None:
            continue
        beh_df = pd.read_csv(beh_fname)
        run_type = utils.initialize.check_run_type(beh_fname)
        logger.info(
            "__________________ %s %s %s %s ____________________", sub, ses, run, run_type)
        metadata_df = beh_df[[
            'src_subject_id', 'session_id', 'param_task_name', 'param_run_num',
            'param_cue_type', 'param_stimulus_type', 'param_cond_type', 'event02_expect_RT', 'event02_expect_angle', 'event04_actual_RT', 'event04_actual_angle'
        ]]

    # NOTE: merge fixation columns (some files look different) handle slight changes in biopac dataframe
        if 'fixation-01' in physio_df.columns:
            physio_df[
                'event_fixation'] = physio_df['fixation-01'] + physio_df['fixation-02']

    # NOTE: baseline correct -- extract fixations: _________________________________________________________________________________
        utils.preprocess.identify_fixation_sec(physio_df, 'event_fixation', samplingrate)
        physio_df_bl = utils.preprocess.baseline_correct(
            df=physio_df, raw_eda_col='physio_eda', baseline_col='event_fixation')

        # ___________________________________________________________________________________

    # NOTE: extract epochs ___________________________________________________________________________________
        dict_onset = {}
        for i, (key, value) in enumerate(dict_channel.items()):
            dict_onset[value] = {}

            utils.preprocess.binarize_channel(physio_df,
                                               source_col=key,
                                               new_col=value,
                                               threshold=None,
                                               binary_high=5,
                                               binary_low=0)
            dict_onset[value] = utils.preprocess.identify_boundary(
                physio_df, value)
            logger.info("\t* total number of %s trials: %d",
                        value, len(dict_onset[value]['start']))


    # NOTE: TTL extraction ___________________________________________________________________________________
        if run_type == 'pain':
            final_df = pd.DataFrame()
            # binarize TTL channels (raise error if channel has no TTL, despite being a pain run)
            nan_index, metadf_dropNA, plateau_start = utils.ttl_extraction.ttl_extraction(
                physio_df=physio_df,
                dict_beforettl=dict_onset['event_expectrating'],
                dict_afterttl=dict_onset['event_actualrating'],
                dict_stimuli=dict_onset['event_stimuli'],
                samplingrate=samplingrate,
                metadata_df=metadata_df,
                ttl_index=ttl_index
            )

            # create a dictionary for neurokit. this will serve as the events
            event_stimuli = {
                'onset': np.array(plateau_start).astype(pd.Int64Dtype),
                'duration': np.repeat(samplingrate * 5, len(plateau_start)),
                'label': np.array(np.arange(len(plateau_start))),
                'condition': metadf_dropNA['param_stimulus_type'].values.tolist()
            }
            # utils.qcplots.plot_ttl_extraction(physio_df, [
            #                     'EDA_corrected_02fixation', 'physio_ppg', 'trigger_heat'], event_stimuli)

        else:
            metadf_dropNA =  metadata_df.assign(trial_num=list(np.array(metadata_df.index + 1)))

            event_stimuli = {
                'onset': np.array(dict_onset['event_stimuli']['start']),
                'duration': np.repeat(samplingrate * 5, 12),
                'label': np.array(np.arange(12), dtype='<U21'),
                'condition': beh_df['param_stimulus_type'].values.tolist()
            }
            # utils.qcplots.plot_ttl_extraction(physio_df, [
                                # 'EDA_corrected_02fixation', 'physio_ppg', 'trigger_heat'], event_stimuli)

    # NOTE: save dict_onset __________________________________________________________________________________
        dict_savedir = join(output_savedir, 'physio01_SCR', sub, ses)
        dict_fname = f"{sub}_{ses}_{run}_runtype-{run_type}_samplingrate-{samplingrate}_onset.json"
        utils.preprocess.save_dict(dict_savedir, dict_fname, dict_onset)

    # NOTE: PHASIC_____________________________________________________________________________
        scr_phasic = utils.preprocess.extract_SCR(df=physio_df,
                                 eda_col='physio_eda',
                                 amp_min=0.01,
                                 event_stimuli=event_stimuli, samplingrate=samplingrate,
                                 epochs_start=SCR_epoch_start, epochs_end=SCR_epoch_end, baseline_correction=True,
                                 plt_col=['trigger_mri', 'event_fixation', 'event_cue', 'event_expectrating', 'event_stimuli', 'event_actualrating'],
                                 plt_savedir='./plt')
        if scr_phasic is None:
            continue

    #  NOTE: concatenate dataframes __________________________________________________________________________
        metadata_SCR = utils.preprocess.combine_metadata_SCR(scr_phasic, metadf_dropNA, total_trial = 12)

    # NOTE: save phasic data _________________________________________________________________________________
        phasic_save_dir = join(output_savedir, 'physio02_SCR', sub, ses)
        Path(phasic_save_dir).mkdir(parents=True, exist_ok=True)
        SCR_df = pd.concat(
            [metadata, metadata_SCR], axis=1
        )
        phasic_fname = f"{sub}_{ses}_{run}_runtype-{run_type}_epochstart-0_epochend-5_physio-scr.csv"
        SCR_df.to_csv(join(phasic_save_dir, phasic_fname), index = False)
        logger.info("__________________ :+: FINISHED :+: __________________\n")


def get_args():
    # argument parser _______________________________________________________________________________________
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-physiodir",
                        type=str, help="path where BIDS converted physio data lives")
    parser.add_argument("--input-behdir",
                        type=str, help="path where BIDS converted behavioral data lives")
    parser.add_argument("--output-logdir",
                        type=str, help="path where logs will be saved - essential for re-running failed participants")
    parser.add_argument("--output-savedir",
                        type=str, help="path where transformed physio data will be saved")
    parser.add_argument("--metadata",
                        type=str, help=".csv filepath to metadata file of run information (complete/runtype etc)")
    parser.add_argument("--dictchannel",
                        type=str,
                        help=".json file for changing physio data channel names | key:value == "
                             "old_channel_name:new_channel_name")
    parser.add_argument("-sid", "--slurm-id", type=int,
                        help="specify slurm array id")
    parser.add_argument("--stride", type=int,
                        help="how many participants to batch per jobarray")
    parser.add_argument("-z", "--zeropad",
                        type=int, help="how many zeros are padded for BIDS subject id")
    parser.add_argument("-t", "--task",
                        type=str, help="specify task name (e.g. task-alignvideos)")
    parser.add_argument("-sr", "--samplingrate", type=int,
                        help="sampling rate of acquisition file")
    parser.add_argument("--scr-epochstart", type=int,
                        help="beginning of epoch")
    parser.add_argument("--scr-epochend", type=int,
                        help="end of epoch")
    parser.add_argument("--ttl-index", type=int,
                        help="index of which TTL to use")
    parser.add_argument('--exclude-sub', nargs='+',
                        type=int, help="string of integers, subjects to be removed from code", required=False)
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()
