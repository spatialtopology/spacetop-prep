#!/usr/bin/env python
"""
1. Unlock scans_tsv and update it based on runtype metadata
2. Harmonize discrepancy between nifti and behavioral data
3. Starting from Line 242, Behavioral data conversion to BIDS valid format
Same format occurs for pain, vicarious, cognitive data
convert behavioral file into event lists and singletrial format

- regressor of interest per task
- duration of epoch
- rating onset
- potential covariates?
"""
# %%
import numpy as np
import pandas as pd
import os, glob, re, json
from os.path import join
from pathlib import Path
import logging
import subprocess
import argparse


__author__ = "Heejung Jung"
__copyright__ = "Spatial Topology Project"
__credits__ = ["Heejung"] # people who reported bug fixes, made suggestions, etc. but did not actually write the code.
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Heejung Jung"
__email__ = "heejung.jung@colorado.edu"
__status__ = "Development" 


# %% ---------------------------------------------------------------------------
#                                   Functions
# ------------------------------------------------------------------------------

# Configure the logger globally
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    handler = logging.FileHandler(log_file, mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed with error: {result.stderr}")
    else:
        print(result.stdout)


def list_nifti_and_event_files(designated_dir):
    nifti_files = []
    event_files = []
    files = glob.glob(os.path.join(designated_dir, '**'), recursive=True)
    
    for file in files:
        if 'task-social' in file and file.endswith('.nii.gz'):
            nifti_files.append(file)
        elif 'task-social' in file and file.endswith('_events.tsv'):
            event_files.append(file)

    return sorted(nifti_files), sorted(event_files)
# /Users/h/Documents/projects_local/spacetop-prep/spacetop_prep/events/spacetop_task-social_run-metadata.csv
code_dir = Path(__file__).resolve().parent
metadata_df = pd.read_csv(join(code_dir,  'spacetop_task-social_run-metadata.csv'))

def get_task_type(bids_string, metadata_df):
    fname = Path(bids_string).name
    sub = extract_bids(fname, 'sub')
    ses = extract_bids(fname, 'ses')
    run_column = extract_bids(fname, 'run')
    filtered_df = metadata_df[(metadata_df['sub'] == sub) & (metadata_df['ses'] == ses)]
    if not filtered_df.empty:
        return filtered_df[run_column].values[0]
    else:
        return None
    
    
def extract_run_and_task(filename):
    match = re.search(r'task-([a-zA-Z0-9]+)_.*_run-([0-9]+)', filename)
    if match:
        return match.groups()
    return None, None

def remove_orphan_nifti_files(nifti_files, event_files):
    event_file_basenames = [os.path.basename(f) for f in event_files]
    orphan_files = []

    for nifti_file in nifti_files:
        nifti_basename = os.path.basename(nifti_file)
        task, run = extract_run_and_task(nifti_basename)
        if task and run:
            expected_event_filename = f'sub-*_ses-*_task-social*_run-{run}_desc*_events.tsv'
            if not any(re.match(expected_event_filename.replace('*', '.*'), event_filename) for event_filename in event_file_basenames):
                orphan_files.append(nifti_file)
    
    return orphan_files

def extract_cue_metadata_and_run(filename):
    cue_metadata = re.search(r'_desc-(\w+)_events\.tsv', filename).group(1)
    run = re.search(r'_run-(\d+)_', filename).group(1)
    return cue_metadata, run

# Function to extract run information from filenames
def extract_run(filename):
    match = re.search(r'_run-(\d+)_', filename)
    return match.group(1) if match else None

# Function to map social files to cue metadata
def map_social_to_cue(filename):
    run = extract_run(filename)
    if run in cue_metadata_dict:
        return cue_metadata_dict[run]
    return None

def is_equivalent(val1, val2, tolerance=1):
    return abs(val1 - val2) <= tolerance
# TODO:

def calc_adjusted_angle_df(df, x_col, y_col, xcenter, ycenter):
    # Vectorized calculation of angles
    angles = np.arctan2((ycenter - df[y_col]), (df[x_col] - xcenter))
    
    # Adjust the angle so it's between 0 and π radians
    angles = np.pi - angles
    
    # Convert angles to degrees and ensure they are positive
    angles_deg = np.abs(np.degrees(angles))
    
    # Ensure all angles fall within the 0 to 180 range
    angles_deg = angles_deg % 360
    angles_deg[angles_deg > 180] = 360 - angles_deg[angles_deg > 180]
    
    return angles_deg

def calculate_ttl_values(stimulus_times, ttl_row, beh_df):
    # Retrieve the stimulus type from beh_df for the current row
    stimulus_type = beh_df['event03_stimulus_type']
    times = stimulus_times[stimulus_type]

    # Calculate TTL values if they are NaN in ttl_df
    if pd.isna(ttl_row['TTL1']):
        ttl_row['TTL1'] = beh_df['event03_stimulus_displayonset']
    if pd.isna(ttl_row['TTL2']):
        ttl_row['TTL2'] = ttl_row['TTL1'] + times['rampup']
    if pd.isna(ttl_row['TTL3']):
        ttl_row['TTL3'] = ttl_row['TTL2'] + times['plateau']
    if pd.isna(ttl_row['TTL4']):
        ttl_row['TTL4'] = ttl_row['TTL3'] + times['rampdown']
    return ttl_row

def categorize_rating(value):
    if value == "n/a" or pd.isna(value):
        return np.nan
    else:
        return pd.cut([value], bins=bins, labels=labels, right=True)[0]


def is_equivalent(val1, val2, tolerance=1):
    return abs(val1 - val2) <= tolerance

def extract_bids(filename: str, key: str) -> str:
    """
    Extracts BIDS information based on input "key" prefix.
    If filename includes an extension, code will remove it.
    """
    bids_info = [match for match in filename.split('_') if key in match][0]
    bids_info_rmext = bids_info.split(os.extsep, 1)
    return bids_info_rmext[0]

# %% ---------------------------------------------------------------------------
#  1. add task-social runtype metadata & 2. harmonize scans tsv and nifti files
# ------------------------------------------------------------------------------


# scans_list = sorted(glob.glob('sub-*/**/*scans*.tsv', recursive=True))
# for scan_fname in scans_list:
#     # NOTE: Step 1: Get the scans.tsv using datalad
#     run_command(f"datalad get {scan_fname}")
#     print(f"datalad get {scan_fname} ")
#     # Check if scans_file is not empty and unlock it using git annex
#     if os.path.exists(scan_fname) and os.path.getsize(scan_fname) > 0:
#         run_command(f"git annex unlock {scan_fname}")
#         print(f"unlock {scan_fname}")

#     scans_df = pd.read_csv(scan_fname, sep='\t')

#     # NOTE: Step 2: Define the directory containing the task-social event files
#     cue_events_dir = './' + os.path.dirname( scan_fname) + '/func'
#     cue_event_files = sorted([f for f in os.listdir(cue_events_dir) if 'task-social' in f and f.endswith('_events.tsv')])

#     # NOTE: Step 3: Function to extract cue metadata and run information from filenames
#     # Create a dictionary to map run to cue metadata
#     cue_metadata_dict = {}
#     for file in cue_event_files:
#         metadata, run = extract_cue_metadata_and_run(file)
#         cue_metadata_dict[run] = metadata


#     # NOTE: Step 4: Apply the function to add the task-social_runtype column
#     scans_df['task-social_runtype'] = scans_df['filename'].apply(lambda x: map_social_to_cue(x) if 'task-social' in x else None)
#     scans_df['task-social_runtype'].fillna('n/a', inplace=True)


#     # NOTE: Step 5: if events file and niftifiles disagree, delete files
#     nifti_files, event_files = list_nifti_and_event_files(cue_events_dir)
#     orphan_files = remove_orphan_nifti_files(nifti_files, event_files)
#     if orphan_files:
#         for orphan_file in orphan_files:
#             print(f"Removing {orphan_file}")
#             #run_command(f"git rm {orphan_file}")
#             scans_df = scans_df[scans_df['filename'] != os.path.basename(orphan_file)]

#     # Save the updated DataFrame back to the scans_file
#     scans_df.to_csv(scan_fname, index=False, sep='\t')

#     # Add the updated scans_file back to git annex
#     print(f"made edits to events file and deleted nifti files if not harmonized: {scan_fname}")
#     run_command(f"git annex add {scan_fname}")
#     run_command(f"git commit -m 'DOC: update scans tsv with task-social runtype metadata and remove orphan NIfTI files'")

    
#     # run_command(f"git annex add {scan_fname}")
#     # run_command(f"git commit -m 'DOC: update scans tsv and remove orphan NIfTI files'")
#     # NOTE: Step 6: ultimately, delete BIDS data
#     for event_fname in cue_event_files:
#         event_fpath = os.path.join(cue_events_dir, event_fname)
#         run_command(f"git rm {event_fpath}")
#         print(f"remove all the task-social events files {event_fpath}")
#     run_command(f"git commit -m 'DEP: delete non-bids compliant events file'")
#     print("run_command(git commit -m DEP: delete non-bids compliant events file")




# %% ---------------------------------------------------------------------------
#                                   Parameters
# ------------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Process behavioral files for specific subjects or all subjects.")
    parser.add_argument('--bids_string', type=str, help="BIDS formatted string in format: sub-{sub%4d} ses-{ses%2d} task-{task} run-{run%2d}")
    parser.add_argument('--bids_dir', type=str, default='/Users/h/Documents/projects_local/1076_spacetop', help="curated top directory of datalad.")
    parser.add_argument('--code_dir', type=str, default='/Users/h/Documents/projects_local/1076_spacetop/code', help="where this code lives.")
    parser.add_argument('--source_dir', type=str, default='/Users/h/Documents/projects_local/1076_spacetop/sourcedata', help="where this code lives.")
    return parser.parse_args()

args = parse_args()
bids_string = args.bids_string
bids_dir = args.bids_dir
code_dir = args.code_dir
source_dir = args.source_dir
beh_inputdir = join(source_dir, 'd_beh')
# task_name = args.task_name
# bids_dir = '/Users/h/Documents/projects_local/1076_spacetop' # the top directory of datalad
# code_dir = '/Users/h/Documents/projects_local/1076_spacetop/code' # where this code live
# source_dir = '/Users/h/Documents/projects_local/1076_spacetop/sourcedata'# where the source behavioral directory lives
# beh_inputdir = join(source_dir, 'd_beh')

trajectory_x = 960
trajectory_y = 707

# gLMS scale labels for expectation and outcome ratings
bins = [0, 1, 3, 10, 29, 64, 98, 180]
labels = [
    "No sensation",
    "Barely detectable",
    "Weak",
    "Moderate",
    "Strong",
    "Very Strong",
    "Strongest sensation of any kind"
]


# %% ---------------------------------------------------------------------------
#                           1. Cognitive BIDSify
# ------------------------------------------------------------------------------

task_name = 'cognitive'
cognitive_logger = setup_logger('cognitive', 'task-social_cognitive.log')

if args.bids_string is not None:
    if task_name == get_task_type(args.bids_string, metadata_df): # and task_name in args.bids_string:
        fname = Path(bids_string).name
        sub = extract_bids(fname, 'sub')
        ses = extract_bids(fname, 'ses')
        run = extract_bids(fname, 'run')

        # filtered_cognitive_flist = glob.glob(join(beh_inputdir, sub,  '**','task-social', '**', f'*{bids_string}*.csv'), recursive=True)
        filtered_cognitive_flist = glob.glob(str(Path(beh_inputdir) / sub / '**' / 'task-social' / '**' / f'*{args.bids_string}*.csv'), recursive=True)

        if not filtered_cognitive_flist:
            temp_fpath = glob.glob(str(Path(beh_inputdir) / sub / 'task-social' / ses / f'{sub}_{ses}_task-social_{run}*TEMP*.csv'))
            if temp_fpath:
                filtered_vicarious_flist = [str(temp_fpath[0])]
            else:
                print(f'No behavior data file found for {sub}, {ses}, {run}. Checked both standard and temporary filenames.')
                filtered_cognitive_flist = []
                cognitive_logger.error(f"An error occurred while processing the trajectory file: {sub}, {ses}, {run}")
    else:
        continue # continue to next task
else:
    cognitive_flist = glob.glob(join(beh_inputdir,'sub-*', '**','task-social', '**', f'*{task_name}*.csv'), recursive=True)
    filtered_cognitive_flist = [file for file in cognitive_flist if "sub-0001" not in file]



for cognitive_fpath in sorted(filtered_cognitive_flist):

    # 1. create an empty dataframe to host new BIDS data _______________________
    bids_beh = pd.DataFrame(columns=[
        'onset', 'duration', 'run_type', 'trial_type','trial_index','cue', 'stimulusintensity', 
        'rating_value', 'rating_glmslabel', 'rating_value_fillna', 
        'rating_glmslabel_fillna','rating_mouseonset','rating_mousedur',
        'stim_file', 
        'pain_onset_ttl1', 'pain_onset_ttl2', 'pain_onset_ttl3', 'pain_onset_ttl4', 'pain_stimulus_delivery_success',
        'cognitive_correct_response', 'cognitive_participant_response', 'cognitive_response_accuracy'])

    cue = bids_beh.copy();
    expect = bids_beh.copy();
    stim = bids_beh.copy();
    outcome = bids_beh.copy();
    cognitive_logger.info(f"\n\n{cognitive_fpath}")   


    # 2. extract metadata from original behavioral file ________________________
    cognitive_fname = os.path.basename(cognitive_fpath)
    sub_bids = re.search(r'sub-\d+', cognitive_fname).group(0)
    ses_bids = re.search(r'ses-\d+', cognitive_fname).group(0)
    run_bids = re.search(r'run-\d+', cognitive_fname).group(0)
    bids_subsesrun = f"{sub_bids}_{ses_bids}_{run_bids}"
    runtype = get_task_type(bids_subsesrun, metadata_df)
    # runtype = get_task_type(args.bids_string, metadata_df)
    # runtype = re.search(r'run-\d+-(\w+?)_', cognitive_fname).group(1)

    cognitive_logger.info(f"_______ {sub_bids} {ses_bids} {run_bids} {runtype} _______")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'func')
    beh_df = pd.read_csv(cognitive_fpath)
    trigger = beh_df['param_trigger_onset'][0]

    # 3. load trajectory data and calculate ratings ____________________________
    trajectory_glob = glob.glob(join(beh_inputdir, sub_bids, 'task-social', ses_bids, f"{sub_bids}_{ses_bids}_task-social_{run_bids}_runtype-{runtype}_beh-preproc.csv"))

    if trajectory_glob:
        try:
            trajectory_fname = trajectory_glob[0]
            traj_df = pd.read_csv(trajectory_fname)

            # Step 2: Calculate degrees based on x, y coordinates
            traj_df['adjusted_expectangle_degrees'] = calc_adjusted_angle_df(
                traj_df, 'expectrating_end_x', 'expectrating_end_y', trajectory_x, trajectory_y)
            traj_df['adjusted_outcomeangle_degrees'] = calc_adjusted_angle_df(
                traj_df, 'outcomerating_end_x', 'outcomerating_end_y', trajectory_x, trajectory_y)

            # Step 3: Check if the calculated new degree matches the one in beh_df
            beh_df['event02_expect_fillna'] = beh_df['event02_expect_angle'].round(2)
            beh_df['event02_expect_fillna'].fillna(traj_df['adjusted_expectangle_degrees'].round(2), inplace=True)
            comparison_series = ((beh_df['event02_expect_angle'].round(2)) == (traj_df['adjusted_expectangle_degrees'].round(2)))
            traj_df['comparison_flag'] = ~comparison_series
            expect_overall_flag = traj_df['comparison_flag'].any()

            if expect_overall_flag:
                discrepancy_indices = traj_df[traj_df['comparison_flag']].index
                for idx in discrepancy_indices:
                    cognitive_logger.info(f"\tExpect Rating {idx}: (traj_df): {traj_df.loc[idx]['adjusted_expectangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event02_expect_fillna']}")

            beh_df['event04_outcome_fillna'] = beh_df['event04_actual_angle'].round(2)
            beh_df['event04_outcome_fillna'].fillna(traj_df['adjusted_outcomeangle_degrees'].round(2), inplace=True)
            outcome_comparison_mask = ((beh_df['event04_actual_angle'].round(2)) == (traj_df['adjusted_outcomeangle_degrees'].round(2)))
            traj_df['outcome_comparisonflag'] = ~outcome_comparison_mask
            outcome_overall_flag = traj_df['outcome_comparisonflag'].any()

            if outcome_overall_flag:
                discrepancy_indices = traj_df[traj_df['outcome_comparisonflag']].index
                for idx in discrepancy_indices:
                    cognitive_logger.info(f"\tOutcome Rating {idx} (traj_df): {traj_df.loc[idx]['adjusted_outcomeangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event04_outcome_fillna']}")
                    
        except Exception as e:
            cognitive_logger.error("An error occurred while processing the trajectory file: %s", str(e))
    else:
        if args.bids_string:
            # Step 2: Handle case where trajectory data is missing but bids_string is provided
            beh_df['event02_expect_fillna'] = 'n/a'
            beh_df['event04_outcome_fillna'] = 'n/a'
            cognitive_logger.info(f"Skipping trajectory processing for {args.bids_string} as no trajectory file exists.")
        else:
            # Step 3: Flag the issue if neither trajectory data exists nor bids_string is provided
            cognitive_logger.warning(f"No trajectory data found for {sub_bids}, {ses_bids}, {run_bids}. No BIDS string provided.")

    
    # map it to new label
    # 4. cue ___________________________________________________________________
    cue['onset'] = (beh_df['event01_cue_onset'] - trigger).round(2)
    cue['duration'] = (beh_df['ISI01_onset'] - beh_df['event01_cue_onset']).round(2)
    cue['run_type'] = task_name
    cue['trial_type'] = 'cue'
    cue['trial_index'] = beh_df.index +1
    cue['rating_value'] = "n/a"
    cue['rating_glmslabel'] = "n/a"
    cue['rating_value_fillna'] = "n/a"
    cue['rating_glmslabel_fillna'] = "n/a"
    cue['rating_mouseonset'] = "n/a"
    cue['rating_mousedur'] = "n/a"
    if (beh_df['event01_cue_type'] == beh_df['param_cue_type']).all():
        cue['cue'] = beh_df['event01_cue_type'] 
    else:
        cognitive_logger.error(f"4-1. cue parameter does not match")
        continue
    cue['stimulusintensity'] =  "n/a"
    cue['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )

    cue['pain_onset_ttl1'] = "n/a"
    cue['pain_onset_ttl2'] = "n/a"
    cue['pain_onset_ttl3'] = "n/a"
    cue['pain_onset_ttl4'] = "n/a"
    cue['pain_stimulus_delivery_success'] = "n/a"
    cue['cognitive_correct_response'] = "n/a"
    cue['cognitive_participant_response'] = "n/a"
    cue['cognitive_response_accuracy'] = "n/a"

          
    # 5. expect ________________________________________________________________
    expect['onset'] = (beh_df['event02_expect_displayonset'] - trigger).round(2)
    expect['duration'] = (beh_df['event02_expect_RT']).round(2)
    expect['run_type'] = task_name
    expect['trial_type'] = 'expectrating'
    expect['trial_index'] =  beh_df.index +1
    expect['rating_value'] =  beh_df['event02_expect_angle'].round(2)
    expect['rating_value_fillna'] = (beh_df['event02_expect_fillna']).round(2)
    expect['rating_glmslabel'] = expect['rating_value'].apply(categorize_rating)
    expect['rating_glmslabel_fillna'] = expect['rating_value_fillna'].apply(categorize_rating)
    expect['rating_mouseonset'] = (traj_df['expect_motiononset']).round(2)
    expect['rating_mousedur'] = (traj_df['expect_motiondur']).round(2)
    expect['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    expect['stimulusintensity'] = "n/a"
    expect['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )
    expect['pain_onset_ttl1'] = "n/a"
    expect['pain_onset_ttl2'] = "n/a"
    expect['pain_onset_ttl3'] = "n/a"
    expect['pain_onset_ttl4'] = "n/a"
    expect['pain_stimulus_delivery_success'] = "n/a"
    expect['cognitive_correct_response'] = "n/a"
    expect['cognitive_participant_response'] = "n/a"
    expect['cognitive_response_accuracy'] = "n/a"
    
    # 6. stim __________________________________________________________________

    stim['onset'] = (beh_df['event03_stimulus_displayonset'] - trigger).round(2)
    stim['duration'] = 5 #(beh_df['ISI03_onset'] - beh_df['event03_stimulus_displayonset']).round(2)
    stim['run_type'] = task_name
    stim['trial_type'] = 'stimulus'
    stim['trial_index'] =  beh_df.index +1
    stim['rating_value'] = "n/a" 
    stim['rating_glmslabel'] =  "n/a" 
    stim['rating_value_fillna'] = "n/a"
    stim['rating_glmslabel_fillna'] = "n/a"
    stim['rating_mouseonset'] = "n/a"
    stim['rating_mousedur'] = "n/a"
    stim['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    stim['stimulusintensity'] =  beh_df['event03_stimulus_type']
    stim['stim_file'] = f'task-social/stim/runtype-{task_name}/' + beh_df['event03_C_stim_filename'] 

    stim['pain_onset_ttl1'] = "n/a"
    stim['pain_onset_ttl2'] = "n/a"
    stim['pain_onset_ttl3'] = "n/a"
    stim['pain_onset_ttl4'] = "n/a"
    stim['pain_stimulus_delivery_success'] = "n/a"    
    stim['cognitive_correct_response'] = beh_df['event03_C_stim_match']
    stim['cognitive_participant_response'] = beh_df['event03_stimulusC_responsekeyname'].map({'right':'same', 'left':'diff'})
    stim['cognitive_response_accuracy'] = stim['cognitive_correct_response'] == stim['cognitive_participant_response']


    # outcome __________________________________________________________________
    outcome['onset'] = (beh_df['event04_actual_displayonset'] - trigger).round(2)
    outcome['duration'] = beh_df['event04_actual_RT'].round(2)
    outcome['run_type'] = task_name
    outcome['trial_type'] = 'outcomerating'
    outcome['trial_index'] =  beh_df.index +1
    outcome['rating_value'] =  (beh_df['event04_actual_angle']).round(2)
    outcome['rating_value_fillna'] = beh_df['event04_outcome_fillna']
    outcome['rating_glmslabel'] = outcome['rating_value'].apply(categorize_rating)
    outcome['rating_glmslabel_fillna'] = outcome['rating_value_fillna'].apply(categorize_rating)
    outcome['rating_mouseonset'] = (traj_df['outcome_motiononset']).round(2)
    outcome['rating_mousedur'] = (traj_df['outcome_motiondur']).round(2)
    outcome['cue'] = beh_df['event01_cue_type'] 
    outcome['stimulusintensity'] =  beh_df['event03_stimulus_type']
    outcome['stim_file'] = 'task-social/outcomerating/task-cognitive_scale.png'
    outcome['pain_onset_ttl1'] = "n/a"
    outcome['pain_onset_ttl2'] = "n/a"
    outcome['pain_onset_ttl3'] = "n/a"
    outcome['pain_onset_ttl4'] = "n/a"
    outcome['pain_stimulus_delivery_success'] = "n/a"  
    outcome['cognitive_correct_response'] = "n/a"
    outcome['cognitive_participant_response'] = "n/a"
    outcome['cognitive_response_accuracy'] = "n/a"


    events = pd.concat([cue, expect, stim, outcome], ignore_index=True)
    events_sorted = events.sort_values(by='onset')
    events_sorted.fillna('n/a', inplace=True)
    if os.path.exists(beh_savedir) and os.path.isdir(beh_savedir):
        events_sorted.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-social_acq-mb8_{run_bids}_events.tsv"), sep='\t', index=False)
    else:
        cognitive_logger.critical(f"WARNING: The directory {beh_savedir} does not exist.")
    
    # extract bids info and save as new file



# %% ---------------------------------------------------------------------------
#                           2. Pain BIDSify
# ------------------------------------------------------------------------------
task_name = 'pain'

pain_info_logger = setup_logger('pain_info', 'task-social_pain_info.log', level=logging.INFO)
pain_warning_logger = setup_logger('pain_warning', 'task-social_pain_warning.log', level=logging.WARNING)


if args.bids_string is not None:
    if task_name == get_task_type(args.bids_string, metadata_df): # and task_name in args.bids_string:
        fname = Path(bids_string).name
        sub = extract_bids(fname, 'sub')
        ses = extract_bids(fname, 'ses')
        run = extract_bids(fname, 'run')

        filtered_pain_flist = glob.glob(str(Path(beh_inputdir) / sub / '**' / 'task-social' / '**' / f'*{args.bids_string}*.csv'), recursive=True)

        if not filtered_pain_flist:
            temp_fpath = glob.glob(str(Path(beh_inputdir) / sub / 'task-social' / ses / f'{sub}_{ses}_task-social_{run}*TEMP*.csv'))
            if temp_fpath:
                filtered_pain_flist = [str(temp_fpath[0])]
            else:
                print(f'No behavior data file found for {sub}, {ses}, {run}. Checked both standard and temporary filenames.')
                filtered_pain_flist = []
                pain_warning_logger.error(f"An error occurred while processing the trajectory file: {sub}, {ses}, {run}")
else:
    pain_list = glob.glob(join(beh_inputdir,'sub-*', '**','task-social', '**', f'*{task_name}*.csv'), recursive=True)
    filtered_pain_flist = [file for file in pain_list if "sub-0001" not in file]




for pain_fpath in sorted(filtered_pain_flist):

    # 1. create an empty dataframe to host new BIDS data _______________________
    bids_beh = pd.DataFrame(columns=[
        'onset', 'duration', 'run_type', 'trial_type','trial_index','cue', 'stimulusintensity', 
        'rating_value', 'rating_glmslabel', 'rating_value_fillna', 
        'rating_glmslabel_fillna','rating_mouseonset','rating_mousedur',
        'stim_file', 
        'pain_onset_ttl1', 'pain_onset_ttl2', 'pain_onset_ttl3', 'pain_onset_ttl4', 'pain_stimulus_delivery_success',
        'cognitive_correct_response', 'cognitive_participant_response', 'cognitive_response_accuracy'])
        
    cue = bids_beh.copy();
    expect = bids_beh.copy();
    stim = bids_beh.copy();
    outcome = bids_beh.copy();
    pain_info_logger.info(f"\n\n{pain_fpath}")   


    # 2. extract metadata from original behavioral file ________________________
    pain_fname = os.path.basename(pain_fpath)
    sub_bids = re.search(r'sub-\d+', pain_fname).group(0)
    ses_bids = re.search(r'ses-\d+', pain_fname).group(0)
    run_bids = re.search(r'run-\d+', pain_fname).group(0)
    bids_subsesrun = f"{sub_bids}_{ses_bids}_{run_bids}"
    runtype = get_task_type(bids_subsesrun, metadata_df)
    # runtype = re.search(r'run-\d+-(\w+?)_', pain_fname).group(1)

    pain_info_logger.info(f"_______ {sub_bids} {ses_bids} {run_bids} {runtype} _______")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'func')
    beh_df = pd.read_csv(pain_fpath)
    trigger = beh_df['param_trigger_onset'][0]

    # 3. load trajectory data and calculate ratings ____________________________
    trajectory_glob = glob.glob(join(beh_inputdir, sub_bids, 'task-social', ses_bids, 
                                     f"{sub_bids}_{ses_bids}_task-social_{run_bids}_runtype-{runtype}_beh-preproc.csv"))

    try:
        # Check if trajectory file exists
        if trajectory_glob:
            trajectory_fname = trajectory_glob[0]
            traj_df = pd.read_csv(trajectory_fname)
        else:
            # If trajectory_glob is empty, raise a custom exception
            raise FileNotFoundError("Trajectory preproc DOES NOT EXIST")
            
    except FileNotFoundError as e:
        # Log the specific file not found error and continue
        pain_warning_logger.warning(str(e))
        pain_warning_logger.warning("Skipping processing due to missing trajectory file.")
        continue 
    except Exception as e:
        # Log any other exceptions that might occur and continue
        pain_warning_logger.error("An error occurred while processing the trajectory file: %s", str(e))
        continue

    # If the trajectory file was successfully loaded, proceed with calculations
    if 'traj_df' in locals():
        # 3-1. Calculate degrees based on x, y coordinates
        traj_df['adjusted_expectangle_degrees'] = calc_adjusted_angle_df(
            traj_df, 'expectrating_end_x', 'expectrating_end_y', trajectory_x, trajectory_y)
        traj_df['adjusted_outcomeangle_degrees'] = calc_adjusted_angle_df(
            traj_df, 'outcomerating_end_x', 'outcomerating_end_y', trajectory_x, trajectory_y)

        # 3-3. Check if the calculated new degree matches the one in beh_df
        beh_df['event02_expect_fillna'] = beh_df['event02_expect_angle'].round(2)
        beh_df['event02_expect_fillna'].fillna(traj_df['adjusted_expectangle_degrees'].round(2), inplace=True)
        comparison_series = (beh_df['event02_expect_fillna'].round(2) == traj_df['adjusted_expectangle_degrees'].round(2))
        traj_df['comparison_flag'] = ~comparison_series
        expect_overall_flag = traj_df['comparison_flag'].any()

        if expect_overall_flag:
            discrepancy_indices = traj_df[traj_df['comparison_flag']].index
            for idx in discrepancy_indices:
                pain_info_logger.info(f"\tExpect Rating {idx}: (traj_df): {traj_df.loc[idx]['adjusted_expectangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event02_expect_fillna']}")

        beh_df['event04_outcome_fillna'] = beh_df['event04_actual_angle'].round(2)
        beh_df['event04_outcome_fillna'].fillna(traj_df['adjusted_outcomeangle_degrees'].round(2), inplace=True)
        outcome_comparison_mask = (beh_df['event04_actual_angle'].round(2) == traj_df['adjusted_outcomeangle_degrees'].round(2))
        traj_df['outcome_comparisonflag'] = ~outcome_comparison_mask
        outcome_overall_flag = traj_df['outcome_comparisonflag'].any()

        if outcome_overall_flag:
            discrepancy_indices = traj_df[traj_df['outcome_comparisonflag']].index
            for idx in discrepancy_indices:
                pain_info_logger.info(f"\tOutcome Rating {idx} (traj_df): {traj_df.loc[idx]['adjusted_outcomeangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event04_outcome_fillna']}")
    else:
        # If trajectory_df is not defined, handle the case where no trajectory processing can occur
        pain_warning_logger.warning("No trajectory data available; skipping angle calculations.")
    

    # 4. cue ___________________________________________________________________
    cue['onset'] = (beh_df['event01_cue_onset'] - trigger).round(2)
    cue['duration'] = (beh_df['ISI01_onset'] - beh_df['event01_cue_onset']).round(2)
    cue['run_type'] = task_name
    cue['trial_type'] = 'cue'
    cue['trial_index'] = beh_df.index +1
    cue['rating_value'] = "n/a"
    cue['rating_glmslabel'] = "n/a"
    cue['rating_value_fillna'] = "n/a"
    cue['rating_glmslabel_fillna'] = "n/a"
    cue['rating_mouseonset'] = "n/a"
    cue['rating_mousedur'] = "n/a"
    if (beh_df['event01_cue_type'] == beh_df['param_cue_type']).all():
        cue['cue'] = beh_df['event01_cue_type'] 
    else:
        pain_info_logger.error(f"4-1. cue parameter does not match")
        continue
    cue['stimulusintensity'] =  "n/a"
    cue['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )
    cue['pain_onset_ttl1'] = "n/a"
    cue['pain_onset_ttl2'] = "n/a"
    cue['pain_onset_ttl3'] = "n/a"
    cue['pain_onset_ttl4'] = "n/a"
    cue['pain_stimulus_delivery_success'] = "n/a"
    cue['cognitive_correct_response'] = "n/a"
    cue['cognitive_participant_response'] = "n/a"
    cue['cognitive_response_accuracy'] = "n/a"
          
    # 5. expect ________________________________________________________________
    expect['onset'] = (beh_df['event02_expect_displayonset'] - trigger).round(2)
    expect['duration'] = (beh_df['event02_expect_RT']).round(2)
    expect['run_type'] = task_name
    expect['trial_type'] = 'expectrating'
    expect['trial_index'] =  beh_df.index +1
    expect['rating_value'] =  beh_df['event02_expect_angle'].round(2)
    expect['rating_value_fillna'] = (beh_df['event02_expect_fillna']).round(2)
    expect['rating_glmslabel'] = expect['rating_value'].apply(categorize_rating)
    expect['rating_glmslabel_fillna'] = expect['rating_value_fillna'].apply(categorize_rating)
    expect['rating_mouseonset'] = (traj_df['expect_motiononset']).round(2)
    expect['rating_mousedur'] = (traj_df['expect_motiondur']).round(2)
    expect['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    expect['stimulusintensity'] =  "n/a"
    expect['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )
    # expect['stim_file'] = beh_df["event01_cue_filename"]
    expect['pain_onset_ttl1'] = "n/a"
    expect['pain_onset_ttl2'] = "n/a"
    expect['pain_onset_ttl3'] = "n/a"
    expect['pain_onset_ttl4'] = "n/a"
    expect['pain_stimulus_delivery_success'] = "n/a"
    expect['cognitive_correct_response'] = "n/a"
    expect['cognitive_participant_response'] = "n/a"
    expect['cognitive_response_accuracy'] = "n/a"
    # 6. stim __________________________________________________________________
    # 6-1. if ttl tsv exists, load in TTL duration
    ttldir = '/Volumes/spacetop_projects_cue/data/fmri/fmri01_onset/onset02_SPM'

    ttl_glob = glob.glob(join(ttldir, sub_bids, ses_bids, 
                               f"{sub_bids}_{ses_bids}_task-social_{run_bids}_runtype-{runtype}_events_ttl.tsv"), recursive=True)
    stimulus_times = {
    'low_stim': {'rampup': 3.502, 'plateau': 5.000, 'rampdown': 3.402},
    'med_stim': {'rampup': 3.758, 'plateau': 5.000, 'rampdown': 3.606},
    'high_stim': {'rampup': 4.008, 'plateau': 5.001, 'rampdown': 3.813}
}
    if ttl_glob:
        ttl_fname = ttl_glob[0]
        ttl_df = pd.read_csv(ttl_fname, sep='\t')
        # if ttl_df is missing Value in ttl4, add back in value
        for i, ttl_row in ttl_df.iterrows():
            ttl_df.loc[i] = calculate_ttl_values(stimulus_times, ttl_row, beh_df.loc[i])
    else:
        pain_info_logger.info("TTL dataframe non existent.")

        beh_df['total_stimulus_time'] = beh_df['event03_stimulus_type'].apply(lambda x: sum(stimulus_times[x].values()))
    temperature_map = {
    'high_stim': '50_celsius',
    'med_stim': '49_celsius',
    'low_stim': '48_celsius'
    }

    stim['onset'] = (beh_df['event03_stimulus_displayonset'] - trigger).round(2)
    if ttl_glob: 
        stim['duration'] = (ttl_df['TTL4'] - ttl_df['TTL1']).round(2)
    else:
        stim['duration'] = ((beh_df['event03_stimulus_displayonset']-trigger) + beh_df['total_stimulus_time']).round(2) - (beh_df['event03_stimulus_displayonset'] - trigger).round(2)

    stim['run_type'] = task_name
    stim['trial_type'] = 'stimulus'
    stim['trial_index'] =  beh_df.index +1
    stim['rating_value'] = "n/a" 
    stim['rating_glmslabel'] =  "n/a" 
    stim['rating_value_fillna'] = "n/a"
    stim['rating_glmslabel_fillna'] = "n/a"
    stim['rating_mouseonset'] = "n/a"
    stim['rating_mousedur'] = "n/a"
    stim['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    stim['stimulusintensity'] =  beh_df['event03_stimulus_type']
    stim['stim_file'] = "n/a" #beh_df['event03_stimulus_type'].map(temperature_map) 
    if ttl_glob:
        stim['pain_onset_ttl1'] = (ttl_df['TTL1']).round(2)
        stim['pain_onset_ttl2'] = (ttl_df['TTL2']).round(2)
        stim['pain_onset_ttl3'] = (ttl_df['TTL3']).round(2)
        stim['pain_onset_ttl4'] = (ttl_df['TTL4']).round(2)
    else:
        stim['pain_onset_ttl1'] = (beh_df['event03_stimulus_displayonset'] - trigger).round(2)
        stim['pain_onset_ttl2'] = (stim['pain_onset_ttl1'] + beh_df['event03_stimulus_type'].apply(lambda x: stimulus_times[x]['rampup'])).round(2)
        stim['pain_onset_ttl3'] = (stim['pain_onset_ttl2'] + beh_df['event03_stimulus_type'].apply(lambda x: stimulus_times[x]['plateau'])).round(2)
        stim['pain_onset_ttl4'] = (stim['pain_onset_ttl3'] + beh_df['event03_stimulus_type'].apply(lambda x: stimulus_times[x]['rampdown'])).round(2)
    stim['pain_stimulus_delivery_success'] = beh_df['event03_stimulus_P_trigger'].apply(lambda x: "success" if x == "Command Recieved: TRIGGER_AND_Response: RESULT_OK" else "fail")
    stim['cognitive_correct_response'] = "n/a"
    stim['cognitive_participant_response'] = "n/a"
    stim['cognitive_response_accuracy'] = "n/a"


    # outcome __________________________________________________________________
    outcome['onset'] = (beh_df['event04_actual_displayonset'] - trigger).round(2)
    outcome['duration'] = beh_df['event04_actual_RT'].round(2)
    outcome['run_type'] = task_name
    outcome['trial_type'] = 'outcomerating'
    outcome['trial_index'] =  beh_df.index +1
    outcome['rating_value'] =  beh_df['event04_actual_angle'].round(2)
    outcome['rating_value_fillna'] = (beh_df['event04_outcome_fillna']).round(2)
    outcome['rating_glmslabel'] = outcome['rating_value'].apply(categorize_rating)
    outcome['rating_glmslabel_fillna'] = outcome['rating_value_fillna'].apply(categorize_rating)
    outcome['rating_mouseonset'] = (traj_df['outcome_motiononset']).round(2)
    outcome['rating_mousedur'] = (traj_df['outcome_motiondur']).round(2)

    outcome['cue'] = beh_df['event01_cue_type'] 
    outcome['stimulusintensity'] =  beh_df['event03_stimulus_type']
    outcome['stim_file'] = 'task-social/outcomerating/task-pain_scale.png'
    outcome['pain_onset_ttl1'] = "n/a"
    outcome['pain_onset_ttl2'] = "n/a"
    outcome['pain_onset_ttl3'] = "n/a"
    outcome['pain_onset_ttl4'] = "n/a"
    outcome['pain_stimulus_delivery_success'] = beh_df['event03_stimulus_P_trigger'].apply(lambda x: "success" if x == "Command Recieved: TRIGGER_AND_Response: RESULT_OK" else "fail")
    outcome['cognitive_correct_response'] = "n/a"
    outcome['cognitive_participant_response'] = "n/a"
    outcome['cognitive_response_accuracy'] = "n/a"

    events = pd.concat([cue, expect, stim, outcome], ignore_index=True)
    events_sorted = events.sort_values(by='onset')
    events_sorted.fillna('n/a', inplace=True)
    if os.path.exists(beh_savedir) and os.path.isdir(beh_savedir):
        events_sorted.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-social_acq-mb8_{run_bids}_events.tsv"), sep='\t', index=False)
    else:
        pain_warning_logger.critical(f"WARNING: The directory {beh_savedir} does not exist.")
    
    # extract bids info and save as new file

# %% ---------------------------------------------------------------------------
#                           3. Vicarious BIDSify
# ------------------------------------------------------------------------------
task_name = 'vicarious'
vicarious_logger = setup_logger('vicarious', 'task-social_vicarious.log')

if args.bids_string is not None:
    if task_name == get_task_type(args.bids_string, metadata_df):
        fname = Path(args.bids_string).name
        sub = extract_bids(fname, 'sub')
        ses = extract_bids(fname, 'ses')
        run = extract_bids(fname, 'run')
        # filtered_cognitive_flist = glob.glob(join(beh_inputdir, sub,  '**','task-social', '**', f'*{bids_string}*.csv'), recursive=True)
        filtered_vicarious_flist = glob.glob(str(Path(beh_inputdir) / sub / '**' / 'task-social' / '**' / f'*{args.bids_string}*.csv'), recursive=True)

        if not filtered_vicarious_flist:
            temp_fpath = glob.glob(str(Path(beh_inputdir) / sub / 'task-social' / ses / f'{sub}_{ses}_task-social_{run}*TEMP*.csv'))
            if temp_fpath:
                filtered_vicarious_flist = [temp_fpath[0]]   # Get the first matching file
            else:
                print(f'No behavior data file found for {sub}, {ses}, {run}. Checked both standard and temporary filenames.')
                filtered_vicarious_flist = []
                vicarious_logger.error(f"No behavior data file found for {sub}, {ses}, {run}. Checked both standard and temporary filenames.")
else:
    vicarious_flist = glob.glob(join(beh_inputdir,'sub-*', '**','task-social', '**', f'*{task_name}*.csv'), recursive=True)
    filtered_vicarious_flist = [file for file in vicarious_flist if "sub-0001" not in file]

for vicarious_fpath in sorted(filtered_vicarious_flist):

    # 1. create an empty dataframe to host new BIDS data _______________________
    bids_beh = pd.DataFrame(columns=[
        'onset', 'duration', 'run_type', 'trial_type','trial_index','cue', 'stimulusintensity', 
        'rating_value', 'rating_glmslabel', 'rating_value_fillna', 
        'rating_glmslabel_fillna','rating_mouseonset','rating_mousedur',
        'stim_file', 
        'pain_onset_ttl1', 'pain_onset_ttl2', 'pain_onset_ttl3', 'pain_onset_ttl4', 'pain_stimulus_delivery_success',
        'cognitive_correct_response', 'cognitive_participant_response', 'cognitive_response_accuracy'])
    cue = bids_beh.copy();
    expect = bids_beh.copy();
    stim = bids_beh.copy();
    outcome = bids_beh.copy();
    vicarious_logger.info(f"\n\n{vicarious_fpath}")   
    # 2. extract metadata from original behavioral file ________________________
    vicarious_fname = os.path.basename(vicarious_fpath)
    sub_bids = re.search(r'sub-\d+', vicarious_fname).group(0)
    ses_bids = re.search(r'ses-\d+', vicarious_fname).group(0)
    run_bids = re.search(r'run-\d+', vicarious_fname).group(0)
    bids_subsesrun = f"{sub_bids}_{ses_bids}_{run_bids}"
    runtype = get_task_type(bids_subsesrun, metadata_df)
    # runtype = re.search(r'run-\d+-(\w+?)_', vicarious_fname).group(1)

    vicarious_logger.info(f"_______ {sub_bids} {ses_bids} {run_bids} {runtype} _______")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'func')
    beh_df = pd.read_csv(vicarious_fpath)
    trigger = beh_df['param_trigger_onset'][0]

    # 3. load trajectory data and calculate ratings ____________________________
    trajectory_glob = glob.glob(join(beh_inputdir, sub_bids, 'task-social', ses_bids, f"{sub_bids}_{ses_bids}_task-social_{run_bids}_runtype-{runtype}_beh-preproc.csv"))
    
    if trajectory_glob:
        try:
            trajectory_fname = trajectory_glob[0]
            traj_df = pd.read_csv(trajectory_fname)

            # Step 2: Calculate degrees based on x, y coordinates
            traj_df['adjusted_expectangle_degrees'] = calc_adjusted_angle_df(
                traj_df, 'expectrating_end_x', 'expectrating_end_y', trajectory_x, trajectory_y)
            traj_df['adjusted_outcomeangle_degrees'] = calc_adjusted_angle_df(
                traj_df, 'outcomerating_end_x', 'outcomerating_end_y', trajectory_x, trajectory_y)

            # Step 3: Check if the calculated new degree matches the one in beh_df
            beh_df['event02_expect_fillna'] = beh_df['event02_expect_angle'].round(2)
            beh_df['event02_expect_fillna'].fillna(traj_df['adjusted_expectangle_degrees'].round(2), inplace=True)
            comparison_series = ((beh_df['event02_expect_angle'].round(2)) == (traj_df['adjusted_expectangle_degrees'].round(2)))
            traj_df['comparison_flag'] = ~comparison_series
            expect_overall_flag = traj_df['comparison_flag'].any()

            if expect_overall_flag:
                discrepancy_indices = traj_df[traj_df['comparison_flag']].index
                for idx in discrepancy_indices:
                    vicarious_logger.info(f"\tExpect Rating {idx}: (traj_df): {traj_df.loc[idx]['adjusted_expectangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event02_expect_fillna']}")

            beh_df['event04_outcome_fillna'] = beh_df['event04_actual_angle'].round(2)
            beh_df['event04_outcome_fillna'].fillna(traj_df['adjusted_outcomeangle_degrees'].round(2), inplace=True)
            outcome_comparison_mask = ((beh_df['event04_actual_angle'].round(2)) == (traj_df['adjusted_outcomeangle_degrees'].round(2)))
            traj_df['outcome_comparisonflag'] = ~outcome_comparison_mask
            outcome_overall_flag = traj_df['outcome_comparisonflag'].any()

            if outcome_overall_flag:
                discrepancy_indices = traj_df[traj_df['outcome_comparisonflag']].index
                for idx in discrepancy_indices:
                    vicarious_logger.info(f"\tOutcome Rating {idx} (traj_df): {traj_df.loc[idx]['adjusted_outcomeangle_degrees'].round(2)} \t(beh_df): {beh_df.loc[idx]['event04_outcome_fillna']}")
                    
        except Exception as e:
            vicarious_logger.error("An error occurred while processing the trajectory file: %s", str(e))
    else:
        if args.bids_string:
            # Step 2: Handle case where trajectory data is missing but bids_string is provided
            beh_df['event02_expect_fillna'] = 'n/a'
            beh_df['event04_outcome_fillna'] = 'n/a'
            vicarious_logger.info(f"Skipping trajectory processing for {args.bids_string} as no trajectory file exists.")
        else:
            # Step 3: Flag the issue if neither trajectory data exists nor bids_string is provided
            vicarious_logger.warning(f"No trajectory data found for {sub_bids}, {ses_bids}, {run_bids}. No BIDS string provided.")


    # grab the intersection raise warning if dont match
    
    # map it to new label
    # 4. cue ___________________________________________________________________
    cue['onset'] = (beh_df['event01_cue_onset'] - trigger).round(2)
    cue['duration'] = (beh_df['ISI01_onset'] - beh_df['event01_cue_onset']).round(2)
    cue['run_type'] = task_name
    cue['trial_type'] = 'cue'
    cue['trial_index'] = beh_df.index +1
    cue['rating_value'] = "n/a"
    cue['rating_glmslabel'] = "n/a"
    cue['rating_value_fillna'] = "n/a"
    cue['rating_glmslabel_fillna'] = "n/a"
    cue['rating_mouseonset'] = "n/a"
    cue['rating_mousedur'] = "n/a"
    if (beh_df['event01_cue_type'] == beh_df['param_cue_type']).all():
        cue['cue'] = beh_df['event01_cue_type'] 
    else:
        vicarious_logger.error(f"4-1. cue parameter does not match")
        continue
    cue['stimulusintensity'] =  "n/a"
    cue['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )
    cue['pain_onset_ttl1'] = "n/a"
    cue['pain_onset_ttl2'] = "n/a"
    cue['pain_onset_ttl3'] = "n/a"
    cue['pain_onset_ttl4'] = "n/a"
    cue['pain_stimulus_delivery_success'] = "n/a"
    cue['cognitive_correct_response'] = "n/a"
    cue['cognitive_participant_response'] = "n/a"
    cue['cognitive_response_accuracy'] = "n/a"
          
    # 5. expect ________________________________________________________________
    expect['onset'] = (beh_df['event02_expect_displayonset'] - trigger).round(2)
    expect['duration'] = (beh_df['event02_expect_RT']).round(2)
    expect['run_type'] = task_name
    expect['trial_type'] = 'expectrating'
    expect['trial_index'] =  beh_df.index +1

    expect['rating_value'] =  beh_df['event02_expect_angle'].round(2)
    expect['rating_value_fillna'] = (beh_df['event02_expect_fillna']).round(2)
    expect['rating_glmslabel'] = expect['rating_value'].apply(categorize_rating)
    expect['rating_glmslabel_fillna'] = expect['rating_value_fillna'].apply(categorize_rating)

    expect['rating_mouseonset'] = (traj_df['expect_motiononset']).round(2)
    expect['rating_mousedur'] = (traj_df['expect_motiondur']).round(2)
    expect['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    expect['stimulusintensity'] =  "n/a"
    expect['stim_file'] = beh_df["event01_cue_filename"].apply(
        lambda x: f'task-social/cue/runtype-{task_name}/{"sch/" if x.startswith("h") else "scl/"}' + x
    )
    expect['pain_onset_ttl1'] = "n/a"
    expect['pain_onset_ttl2'] = "n/a"
    expect['pain_onset_ttl3'] = "n/a"
    expect['pain_onset_ttl4'] = "n/a"
    expect['pain_stimulus_delivery_success'] = "n/a"
    expect['cognitive_correct_response'] = "n/a"
    expect['cognitive_participant_response'] = "n/a"
    expect['cognitive_response_accuracy'] = "n/a"    
    # 6. stim __________________________________________________________________

    stim['onset'] = (beh_df['event03_stimulus_displayonset'] - trigger).round(2)
    stim['duration'] = 5 #(beh_df['ISI03_onset'] - beh_df['event03_stimulus_displayonset']).round(2)
    stim['run_type'] = task_name
    stim['trial_type'] = 'stimulus'
    stim['trial_index'] =  beh_df.index +1
    stim['rating_value'] = "n/a" 
    stim['rating_glmslabel'] =  "n/a" 
    stim['rating_value_fillna'] = "n/a"
    stim['rating_glmslabel_fillna'] = "n/a"
    stim['rating_mouseonset'] = "n/a"
    stim['rating_mousedur'] = "n/a"
    stim['cue'] = beh_df['event01_cue_type'] # if same as param_cue_type
    stim['stimulusintensity'] =  beh_df['event03_stimulus_type']    
    stim['stim_file'] = f'task-social/stim/runtype-{task_name}/' + beh_df['event03_stimulus_V_filename'] 
    stim['pain_onset_ttl1'] = "n/a"
    stim['pain_onset_ttl2'] = "n/a"
    stim['pain_onset_ttl3'] = "n/a"
    stim['pain_onset_ttl4'] = "n/a"
    stim['pain_stimulus_delivery_success'] = "n/a"  
    stim['cognitive_correct_response'] = "n/a"
    stim['cognitive_participant_response'] = "n/a"
    stim['cognitive_response_accuracy'] = "n/a"

    # outcome __________________________________________________________________
    outcome['onset'] = (beh_df['event04_actual_displayonset'] - trigger).round(2)
    outcome['duration'] = beh_df['event04_actual_RT'].round(2)
    outcome['run_type'] = task_name
    outcome['trial_type'] = 'outcomerating'
    outcome['trial_index'] =  beh_df.index +1
    outcome['rating_value'] =  (beh_df['event04_actual_angle']).round(2)
    outcome['rating_value_fillna'] = beh_df['event04_outcome_fillna']
    outcome['rating_glmslabel'] = outcome['rating_value'].apply(categorize_rating)
    outcome['rating_glmslabel_fillna'] = outcome['rating_value_fillna'].apply(categorize_rating)
    outcome['rating_mouseonset'] = (traj_df['outcome_motiononset']).round(2)
    outcome['rating_mousedur'] = (traj_df['outcome_motiondur']).round(2)
    outcome['cue'] = beh_df['event01_cue_type'] 
    outcome['stimulusintensity'] =  beh_df['event03_stimulus_type']
    outcome['stim_file'] = f'task-social/outcomerating/task-vicarious_scale.png'
    outcome['pain_onset_ttl1'] = "n/a"
    outcome['pain_onset_ttl2'] = "n/a"
    outcome['pain_onset_ttl3'] = "n/a"
    outcome['pain_onset_ttl4'] = "n/a"
    outcome['pain_stimulus_delivery_success'] = "n/a"  
    outcome['cognitive_correct_response'] = "n/a"
    outcome['cognitive_participant_response'] = "n/a"
    outcome['cognitive_response_accuracy'] = "n/a"
    events = pd.concat([cue, expect, stim, outcome], ignore_index=True)
    events_sorted = events.sort_values(by='onset')
    events_sorted.fillna('n/a', inplace=True)
    if os.path.exists(beh_savedir) and os.path.isdir(beh_savedir):
        events_sorted.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-social_acq-mb8_{run_bids}_events.tsv"), sep='\t', index=False)
    else:
        vicarious_logger.critical(f"WARNING: The directory {beh_savedir} does not exist.")
    
    # extract bids info and save as new file


# %% HED tag
description_onset = {
    "LongName": "Onset time of event",
    "Description": "Marks the start of an ongoing event of temporal extent.",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}
description_duration = {
    "LongName": "The period of time during which an event occurs.",
    "Description": "Refers to duration of cue presentation or response time towards target item. (a) For valid_cue and invalid_cue, duration refers to the image presentation of cue. (b) For target_response, duration refers to response time to respond to target item. It is calculated as the interval between onset of button press and onset of target presentation ",
    "Units": "s",
    "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"
    } 

description_runtype = {
    "LongName": "The type of subtasks within task-social",
    "Description": "Refers to the type of subtask: [pain, vicarious, cognitive']",
    "Levels": {
        "pain": "The stimuli being delivered is thermal heat.",
        "vicarious": "The stimuli being delivered is a video with patients in pain",
        "cognitive": "The stimuli being delivered is an image with two figures; participants are prompted to mentally rotate the figures and decide whether they are same or different"
        },
    "HED": {
        "pain": "Property/Sensory-property/Sensory-attribute/Somatic-attribute/Pain",
        "vicarious": "Action/Think/Judge",
        "cognitive": "Action/Think/Discriminate"
    }
} 

description_trialtype = {
    "LongName": "Type of epochs with each trial",
    "Description": "There are four epochs in each trial: cue, expectrating, stim, outcomerating",
    "Levels": {
        "cue": "Participants passively viewed a presentation of a high or low social cue, consisting of data points that participants believed indicated other people's ratings for that stimulus presented for 1 second on screen",
        "expectrating": "Participants provided ratings of their expectations on the upcoming stimulus intensity on a gLMS scale for a total duration of 4 seconds overlaid with the cue image",
        "stim": "Participants passively received/viewed experimentally delivered stimuli for each of the mental rotation, vicarious pain, and somatic pain tasks for 5 seconds each",
        "outcomerating": "Participants provided ratings on their subjective experience of cognitive effort, vicarious pain, or somatic pain for 4 seconds"
    },
    "HED": {
        "cue": "Property/Task-property/Task-stimulus-role/Cue",
        "expectrating": "Action/Think/Encode",
        "stim": "Action/Perceive",
        "outcomerating": "Action/Think/Encode"
    }
}

description_trialindex = {
    "LongName": "Trial order",
    "Description": "Indicates the trial order. There are a total of 12 trials in each run.",
    "HED": "Property/Data-property/Data-value/Quantitative-value/Item-index/1-12"
}

description_ratingvalue = {
    "LongName": "Rating value",
    "Description": "The rating degree on a semicircle scale",
    "HED": "Property/Data-property/Data-value/Quantitative-value/Item-interval/0-180"
}

description_ratingglms = {
    "LongName": "Labels of generalized Labeled Magnitude Scale (gLMS)",
    "Description": "Labels of generalized Labeled Magnitude Scale (gLMS)",
    "Levels": {
        "No sensation": "No sensation",
        "Barely detectable": "Barely detectable",
        "Weak": "Weak",
        "Moderate": "Moderate",
        "Strong": "Strong",
        "Very Strong": "Very Strong",
        "Strongest sensation of any kind": "Strongest sensation of any kind"
    },
    "HED": "Property/Data-property/Data-marker"
}
description_ratingvalueNA = {
    "LongName": "Rating value with imputed values from mouse trajectory data",
    "Description": "Using mouse trajectory data, we extract the last degree recorded on the scale. From this, we impute degrees for cells that were originally marked n/a",
    "HED": "Property/Data-property/Data-value/Quantitative-value/Item-interval/0-180"
}
description_ratingglmsNA = {
    "LongName": "Labels of generalized Labeled Magnitude Scale (gLMS)",
    "Description": "Labels of generalized Labeled Magnitude Scale (gLMS)",
    "Levels": {
        "No sensation": "No sensation",
        "Barely detectable": "Barely detectable",
        "Weak": "Weak",
        "Moderate": "Moderate",
        "Strong": "Strong",
        "Very Strong": "Very Strong",
        "Strongest sensation of any kind": "Strongest sensation of any kind"
    },
    "HED": "Property/Data-property/Data-marker"
}
description_ratingmouseonset = {
    "LongName": "Onset time of mouse trajectory",
    "Description": "the time when the participant started moving the trackball in relation to the rating epoch",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}

description_mousedur = {
    "LongName": "The period of time during which an event occurs.",
    "Description": "Refers to duration of cue presentation or response time towards target item. (a) For valid_cue and invalid_cue, duration refers to the image presentation of cue. (b) For target_response, duration refers to response time to respond to target item. It is calculated as the interval between onset of button press and onset of target presentation ",
    "Units": "s",
    "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"

}
description_cue = {
    "LongName": "A cue to indicate level of upcoming stimulus intensity",
    "Description": "Participants passively viewed a presentation of a high or low social cue, consisting of data points that participants believed indicated other people's ratings for that stimulus presented for 1 second on screen",
    "Levels": {
        "high_cue": "Data points on the cue indicate that past participants perceived the upcoming stimulus as having high intensity",
        "low_cue": "Data points on the cue indicate that past participants perceived the upcoming stimulus as having low intensity"
    },
    "HED": {
        "high_cue": ["Property/Task-property/Task-stimulus-role/Cue", "Property/Data-property/Data-value/Categorical-value/Categorical-level-value/High"],
        "low_cue": ["Property/Task-property/Task-stimulus-role/Cue", "Property/Data-property/Data-value/Categorical-value/Categorical-level-value/Low"]
    }
}

description_stimulusintensity = {
    "LongName": "",
    "Description": "",
    "Levels": {
        "high_stim": "High intensity stimulus (pain, vicarious, cognitive task)",
        "med_stim": "Medium intensity stimulus (pain, vicarious, cognitive task)",
        "low_stim": "Low intensity stimulus (pain, vicarious, cognitive task)"
    },
    "HED":  {
        "high_stim": ["Property/Task-property/Task-event-role/Experimental-stimulus", "Property/Data-property/Data-value/Categorical-value/Categorical-level-value/High"],
        "med_stim": ["Property/Task-property/Task-event-role/Experimental-stimulus", "Property/Data-property/Data-value/Categorical-value/Categorical-level-value/Medium"], 
        "low_stim": ["Property/Task-property/Task-event-role/Experimental-stimulus", "Property/Data-property/Data-value/Categorical-value/Categorical-level-value/Low"]
    }
}

description_stimfile = {
    "LongName": "stimulus file path",
    "Description": "Represents the location of the stimulus file (such as an image, video, or audio file) presented at the given onset time.",
    "HED": "Property/Task-property/Task-event-role/Experimental-stimulus"
}
description_painonset1 = {
    "LongName": "Onset time of pain stimulus (ramp up)",
    "Description": "Marks the start of an pain stimulus trigger.",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}
description_painonset2 = {
    "LongName": "Onset time of pain stimulus (reach plateau)",
    "Description": "Marks the start of when pain stimulus reaches intended temperature and starts plateau.",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}
description_painonset3 = {
    "LongName": "Onset time of pain stimulus (ramp down)",
    "Description": "Marks the end of an pain plateau.",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}
description_painonset4 = {
    "LongName": "Onset time of pain stimulus (baseline)",
    "Description": "Marks the end of a pain stimulus trigger, returning to baseline.",
    "Units": "s",
    "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
}
description_painsuccess = {
    "LongName": "Onset time of pain stimulus (baseline)",
    "Description": "Marks the end of a pain stimulus trigger, returning to baseline.",
    "Units": "s",
    "HED": "Property/Data-property/Data-value/Categorical-value/Categorical-class-value/True"
}
description_cognitiveresponse = {
    "LongName": "Correct response for the rotated image",
    "Description": "Correct answer for whether two figures are same or different",
    "Levels": {
        "same": "The two figures are the same",
        "diff": "The two figures are different"
    },
    "HED": { 
        "same": "Action/Think/Discriminate", 
        "diff": "Action/Think/Discriminate"
        }
}
description_cognitiveparticipant = {
    "LongName": "Participant response for the rotated image",
    "Description": "Participant respond to two options -- same or diff -- to the two figures on screen",
    "Levels": {
        "same": "The two figures are the same",
        "diff": "The two figures are different"
    },
    "HED": { 
        "same": "Action/Think/Discriminate", 
        "diff": "Action/Think/Discriminate"
        }
}
description_cognitiveaccuracy = {
    "LongName": "Mental rotation task accuracy",
    "Description": "Marks the end of a pain stimulus trigger, returning to baseline.",
    "Levels": {
        "True": "Correct response in regards to image (correctly identified as old or new)",
        "False": "Incorrect response in regards to image (incorrectly identified as old or new)"
    },
    "HED": { 
        "True": "Property/Task-property/Task-action-type/Correct-action", 
        "False": "Property/Task-property/Task-action-type/Incorrect-action"
        }
}

events_json = {"onset": description_onset,
                "duration": description_duration, 
                "run_type": description_runtype, 
                "trial_type": description_trialtype,
                "trial_index": description_trialindex,
                "cue": description_cue, 
                "stimulusintensity": description_stimulusintensity, 
                "rating_value":description_ratingvalue,
                "rating_glmslabel": description_ratingglms,
                "rating_value_fillna": description_ratingvalueNA, 
                "rating_glmslabel_fillna": description_ratingglmsNA, 
                "rating_mouseonset": description_ratingmouseonset, 
                "rating_mousedur": description_mousedur, 
                "stim_file": description_stimfile, 
                "pain_onset_ttl1": description_painonset1, 
                "pain_onset_ttl2": description_painonset2, 
                "pain_onset_ttl3": description_painonset3, 
                "pain_onset_ttl4": description_painonset4, 
                "pain_stimulus_delivery_success": description_painsuccess, 
                "cognitive_correct_response": description_cognitiveresponse, 
                "cognitive_participant_response": description_cognitiveparticipant, 
                "cognitive_response_accuracy": description_cognitiveaccuracy
                }  


json_fname = join(bids_dir, f"task-social_events.json")
with open(json_fname, 'w') as file:
    json.dump(events_json, file, indent=4)
