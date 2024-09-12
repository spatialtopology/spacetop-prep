% Preprocessing of behavior data from task-narratives

% This script extracts the moment-by-moment mouse position data (sampled at
% 60 Hz) from original .mat files, finds ratings and motion time from them,
% and adds those data to original .csv files which contain all other time
% stamps.
% The new .csv files will be named as *_beh_preproc.csv.

% See README.md and the associated paper (Jung et al., 2024) for more
% information.

clear
codeDir = '/Users/h/Documents/projects_local/1076_spacetop/code';

taskname = 'task-narratives';
% >>>
% fill in the top level of your d_beh folder
dataDir = '/Users/h/Documents/projects_local/1076_spacetop/sourcedata/d_beh';
% >>>
% change below if you would like to process data from a subset of all subjects
endSub = 133;

% >>>
% besides the `d_beh` repo, you will need another repo (task-narratives
% [https://github.com/spatialtopology/task-narratives]) to get all the
% information needed to generate the events files
% clone it, then fill in the top level of your task_narratives folder
% taskDesignDir = '';
% DesignTable = readtable(fullfile(dataDir, "design", "task-narratives_counterbalance_ver-01.csv"));
url = 'https://raw.githubusercontent.com/spatialtopology/task-narratives/master/design/task-narratives_counterbalance_ver-01.csv';
counterbalance_filename = fullfile(dataDir, 'task-narratives_counterbalance_ver-01.csv');
filepath = websave(counterbalance_filename, url);
DesignTable = readtable(counterbalance_filename);
narratives = {[7, 8], [5, 6], [3, 4], [1, 2]};    % narrative presented in each run

for i = 1:endSub
    sub = strcat('sub-', sprintf("%04d", i));
    
    for r = 1:4    % four runs
        % .csv files contain onset time, stim_file, condition, etc.
        csvFile = fullfile(dataDir, sub, taskname, ...
            strcat(sub, '_ses-02_', taskname, '_run-0', num2str(r), '_beh.csv'));
        if ~exist(csvFile, 'file')
            continue
        end
        csvData = readtable(csvFile);
        
        % *trajectory.mat files contain mouse trajectories
        matFile = fullfile(dataDir, sub, taskname, ...
            strcat(sub, '_ses-02_', taskname, '_run-0', num2str(r), ...
            '_beh_trajectory.mat'));
        if ~exist(matFile, 'file')
            % if there is .csv file but no .mat file
            % no information can be provided or updated
            continue
        end
        load(matFile)
        
        trialNum = size(csvData, 1);    % how many trials
        [feeling_end_x, feeling_end_y, RT_feeling, RT_feeling_adj, motion_onset_feeling, ...
            motion_dur_feeling, expectation_end_x, expectation_end_y, ...
            RT_expectation, RT_expectation_adj, motion_onset_expectation, motion_dur_expectation] ...
            = deal(zeros(trialNum, 1));    % new data to extract and store
        [situation, context] = deal(cell(trialNum, 1));
        
        for k = 1:trialNum
            % Select the final rating point based on reaction time
            % Because of a feature in the experiment code, 
            % the last 0.5 seconds of each trial always recorded mouse positions
            
            % For feeling
            % reaction time
            feelRT = csvData.event03_feel_RT(k);
            if ~isnan(feelRT)
                % participants provided response
                RT_feeling(k) = feelRT;
                RT_feeling_adj(k) = NaN;
                end_point = round(feelRT*60);  % the index of the last mouse position
                feeling_end_x(k) = rating_Trajectory{k, 1}(end_point, 1);
                feeling_end_y(k) = rating_Trajectory{k, 1}(end_point, 2);
            else
                % no recorded RT, impute the RT (RT_adj) by seeking the last "transition point"
                RT_feeling(k) = NaN;
                for l = size(rating_Trajectory{k,1},1):-1:2
                    if (rating_Trajectory{k,1}(l,1) ~= rating_Trajectory{k,1}(l-1,1))...
                            || (rating_Trajectory{k,1}(l,2) ~= rating_Trajectory{k,1}(l-1,2))
                        break
                    end
                end
                if l == 2 && (rating_Trajectory{k,1}(2,1) == rating_Trajectory{k,1}(1,1))...
                        && (rating_Trajectory{k,1}(2,2) == rating_Trajectory{k,1}(1,2))
                    % No movement at all
                    RT_feeling_adj(k) = NaN;
                    feeling_end_x(k) = NaN;
                    feeling_end_y(k) = NaN;
                else
                    % l-1 is when the last movement happened
                    RT_feeling_adj(k) = (l-1)/60;
                    feeling_end_x(k) = rating_Trajectory{k,1}(end,1);
                    feeling_end_y(k) = rating_Trajectory{k,1}(end,2);
                end
            end
            % find decision onset time
            if ~isnan(feelRT)
                % when there was a response, there were always more mouse
                % positions recorded after the response
                % search forward until the response point
                search_end = max(round(feelRT*60), 2);    % avoid errors
            else
                % there was no response
                % search forward until the end of the recording
                search_end = size(rating_Trajectory{k,1}, 1);
            end
            % search first move
            for l = 2:search_end
                if (rating_Trajectory{k,1}(l,1) ~= rating_Trajectory{k,1}(l-1,1))...
                        || (rating_Trajectory{k,1}(l,2) ~= rating_Trajectory{k,1}(l-1,2))
                    break
                end
            end
            if rating_Trajectory{k,1}(l,1) == rating_Trajectory{k,1}(1,1) && ...
                    rating_Trajectory{k,1}(l,2) == rating_Trajectory{k,1}(1,2)
                % mouse didn't move at all
                motion_onset_feeling(k) = NaN;
                motion_dur_feeling(k) = NaN;
            else
                % mouse moved
                motion_onset_feeling(k) = (l-1)/60;
                if ~isnan(feelRT)
                    motion_dur_feeling(k) = feelRT - motion_onset_feeling(k);
                else
                    motion_dur_feeling(k) = RT_feeling_adj(k) - motion_onset_feeling(k);
                end
            end
            
            % For expectation
            expectRT = csvData.event04_expect_RT(k);
            if ~isnan(expectRT)
                % participants provided response
                RT_expectation(k) = expectRT;
                RT_expectation_adj(k) = NaN;
                end_point = round(expectRT*60);  % the index of the last mouse position
                expectation_end_x(k) = rating_Trajectory{k, 2}(end_point, 1);
                expectation_end_y(k) = rating_Trajectory{k, 2}(end_point, 2);
            else
                % no recorded RT, impute the RT (RT_adj) by seeking the last "transition point"
                RT_expectation(k) = NaN;
                for l = size(rating_Trajectory{k,2},1):-1:2
                    if (rating_Trajectory{k,2}(l,1) ~= rating_Trajectory{k,2}(l-1,1))...
                            || (rating_Trajectory{k,2}(l,2) ~= rating_Trajectory{k,2}(l-1,2))
                        break
                    end
                end
                if l == 2 && (rating_Trajectory{k,2}(2,1) == rating_Trajectory{k,2}(1,1))...
                        && (rating_Trajectory{k,2}(2,2) == rating_Trajectory{k,2}(1,2))
                    % No movement at all
                    RT_expectation_adj(k) = NaN;
                    expectation_end_x(k) = NaN;
                    expectation_end_y(k) = NaN;
                else
                    % l-1 is when the last movement happened
                    RT_expectation_adj(k) = (l-1)/60;
                    expectation_end_x(k) = rating_Trajectory{k,2}(end,1);
                    expectation_end_y(k) = rating_Trajectory{k,2}(end,2);
                end
            end
            % find decision onset time
            if ~isnan(expectRT)
                % same logic as for feeling
                search_end = max(round(expectRT*60), 2);    % avoid errors
            else
                search_end = size(rating_Trajectory{k,2}, 1);
            end
            % search first move
            for l = 2:search_end
                if (rating_Trajectory{k,2}(l,1) ~= rating_Trajectory{k,2}(l-1,1))...
                        || (rating_Trajectory{k,2}(l,2) ~= rating_Trajectory{k,2}(l-1,2))
                    break
                end
            end
            if rating_Trajectory{k,2}(l,1) == rating_Trajectory{k,2}(1,1) && ...
                    rating_Trajectory{k,2}(l,2) == rating_Trajectory{k,2}(1,2)
                % mouse didn't move at all
                motion_onset_expectation(k) = NaN;
                motion_dur_expectation(k) = NaN;
            else
                % mouse moved
                motion_onset_expectation(k) = (l-1)/60;
                if ~isnan(expectRT)
                    motion_dur_expectation(k) = expectRT - motion_onset_expectation(k);
                else
                    motion_dur_expectation(k) = RT_expectation_adj(k) - motion_onset_expectation(k);
                end
            end

            % extract experiment conditions (situation and context)
            if k <= 9
                situation_chunk = DesignTable.Situation(DesignTable.Narrative == narratives{r}(rem(i-1, 2)+1));
                situation{k} = situation_chunk{k};
                context_chunk = DesignTable.Context(DesignTable.Narrative == narratives{r}(rem(i-1, 2)+1));
                context{k} = context_chunk{k};
            else
                situation_chunk = DesignTable.Situation(DesignTable.Narrative == narratives{r}(2-rem(i-1, 2)));
                situation{k} = situation_chunk{k-9};
                context_chunk = DesignTable.Context(DesignTable.Narrative == narratives{r}(2-rem(i-1, 2)));
                context{k} = context_chunk{k-9};
            end
        end
        % Make a table for this run
        run_table = addvars(csvData, feeling_end_x, feeling_end_y, RT_feeling, RT_feeling_adj, ...
            motion_onset_feeling, motion_dur_feeling, expectation_end_x, ...
            expectation_end_y, RT_expectation, RT_expectation_adj, ...
            motion_onset_expectation, motion_dur_expectation, ...
            situation, context);%,  'NewVariableNames', ...
        % {'rating_end_x', 'rating_converted', 'RT_adj', 'motion_onset', 'motion_dur'});
        outputFile = fullfile(dataDir, sub, taskname, ...
            strcat(sub, '_ses-02_', taskname, '_run-0', num2str(r), ...
            '_beh-preproc.csv'));
        writetable(run_table, outputFile)
    end
    % if rem(i, 10) == 0; disp(i); end  % for test
end