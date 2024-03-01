#!/usr/bin/env python
"""convert behavioral file into event lists and singletrial format

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
__author__ = "Heejung Jung"
__copyright__ = "Spatial Topology Project"
__credits__ = ["Heejung"] # people who reported bug fixes, made suggestions, etc. but did not actually write the code.
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Heejung Jung"
__email__ = "heejung.jung@colorado.edu"
__status__ = "Development" 

# argparse

bids_dir = '/Users/h/Documents/projects_local/1076_spacetop' # the top directory of datalad
code_dir = '/Users/h/Documents/projects_local/1076_spacetop/code' # where this code live
source_dir = '/Users/h/Documents/projects_local/1076_spacetop/sourcedata'# where the source behavioral directory lives
beh_inputdir = join(source_dir, 'd_beh')


# %% -----------------------------------------------
#                       saxe
# -------------------------------------------------

# * add argparse: sub, 
# * add directories: main_dir, beh_dir, fmri_dir
# * get onset by subtracting trigger
# * get epoch of interest: 
# 'event02_filetype', 'event02_story_onset',
# 'event03_question_onset', 'event04_response_onset',
# 'event04_RT','accuracy'


task_name = "tomsaxe"
current_path = Path.cwd()
main_dir = current_path.parent.parent #'/Users/h/Documents/projects_local/spacetop_fractional_analysis'
# beh_inputdir = join(main_dir, 'data', 'beh', 'beh02_preproc')
# %%
saxe_flist = glob.glob(join(beh_inputdir, '**', f'*{task_name}*.csv'), recursive=True)
filtered_saxe_flist = [file for file in saxe_flist if "sub-0001" not in file]

for saxe_fpath in sorted(filtered_saxe_flist):
    
    saxe_fname = os.path.basename(saxe_fpath)
    sub_bids = re.search(r'sub-\d+', saxe_fname).group(0)
    ses_bids = re.search(r'ses-\d+', saxe_fname).group(0)
    run_bids = re.search(r'run-\d+', saxe_fname).group(0)
    task_name = re.search(r'run-\d+-(\w+)_beh', saxe_fname).group(1)
        # beh_fpath = join(beh_inputdir, sub, f"{sub}_{ses}_task-fractional_{run_bids}-tomsaxe_beh.csv")
    print(f"{sub_bids} {ses_bids} {run_bids} {task_name}")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'beh')
    beh_df = pd.read_csv(saxe_fpath)
    beh_df['response_accuracy'] = beh_df['accuracy'].replace({1: 'correct', 0: 'incorrect'})

    subset_beh = beh_df[['event02_filetype', 'event02_story_onset','event03_question_onset', 'event04_response_onset','event04_RT','response_accuracy', 'event02_filename']]

    # belief, photo, rating, accuracy as covariate
    subset_belief = pd.DataFrame(); subset_photo = pd.DataFrame(); subset_beliefrating = pd.DataFrame(); subset_photorating = pd.DataFrame()

    subset_belief['onset'] = subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'event02_story_onset']
    subset_belief['duration'] = 11
    subset_belief['event_type'] = "stimulus" #'false_belief'
    subset_belief['value'] = "falsebelief"
    subset_belief['response_accuracy'] = "n/a" #subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'accuracy']
    subset_belief['stim_file'] = task_name + '/' + subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'event02_filename']

    subset_photo['onset'] = subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'event02_story_onset']
    subset_photo['duration'] = 11
    subset_photo['event_type'] = "stimulus"
    subset_photo['value'] = "falsephoto"
    subset_photo['response_accuracy'] = "n/a" #subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'accuracy']
    subset_photo['stim_file'] =  task_name + '/' + subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'event02_filename']

    subset_beliefrating['onset'] = subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'event03_question_onset'] #subset_beh.event03_question_onset
    subset_beliefrating['duration'] = subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'event04_RT'] #subset_beh.event04_RT
    subset_beliefrating['event_type'] = "response" #'rating_falsebelief' #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    subset_beliefrating['value'] = "falsebelief" #subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'response_accuracy'] + "_response_falsebelief"
    subset_beliefrating['response_accuracy'] = subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'response_accuracy']
    subset_beliefrating['stim_file'] = task_name + '/' + subset_beh.loc[subset_beh.event02_filetype == 'false_belief', 'event02_filename'].str.replace('story', 'question')

    subset_photorating['onset'] = subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'event03_question_onset']
    subset_photorating['duration'] = subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'event04_RT']
    subset_photorating['event_type'] = "response" #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    subset_photorating['value'] = "falsephoto" #subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'response_accuracy'] + "_response_falsephoto"
    subset_photorating['response_accuracy'] = subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'response_accuracy'] #subset_beh.accuracy #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    subset_photorating['stim_file'] = task_name + '/' + subset_beh.loc[subset_beh.event02_filetype == 'false_photo', 'event02_filename'].str.replace('story', 'question')
    # concatenate above dataframes and save in new folder
    events = pd.concat([subset_belief, subset_photo, subset_beliefrating, subset_photorating], ignore_index=True)
    events_sorted = events.sort_values(by='onset')

    # beh_savedir = join(main_dir, 'data' , 'beh', 'beh03_bids', sub_bids)
    Path(beh_savedir).mkdir( parents=True, exist_ok=True )
    # extract bids info and save as new file
    events.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.tsv"), sep='\t', index=False)

    # create json files

    description_onset = {
        "LongName": "Onset time of event",
        "Description": "Marks the start of an ongoing event of temporal extent.",
        "Units": "s",
        "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
    }
    description_duration = {
        "LongName": "The period of time during which an event occurs. Refers to Image duration or response time after stimulus depending on event_type",
        "Description": "a. For falsebelief and falsephoto trial types, duration refers to the image presentations of falsebelief and falsephoto stories. b. For rating_falsebelief and rating_falsephoto, duration refers to the response time to answer true false questions, followed by falsebelief or flasephoto stimulu",
        "Units": "s",
        "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"} #[x]

    description_eventtype = {
        "LongName": "Event category",
        "Description": "Categorical variable of event types within run",
        "Levels": {
            "stimulus": "A text-based story is presented on screen",
            "response": "A question related to text-based story is presented; Participants are prompted to respond True or False to presented question"
            },
        "HED": {
            "stimulus": "Sensory-event, Experimental-stimulus, Visual-presentation, Item/Language-item/Textblock",
            "response": "Property/Task-property/Task-event-role/Participant-response, Action/Think/Judge"
            }
    } # [x]

    description_value = {
        "LongName": "Stimulus and response type falls under false belief or false photo",
        "Description":"Trial type is either a false belief narrative or false photo narrative",
        "Levels": {"falsebelief": "A story where participant is prompted to represent outdated beliefs of an agents’ latent thoughts ('false belief'), e.g. Tom turned left on the main road as usual to get to work, but we know that very road is under construction.",
                "falsephoto": "A story where participant is prompted to represent a false or outdated content from a photo, e.g. an old photograph that depicts the Berlin wall that no longer accurately describes the current state"
                },
        "HED": {"falsebelief": "Action/Perform/Read",
                "falsephoto": "Action/Perform/Read"} # Q. Is this the right HED?
    }
    description_accuracy = {
        "LongName": "Correct or Incorrect response",
        "Description": "Correct or Incorrect response in regards to question presented on screen; Options are True or False, presented on screen, underneath question. Participants are promted to respond with MR-compatible button box",
        "Levels": {
            "correct": "Correct response in regards to question",
            "incorrect": "Incorrect response in regards to question"
        },
        "HED": { 
            "correct": "Property/Task-property/Task-action-type/Correct-action", 
            "incorrect": "Property/Task-property/Task-action-type/Incorrect-action"
            }
    } #[x]

    description_stimfile =  {
            "LongName": "Stimulus filename which is presented on screen",
            "Description": "Given text file encompasses test that is displayed on screen. Filename is designated as {digit}{belief_or_photo}_{story_or_question}.txt. Digit indicates the number of stimulus that was presented. b or p indicates whether stimulus was false belief or false photo event. Story or question indicates which event was presented on screen.",
            "HED": "(Textblock, Pathname/#)"
        }


    events_json = {"onset": description_onset,
                    "duration": description_duration, 
                    "event_type": description_eventtype, 
                    "value":description_value,
                    "response_accuracy":description_accuracy,
                    "stim_file": description_stimfile}  
    # TODO: change fname to be subject specific
    json_fname = join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.json")
    with open(json_fname, 'w') as file:
        json.dump(events_json, file, indent=4)

# %% -----------------------------------------------
#                       posner
# -------------------------------------------------
task_name = "posner"
current_path = Path.cwd()
main_dir = current_path.parent.parent #'/Users/h/Documents/projects_local/spacetop_fractional_analysis'
# beh_inputdir = join(main_dir, 'data', 'beh', 'beh02_preproc')

posner_flist = glob.glob(join(beh_inputdir, '**', f'*{task_name}*.csv'), recursive=True)

for posner_fpath in sorted(posner_flist):
    posner_fname = os.path.basename(posner_fpath)
    sub_bids = re.search(r'sub-\d+', posner_fname).group(0)
    ses_bids = re.search(r'ses-\d+', posner_fname).group(0)
    run_bids = re.search(r'run-\d+', posner_fname).group(0)
    task_name = re.search(r'run-\d+-(\w+)_beh', posner_fname).group(1)
    print(f"{sub_bids} {ses_bids} {run_bids} {task_name}")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'beh')
        # beh_fpath = join(beh_inputdir, sub, f"{sub}_{ses}_task-fractional_{run_bids}-tomsaxe_beh.csv")
    beh_df = pd.read_csv(posner_fpath)
    beh_df['index'] = beh_df.index + 1
    beh_df['response_accuracy'] = beh_df['accuracy'].map({1: 'correct', 0: 'incorrect'})
    subset_beh = beh_df[['index','param_valid_type', 'event02_cue_onset','event03_target_onset', 'event04_response_onset','event04_RT','response_accuracy', 'param_cue_location', 'param_target_location', 'event04_response_keyname']]

    # belief, photo, rating, accuracy as covariate
    subset_valid = pd.DataFrame(); subset_invalid = pd.DataFrame(); subset_target = pd.DataFrame(); 

    subset_valid['onset'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'event02_cue_onset']
    subset_valid['duration'] = 0.2
    subset_valid['event_type'] = "valid_cue"
    subset_valid['response_accuracy'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'response_accuracy']
    subset_valid['cue_location'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'param_cue_location']
    subset_valid['target_location'] = "n/a" #subset_beh.loc[subset_beh.param_valid_type == 'valid', 'param_target_location']
    subset_valid['button_press'] = "n/a" #subset_beh.loc[subset_beh.param_valid_type == 'valid', 'event04_response_keyname']
    subset_valid['trial_index'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'index']

    subset_invalid['onset'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'event02_cue_onset']
    subset_invalid['duration'] = 0.2
    subset_invalid['event_type'] = "invalid_cue"
    subset_invalid['response_accuracy'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'response_accuracy']
    subset_invalid['cue_location'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'param_cue_location']
    subset_invalid['target_location'] = "n/a" #subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'param_target_location']
    subset_invalid['button_press'] = "n/a" #subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'event04_response_keyname']
    subset_invalid['trial_index'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'index']


    subset_target['onset'] = subset_beh.event03_target_onset
    subset_target['duration'] = subset_beh.event04_RT
    subset_target['event_type'] = "target_response" #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    # subset_target['response_accuracy'] = subset_beh.accuracy #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    subset_target['response_accuracy'] = subset_beh.response_accuracy
    subset_target['cue_location'] = subset_beh.param_cue_location
    subset_target['target_location'] = subset_beh.param_target_location
    subset_target['button_press'] = subset_beh.event04_response_keyname
    subset_target['trial_index'] = subset_beh.index + 1


    # concatenate above dataframes and save in new folder
    posner_events = pd.concat([subset_valid, subset_invalid, subset_target], ignore_index=True)
    posner_events_sorted = posner_events.sort_values(by='onset')
    # beh_savedir = join(main_dir, 'data' , 'beh', 'beh03_bids', sub_bids)
    Path(beh_savedir).mkdir( parents=True, exist_ok=True )
    # extract bids info and save as new file
    posner_events_sorted.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.tsv"), sep='\t', index=False)

    # create json files

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
        "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"} #[x]

    description_eventtype = {
        "LongName": "Event category",
        "Description": "Categorical variable of event types within run.",
        "Levels": {
            "valid_cue": "A cue that accurately predicts the location of the upcoming target stimulus.",
            "invalid_cue": "A cue that inaccurately predicts the location of the upcoming target stimulus.",
            "target_response": "The stimulus that participants are instructed to respond to, following the presentation of a cue. Participants are prompted to respond left or right as to where the target location is."
            },
        "HED": {
            "valid_cue": "Property/Task-property/Task-stimulus-role/Cue, Property/Data-property/Data-value/Categorical-value/Categorical-class-value/valid",
            "invalid_cue": "Property/Task-property/Task-stimulus-role/Cue, Property/Data-property/Data-value/Categorical-value/Categorical-class-value/invalid",
            "target_response": "Property/Task-property/Task-stimulus-role/Target, Property/Task-property/Task-event-role/Participant-response"
            }
    } # [x]

    description_accuracy = {
        "LongName": "Correct or Incorrect response",
        "Description": "Correct or Incorrect response in regards to question presented on screen; Options are True or False, presented on screen, underneath question. Participants are promted to respond with MR-compatible button box.",
        "Levels": {
            "correct": "Correct response in regards to question.",
            "incorrect": "Incorrect response in regards to question."
        },
        "HED": { 
            "correct": "Property/Task-property/Task-action-type/Correct-action", 
            "incorrect": "Property/Task-property/Task-action-type/Incorrect-action"
            }
    } #[x]

    # description_stimfile =  {
    #         "LongName": "Stimulus filename which is presented on screen",
    #         "Description": "Given text file encompasses test that is displayed on screen. Filename is designated as {digit}{belief_or_photo}_{story_or_question}.txt. Digit indicates the number of stimulus that was presented. b or p indicates whether stimulus was false belief or false photo event. Story or question indicates which event was presented on screen.",
    #         "HED": "(Textblock, Pathname/#)"
    #     }

    description_cuelocation = {
        "LongName": "Location of Cue",
        "Description": "The cue was presented as a clearly defined green box. Prior to the cue presentation, two boxes were presented on screen with a gray outline. The green colored cue selectively highlights either the right or left box on the display screen.", 
        "Levels": {
            "right": "The cue, highlighted in green, is presented on the right side of the screen.",
            "left": "The cue, highlighted in green, is presented on the left side of the screen."
        },
        "HED": { 
            "right": "Relation/Spatial-relation/Right-side-of", 
            "left": "Relation/Spatial-relation/Left-side-of"
            }
    } #[x]

    description_targetlocation = {
        "LongName": "Location of Target",
        "Description": "The target was presented as a clearly defined green circle, either appearing inside the right or left box, already present on screen.", 
        "Levels": {
            "right": "The target, a green circle, is presented inside the right box of the screen.",
            "left":  "The target, a green circle, is presented inside the left box of the screen.",
        },
        "HED": { 
            "right": "Relation/Spatial-relation/Right-side-of", 
            "left": "Relation/Spatial-relation/Left-side-of"
            }
    } 

    description_buttonpress = {
        "LongName": "Button Press",
        "Description": "Participant response in relation to target location.", 
        "Levels": {
            "right": "Participant pressed right, indicating that target was presented on the right side of the screen.",
            "left": "Participant pressed left, indicating thattarget was presented on the left side of the screen."
        },
        "HED": { 
            "right": "Action/Move/Move-body-part/Move-upper-extremity/Press, Relation/Spatial-relation/Right-side-of", 
            "left": "Action/Move/Move-body-part/Move-upper-extremity/Press, Relation/Spatial-relation/Left-side-of"
            }
    } 

    description_trialind = {
        "LongName": "Trial Index",
        "Description": "Index of trial, which encompasses cue and target events", 
        "HED": "Property/Data-property/Data-value/Quantitative-value/Item-index"
    } 
    events_json = {"onset": description_onset,
                   "duration": description_duration, 
                   "event_type": description_eventtype, 
                   # "value":description_value,
                   "response_accuracy":description_accuracy,
                   # "stim_file": description_stimfile
                   "cue_location":description_cuelocation,
                   "target_location":description_targetlocation,
                   "button_press":description_buttonpress,
                   "trial_index":description_trialind,
                   }  
    # TODO: change fname to be subject specific
    json_fname = join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.json")
    with open(json_fname, 'w') as file:
        json.dump(events_json, file, indent=4)

# %% -----------------------------------------------
#                       posner 2
# -------------------------------------------------
task_name = "posner"
current_path = Path.cwd()
main_dir = current_path.parent.parent #'/Users/h/Documents/projects_local/spacetop_fractional_analysis'
# beh_inputdir = join(main_dir, 'data', 'beh', 'beh02_preproc')

posner_flist = glob.glob(join(beh_inputdir, '**', f'*{task_name}*.csv'), recursive=True)
# %%
for posner_fpath in sorted(posner_flist):
    posner_fname = os.path.basename(posner_fpath)
    sub_bids = re.search(r'sub-\d+', posner_fname).group(0)
    ses_bids = re.search(r'ses-\d+', posner_fname).group(0)
    run_bids = re.search(r'run-\d+', posner_fname).group(0)
    task_name = re.search(r'run-\d+-(\w+)_beh', posner_fname).group(1)
    print(f"{sub_bids} {ses_bids} {run_bids} {task_name}")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'beh')
        # beh_fpath = join(beh_inputdir, sub, f"{sub}_{ses}_task-fractional_{run_bids}-tomsaxe_beh.csv")
    beh_df = pd.read_csv(posner_fpath)
    subset_beh = beh_df[['param_valid_type', 'event02_cue_onset','event03_target_onset', 'event04_response_onset','event04_RT','accuracy']]

    # belief, photo, rating, accuracy as covariate
    subset_valid = pd.DataFrame(); subset_invalid = pd.DataFrame(); subset_target = pd.DataFrame(); 

    subset_valid['onset'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'event02_cue_onset']
    subset_valid['duration'] = 0.2 + subset_beh.loc[subset_beh.param_valid_type == 'valid', 'event04_RT']
    subset_valid['event_type'] = 'cue_valid'
    subset_valid['pmod_accuracy'] = subset_beh.loc[subset_beh.param_valid_type == 'valid', 'accuracy']

    subset_invalid['onset'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'event02_cue_onset']
    subset_invalid['duration'] = 0.2 + subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'event04_RT']
    subset_invalid['event_type'] = 'cue_invalid'
    subset_invalid['pmod_accuracy'] = subset_beh.loc[subset_beh.param_valid_type == 'invalid', 'accuracy']

    # subset_target['onset'] = subset_beh.event03_target_onset
    # subset_target['duration'] = subset_beh.event04_RT
    # subset_target['event_type'] = 'target_response' #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')
    # subset_target['pmod_accuracy'] = subset_beh.accuracy #'rating_' + subset_beh['event02_filetype'].str.replace('_', '')

    # concatenate above dataframes and save in new folder
    events = pd.concat([subset_valid, subset_invalid, subset_target], ignore_index=True)


    Path(beh_savedir).mkdir( parents=True, exist_ok=True )
    # extract bids info and save as new file
    events.to_csv(join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.tsv"), sep='\t', index=False)



# %% -----------------------------------------------
#                      memory
# -------------------------------------------------
"""
<< memory_beh.csv >>
    * extract trigger onset 
    * (we'll use this to subtract from all onsets)

<< study01_beh.csv >>
event_type: 
    * study_dummy (event02_dummy_stimuli_type)
    * 'study' (event02_dummy_stimuli_type)
image_fname
    * [event02_image_filename]
onset:
    * [RAW_event02_image_onset] [event02_image_onset]
duration
    * [RAW_event03_isi_onset] - [RAW_event02_image_onset]

<< test01_beh.csv >>
event_type
    * 'test'
image_fname
    * [event02_image_filename]
onset
    * [event02_image_onset]
duration
    * [event03_RT]
pmod_accuracy
    * [event03_response_key] (fill NA with 0)
    * compare with [param_answer]

"""
task_name = "memory"
current_path = Path.cwd()
# main_dir = current_path.parent.parent #
# beh_inputdir = join(main_dir, 'data', 'beh', 'beh02_preproc')

# memory_flist = glob.glob(join(beh_inputdir, '**', f'*{task_name}*.csv'), recursive=True)
memory_flist = sorted(glob.glob(join(beh_inputdir, '**', f'*{task_name}_beh.csv'), recursive=True))

for memory_fpath in memory_flist:
    memory_fname = os.path.basename(memory_fpath)
    sub_bids = re.search(r'sub-\d+', memory_fname).group(0)
    ses_bids = re.search(r'ses-\d+', memory_fname).group(0)
    run_bids = re.search(r'run-\d+', memory_fname).group(0)
    task_name = re.search(r'run-\d+-(\w+)_beh', memory_fname).group(1)
    print(f"{sub_bids} {ses_bids} {run_bids} {task_name}")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'beh')
    membids_df = pd.DataFrame(columns=['onset', 'duration', 'event_type', 'value', 'response_accuracy', 'stim_file', 'button_press'])

    df_memmain = pd.read_csv(memory_fpath)
    trigger = df_memmain['param_trigger_onset'].values[0]

    # -> << study >>
    memory_study_flist = sorted(glob.glob(join(beh_inputdir, sub_bids, f'{sub_bids}_ses-04_task-fractional_{run_bids}_memory_study*_beh.csv' )))
    for memory_study_fname in memory_study_flist:
        print(os.path.basename(memory_study_fname))
        df_memstudy = pd.read_csv(memory_study_fname)
        temp_study = pd.DataFrame(columns=['onset', 'duration', 'event_type', 'value', 'response_accuracy', 'stim_file', 'button_press', 'reaction_time']) #.append(pd.DataFrame(index=range(df_memstudy01.shape[0])))

        temp_study['onset'] = df_memstudy['RAW_event02_image_onset'] - trigger
        temp_study['duration'] = df_memstudy['RAW_event03_isi_onset'] - df_memstudy['RAW_event02_image_onset']
        temp_study['event_type'] = df_memstudy['event02_dummy_stimuli_type'].replace({0: 'dummy', 1: 'study'})
        temp_study['value'] = temp_study['event_type'].replace({'dummy': 'study_dummy', 'study':'study'})
        temp_study['stim_file'] = task_name + '/' + df_memstudy['event02_image_filename']
        temp_study['response_accuracy'] = "n/a" #np.nan TODO: reverse inference and go back 
        temp_study['button_press'] = "n/a"
        temp_study['reaction_time'] = "n/a"
        membids_df = pd.concat([membids_df, temp_study], ignore_index=True)

    # -> test onset
    memory_test_flist = sorted(glob.glob(join(beh_inputdir, sub_bids, f'{sub_bids}_ses-04_task-fractional_{run_bids}_memory_test*_beh.csv' )))
    for memory_test_fname in memory_test_flist:
        print(os.path.basename(memory_test_fname))
        df_memtest = pd.read_csv(memory_test_fname)
        temp_test = pd.DataFrame(columns=['onset', 'duration', 'event_type', 'value', 'response_accuracy', 'stim_file', 'button_press', 'reaction_time']) #.append(pd.DataFrame(index=range(df_memstudy01.shape[0])))
        temp_test['onset'] = df_memtest['RAW_event02_image_onset'] - trigger
        temp_test['duration'] = df_memtest['RAW_event03_response_onset'] - df_memtest['RAW_event02_image_onset']
        temp_test['duration'] = temp_test['duration'].fillna(2) # if duration is na, fill with 2
        temp_test['event_type'] = 'test'
        temp_test['value'] =  df_memtest['param_answer'].replace({0: 'test_new', 1:'test_old'})
        temp_test['stim_file'] = task_name + '/' + df_memtest['event02_image_filename']
        df_memtest['event03_response_key'] = df_memtest['event03_response_key'].fillna(0)
        temp_test['response_accuracy'] = (df_memtest['param_answer'] == df_memtest['event03_response_key']).astype(int).replace({0: 'incorrect', 1:'correct'})
        temp_test['button_press'] = df_memtest.event03_response_keyname.replace({'right': 'new', 'left':'old', 'NaN': 'n/a', 'nan': 'n/a'})
        temp_test['reaction_time'] = "n/a"
        membids_df = pd.concat([membids_df, temp_test], ignore_index=True)
# % ` param_answer ` 1 = old, 0 = new
# event03_response_keyname: old is on left; new is on right
        
    # -> test onset
    memory_dist_flist = sorted(glob.glob(join(beh_inputdir, sub_bids, f'{sub_bids}_ses-04_task-fractional_{run_bids}_memory_distraction*_beh.csv' )))
    for memory_dist_fname in memory_dist_flist:
        print(os.path.basename(memory_dist_fname))
        df_memdist = pd.read_csv(memory_dist_fname)
        temp_dist = pd.DataFrame(columns=['onset', 'duration', 'event_type', 'value', 'response_accuracy', 'stim_file',  'button_press', 'reaction_time']) #.append(pd.DataFrame(index=range(df_memstudy01.shape[0])))
        temp_dist['onset'] = df_memdist['p2_operation'] - trigger
        temp_dist['duration'] = 25 
        temp_dist['event_type'] = 'distraction_math'
        temp_dist['value'] = 'math'
        temp_dist['stim_file'] = "n/a"
        temp_dist['response_accuracy'] = "n/a"
        temp_dist['button_press'] = "n/a"
        temp_dist['reaction_time'] = "n/a"
        membids_df = pd.concat([membids_df, temp_dist], ignore_index=True)
    

    Path(beh_savedir).mkdir( parents=True, exist_ok=True )
    save_fname = f"{sub_bids}_ses-04_task-{task_name}_{run_bids}_events.tsv"
    membids_df.to_csv(join(beh_savedir, save_fname), sep='\t', index=False)


    description_onset = {
        "LongName": "Onset time of event",
        "Description": "Marks the start of an ongoing event of temporal extent.",
        "Units": "s",
        "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
    }
    description_duration = {
        "LongName": "The period of time during which an event occurs. Refers to Image duration or response time after stimulus depending on event_type",
        "Description": "a. For falsebelief and falsephoto trial types, duration refers to the image presentations of falsebelief and falsephoto stories. b. For rating_falsebelief and rating_falsephoto, duration refers to the response time to answer true false questions, followed by falsebelief or flasephoto stimulu",
        "Units": "s",
        "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"} #[x]

    description_eventtype = {
        "LongName": "Event category",
        "Description": "Categorical variable of event types within run",
        "Levels": {
            "dummy": "Study phase items, but intended to be excluded from analysis due to primacy or recency effects. These items are presented in the first three or last three orders",
            "study": "Study phase items: Participants are shown items (e.g., images) to memorize for subsequent testing. This phase aims to encode the items into participants' memory.",
            "test": "Test phase items: Participants are asked to identify previously studied items ('old') and distinguish them from new, unstudied items ('new'), assessing recall and recognition abilities.",
            "distraction_math": "Simple math problems are presented to participants, serving to temporarily divert attention from the study-test sequence. This task is designed to mitigate rehearsal and reduce potential carry-over effects between the study and test phases."
        },
        "HED": {
            "dummy": "Action/Think/Encode",
            "study": "Action/Think/Encode", 
            "test":"Action/Think/Recall",
            "distraction_math":"Action/Think/Count"
            }
    } # [x]

    description_value = {
        "LongName": "The levels of study items and test items",
        "Description":"",
        "Levels": {"study_dummy": "Presentation of items to study - the first and the last three items are discarded due to primary/recency effects, indicated as dummy.",
                "study": "Presentation of items to study",
                "test_old":"Test phase items: items that were presented during study phase",
                "test_new":"Test phase items: items that were not presented during study phase; new items presented to participant during test phase",
                "math":"Simple math problems presented during math phase"
                },
        "HED": {"study_dummy": "Action/Perform/Read",
                "study": "Action/Think/Encode",
                "test_old": "Action/Think/Recall",
                "test_new":"Action/Think/Recall",
                "math":"Action/Think/Count"} # Q. Is this the right HED?
    }


    description_accuracy = {
        "LongName": "Correct or Incorrect response",
        "Description": "Correct or Incorrect response in regards to question presented on screen; Options are Old and New, presented on screen, underneath image. Participants are promted to respond with MR-compatible button box",
        "Levels": {
            "correct": "Correct response in regards to image (correctly identified as old or new)",
            "incorrect": "Incorrect response in regards to image (incorrectly identified as old or new)"
        },
        "HED": { 
            "correct": "Property/Task-property/Task-action-type/Correct-action", 
            "incorrect": "Property/Task-property/Task-action-type/Incorrect-action"
            }
    } #[x]

    description_stimfile =  {
            "LongName": "Stimulus filename which is presented on screen",
            "Description": "Given text file encompasses test that is displayed on screen. Filename is designated as {digit}{belief_or_photo}_{story_or_question}.txt. Digit indicates the number of stimulus that was presented. b or p indicates whether stimulus was false belief or false photo event. Story or question indicates which event was presented on screen.",
            "HED": "(Textblock, Pathname/#)"
        }

    description_buttonpress =  {
            "LongName": "Key press",
            "Description": "Given text file encompasses test that is displayed on screen. Filename is designated as {digit}{belief_or_photo}_{story_or_question}.txt. Digit indicates the number of stimulus that was presented. b or p indicates whether stimulus was false belief or false photo event. Story or question indicates which event was presented on screen.",
            "Levels": {
                "old": "Participant presses old button to indicate they saw the item during the study phase. Old option is presented on the left side of the screen", 
                "new": "Participant presses new button to indicate they did not see the item during the study phase. New option is presented on the right side of the screen"},
            "HED": {
                "old": "Action/Move/Move-body-part/Move-upper-extremity/Press", 
                "new": "Action/Move/Move-body-part/Move-upper-extremity/Press"
        }
    }
    
    description_rt=  {
        "LongName": "Reaction time of responding to test item",
        "Description": "Reaction time is measure as the time of button press minus the time of test item presentation",
        "HED": ""
    }
    events_json = {"onset": description_onset,
                   "duration": description_duration, 
                   "event_type": description_eventtype, 
                   "value":description_value,
                   "response_accuracy":description_accuracy,
                   "stim_file": description_stimfile,
                   "button_press":description_buttonpress,
                   "reaction_time":description_rt,
                   }  
    # TODO: change fname to be subject specific
    json_fname = join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.json")
    with open(json_fname, 'w') as file:
        json.dump(events_json, file, indent=4)
# %% -----------------------------------------------
#                       spunt
# -------------------------------------------------
"""
[param_cond_type_string]: c4_HowHand
[param_normative_response]: correct answer
[param_image_filename]: image_fname
param_trigger_onset
onset: [event02_image_onset] [RAW_e2_image_onset] - param_trigger_onset
duration: [event02_image_dur] [RAW_e3_response_onset] - [RAW_e2_image_onset] 
event_type:
button_press: [RAW_e3_response_onset] - [param_trigger_onset]
pmod_accuracy: [accuracy]

param_normative_response: 1, 2
event03_response_key: 1,3 -> convert to 1,2
Yes = 1, No =2
"""
task_name = "tomspunt"
current_path = Path.cwd()
spunt_flist = sorted(glob.glob(join(beh_inputdir, '**', f'*{task_name}_beh.csv'), recursive=True))
for spunt_fpath in spunt_flist:
    spunt_fname = os.path.basename(spunt_fpath)
    sub_bids = re.search(r'sub-\d+', spunt_fname).group(0)
    ses_bids = re.search(r'ses-\d+', spunt_fname).group(0)
    run_bids = re.search(r'run-\d+', spunt_fname).group(0)
    task_name = re.search(r'run-\d+-(\w+)_beh', spunt_fname).group(1)
    print(f"{sub_bids} {ses_bids} {run_bids} {task_name}")
    beh_savedir = join(bids_dir, sub_bids, ses_bids, 'beh')

    df_spunt = pd.read_csv(spunt_fpath)

    events = pd.DataFrame(columns=['onset', 'duration','question', 'event_type','participant_response', 'normative_response', 'response_accuracy', 'stim_file']) 
    blockquestion = pd.DataFrame(columns=['onset', 'duration','question', 'event_type','participant_response', 'normative_response', 'response_accuracy', 'stim_file']) 

    events['onset'] = df_spunt['RAW_e2_image_onset'] - df_spunt['param_trigger_onset']
    events['duration'] = df_spunt['RAW_e3_response_onset'] - df_spunt['RAW_e2_image_onset'] 
    events['question'] = df_spunt['param_ques_type_string']
    df_spunt['event_type'] = df_spunt['param_cond_type_string'].str.replace('^(c[1234])_', '', regex=True).str.replace(r'([a-z])([A-Z])', r'\1_\2').str.lower()
    events['participant_response'] = df_spunt['event03_response_keyname'].replace({'left': 'yes', 'right':'no'})
    events['normative_response'] = df_spunt['param_normative_response'].replace({1:'yes', 2:'no'})
    events['event_type'] = df_spunt['event_type'].str[:3] + '_' + df_spunt['event_type'].str[3:]
    events['stim_file'] = task_name + '/' + df_spunt['param_image_filename']
    df_spunt['reponse_subject'] = df_spunt['event03_response_key'].replace(3, 2)
    events['response_accuracy'] = (events['participant_response'] == events['normative_response']).astype(int).replace({1: "correct", 0: "incorrect"})

    blockquestion['onset'] = df_spunt['event01_blockquestion_onset']
    blockquestion['duration'] = df_spunt['event01_blockquestion_dur']
    blockquestion['question'] = df_spunt['param_ques_type_string']
    blockquestion['event_type'] = "block_question_presentation"
    blockquestion['participant_response'] = "n/a"
    blockquestion['normative_response'] = "n/a"
    blockquestion['stim_file'] = "n/a"
    blockquestion['response_accuracy'] = "n/a"
    block_unique = blockquestion.drop_duplicates()

    events = pd.concat([events, block_unique], ignore_index=True)


    Path(beh_savedir).mkdir( parents=True, exist_ok=True )
    save_fname = f"{sub_bids}_ses-04_task-{task_name}_{run_bids}_events.tsv"
    events.to_csv(join(beh_savedir, save_fname), sep='\t', index=False)

    # create metadata    
    description_onset = {
        "LongName": "Onset time of event",
        "Description": "Marks the start of an ongoing event of temporal extent.",
        "Units": "s",
        "HED": "Property/Data-property/Data-marker/Temporal-marker/Onset"
    }
    description_duration = {
        "LongName": "The period of time during which an event occurs.",
        "Description": "duration refers to the Image duration, which is contingent on response time after stimulus presentation",
        "Units": "s",
        "HED": "Property/Data-property/Data-value/Spatiotemporal-value/Temporal-value/Duration"} #[x]

    description_eventtype = {
        "LongName": "Event category",
        "Description": "Categorical variable of event types within run",
        "Levels": {
            "howhand": "Question related to explicit physical attributes of hand related actions, e.g. Is this person reaching?",
            "whyhand": "Questions related to inferring the implicit mental states focusing on hand related actions, e.g. Is the person helping someone?",
            "whyface": "Questions related to inferring the implicit mental states, focusing on face related observations, e.g. Is the person proud of themselves",
            "howface": "Question related to explicit physical attributes of face observations",
            "block_question_presentation": "Prior to eight blocks of trials, the question of interest is presented on screen. For example, 'Is the person admiring someone?' or 'Is the person lifting something?'"
        },
        "HED": {
            "howhand": "Action/Think/Judge",
            "whyhand": "Action/Think/Judge", 
            "whyface": "Action/Think/Judge",
            "howface": "Action/Think/Judge", 
            "block_question_presentation": "Action/Perform/Read"
            }
    } # [x]



    description_participantresponse =  {
            "LongName": "Participant response",
            "Description": "Participant responds Yes or No, based on experimetal question and image presented",
            "Levels": {
                "yes": "Participant presses yes button to indicate the image matches the question", 
                "no": "Participant presses no button to indicate the image does NOT match the question"},
            "HED": {
                "yes": "Property/Data-property/Data-value/Categorical-value/Categorical-class-value/True", 
                "no": "Property/Data-property/Data-value/Categorical-value/Categorical-class-value/False"
        }
    }


    description_normative_response =  {
            "LongName": "Normative response",
            "Description": "Group responses based on identical trial",
            "Levels": {
                "yes": "Group responded yes, to indicate the image matches the question", 
                "no": "Group responded no indicate the image does NOT match the question"},
            "HED": {
                "yes": "Property/Data-property/Data-value/Categorical-value/Categorical-class-value/True", 
                "no": "Property/Data-property/Data-value/Categorical-value/Categorical-class-value/False"
        }
    }

    description_accuracy = {
        "LongName": "Correct or Incorrect response",
        "Description": "Correct or Incorrect response in regards to question presented on screen; Options are Yes or No, presented on screen, underneath image. Participants are promted to respond with MR-compatible button box",
        "Levels": {
            "correct": "Correct response in regards to question",
            "incorrect": "Incorrect response in regards to question"
        },
        "HED": { 
            "correct": "Property/Task-property/Task-action-type/Correct-action", 
            "incorrect": "Property/Task-property/Task-action-type/Incorrect-action"
            }
    } #[x]
    description_stimfile =  {
            "LongName": "Stimulus filename which is presented on screen",
            "Description": "Given text file encompasses test that is displayed on screen. Filename is designated as {digit}{belief_or_photo}_{story_or_question}.txt. Digit indicates the number of stimulus that was presented. b or p indicates whether stimulus was false belief or false photo event. Story or question indicates which event was presented on screen.",
            "HED": "(Textblock, Pathname/#)"
        }
    events_json = {"onset": description_onset,
                   "duration": description_duration, 
                   "event_type": description_eventtype, 
                   "participant_response": description_participantresponse,
                   "normative_response": description_normative_response,
                   "response_accuracy":description_accuracy,
                   "stim_file": description_stimfile,
                   }  
    
    # TODO: change fname to be subject specific
    json_fname = join(beh_savedir, f"{sub_bids}_{ses_bids}_task-{task_name}_{run_bids}_events.json")
    with open(json_fname, 'w') as file:
        json.dump(events_json, file, indent=4)