%% ProcessWindProfilerBarometerData.m
%
%   Script to ingest and process the wind-profiler barometer data
%
%   D.L. Pepyne
%   Copyright 2018 __University of Massachusetts__.
%   All rights reserved.
%
%   Revision: 26 June 2018; 27 June 2018
%
%% =======================================================================

close all
clear all
clc

%% =======================================================================
% define the program parameters
%

blockSizeInSec = 300;

%% =======================================================================
% load the barometer data into working memory
%

% initialize arrays for holding the barometer data
dqSN = [];  % serial numbers
dqTM = [];  % sample times - seconds since midnight
dqBP = [];  % barometric pressure samples - hPa

% get the directory to process - each directory contains data for a single day
dqDirName = uigetdir('/Users/davep/Documents/casa_folder/2018/PAROS/wind_profiling/', 'Select barometer data directory');
if ( dqDirName == 0 ),
    return;
end

% get the list files in the directory
dqFileList = dir([dqDirName, '/*.txt']);

% for each file
numDQFiles = length(dqFileList);
for f = 1:numDQFiles,
    
    % import the data
    dqFileName = dqFileList(f).name;    
    disp(['INFO - importing data from file - ', num2str(f),': ', dqFileName]);    
    try
        DQDATA = importDQDATA(fullfile(dqDirName, dqFileName));
    catch
        disp(['ERROR - failed importing data from file: ', num2str(f),': ', dqFileName]);
        continue
    end
    
    % store the serial numbers
    dqSN = [dqSN; table2array( DQDATA(1:end,1) ) ];
    
    % store the barometric pressures
    dqBP = [dqBP; table2array( DQDATA(1:end,3) ) ];
    
    % convert the sample times to seconds since midnight
    tempTM = datevec(table2array(DQDATA(1:end,2)),"mm/dd/yy HH:MM:SS.FFF");    
    secSinceMidnight = 3600 * tempTM(:,4) + 60 * tempTM(:,5) + tempTM(:,6);
    
    % store the seconds since midnight sample times
    dqTM = [dqTM; secSinceMidnight];
    
end

% free up some memory
clear DQDATA tempTM secSinceMidnight

%% =======================================================================
% get list of unique barometer serial numbers in the data set - report the
% number of samples and number of missing samples
%

dqSNList = unique(dqSN);
numBarometers = numel(dqSNList);

samplePeriod = [];

disp(' ')
disp(['INFO - ',num2str(numBarometers),' barometers found'])
for b = 1:numBarometers,
    I = find(dqSN == dqSNList(b));
    diffTM = diff(dqTM(I));    
    samplePeriod(b) = median(diffTM);
    expectedSamples = round( ( dqTM(I(end)) - dqTM(I(1)) ) / samplePeriod(b) ) + 1;
    numSamples = length(I);
    missingSamples = expectedSamples - numSamples;
    dispStr = sprintf('  serial: %d, %d samples, %d missing',...
        dqSNList(b),...
        numSamples,...
        missingSamples);
    disp(dispStr)
end

%% =======================================================================
% plot the raw barometric pressure data
%

figure

for b = 1:numel(dqSNList),    
    I = find(dqSN == dqSNList(b));    
    plot(dqTM(I)/3600, dqBP(I))
    hold on    
end

legend(num2str(dqSNList))

grid on
xlabel('Sample Time (hours since midnight UTC)')
ylabel('Barometric Pressure (hPa)')

titleStr = sprintf('Raw Barometric Pressure Data - %s',dqDirName(end-13:end));
title(titleStr)

hold off

%% =======================================================================
% plot the sample rates as a verification of missing samples
%

figure

for b = 1:numel(dqSNList),     
    I = find(dqSN == dqSNList(b));    
    plot(1./diff(dqTM(I))+(b-1))
    hold on    
end

legend(num2str(dqSNList))

grid on
xlabel('Sample Index')
ylabel('Sample Rate (Hz)')

titleStr = sprintf('Sample Rate Data - %s',dqDirName(end-13:end));
title(titleStr)

axis([xlim 0 50])

hold off

%% =======================================================================
% process the data in blocks
%

% give user a chance to look at plots before processing
disp(' ')
disp('Press any key to continue...')
pause
disp(' ')

% set the block start and stop time in seconds since midnight
blockStartTime = min(dqTM);
blockEndTime   = blockStartTime + blockSizeInSec;

% initialize memory for spectrogram data
for b = 1:numBarometers,
    PSDtime{b} = [];
    PSDdata{b} = [];
end

% loop until all blocks in the given data set have been processed
while ( blockEndTime < max(dqTM) ),

    %
    % print a progress message
    %
    
    disp(['INFO - processing data for hour = ',num2str(blockStartTime/3600,'%0.2f')])
    
    %
    % get the pressure data for the current block
    %
    
    for b = 1:numBarometers,
        
        % get indices of samples associated with current barometer
        I = find(dqSN == dqSNList(b));
        
        % get indices of samples in the current block
        J = find(dqTM(I) >= blockStartTime & dqTM(I) < blockEndTime);
        
        % continue if current barometer no samples in the current block
        if ( isempty(J) ),
            disp(['WARNING - ',num2str(dqSNList(b)),' has no samples in current block'])
            continue
        end
        
        % continue if the number of samples is less than 90% of expected
        if ( numel(J) < 0.90 * (samplePeriod(b) * blockSizeInSec) ),
            disp(['WARNING - pressure samples in segment = ',num2str(numel(dqIndx)),', number expected = ',num2str(samplePeriod(b) * blockSizeInSec)])
            continue
        end

        % copy the block of pressure data for current barometer to local variables
        DQt = dqTM(I(J));
        DQx = dqBP(I(J));
        
        % print number of samples vs. number expected
        dispStr = sprintf('  serial: %d, %d samples of %d expected',...
            dqSNList(b), length(DQx), round(blockSizeInSec / samplePeriod(b)));
        disp(dispStr)
        
        % linear interpolate missing samples, if any
        diffTM = diff(DQt);
        I = find(diffTM > 1.9 * samplePeriod(b));        
        if ( numel(I) > 0 ),
            
            tmpTM = [];
            tmpBP = [];
            
            for m = 1:numel(I),                
                deltaTM = DQt(I(m)+1) - DQt(I(m));                
                numMissing = round( deltaTM / samplePeriod(b) ) - 1;
                tmpTM = [tmpTM; DQt(I(m)) + samplePeriod(b) * [1:numMissing]'];
                tmpBP = [tmpBP; nan(numMissing,1)];                
            end
            
            DQt = [DQt;tmpTM];
            DQx = [DQx;tmpBP];
            
            [DQt,I] = sort(DQt,'ascend');
            DQx = DQx(I);
    
            [F,DQTF] = fillmissing(DQx,'linear','SamplePoints',DQt);
            DQx(DQTF) = F(DQTF);
    
%             figure(100)
%             plot(DQt/3600,DQx,'-b')
%             hold on
%             plot(DQt(DQTF)/3600,DQx(DQTF),'or')
%             grid on
%             hold off
%             return
            
        end  % end linear interpolate missing samples

        %
        % obtain the infrasound power spectral density
        %

        % convert the pressure data from hPa to Pa
        DQx = 100 * DQx;

        % calculate the mean pressure sample rate
        dqFs = 1 / mean(diff( DQt ));

        % design a band pass filter
        filter_order       = 4;
        cutoff_lo          = 0.01;
        cutoff_hi          = 9.9;
        normalized_freq_lo = cutoff_lo / (0.5 * dqFs); 
        normalized_freq_hi = cutoff_hi / (0.5 * dqFs);
        [filt_b,filt_a] = butter(filter_order,...
            [normalized_freq_lo normalized_freq_hi],...
            'bandpass');

        % apply the band pass filter to extract the local wind
        % generated infrasound signal from the pressure signal
        DQxf = filtfilt(filt_b,filt_a,DQx);

        % compute the power spectral density of the filtered
        % pressure data using Welch's method
        B = 1000;  % Welch block size
        O = 500;   % samples overlap 50%
        NFFT = 2^nextpow2(B);
        [DQPxx,F] = pwelch(DQxf,hamming(B),O,NFFT,dqFs,'onesided','psd');
        DQPxxdB = 10*log10(DQPxx);

        % plot the infrasound signal and associated power spectrum
        if b == 1,

            figure(200)

            subplot(2,1,1)
            plot(DQt/3600,DQxf,'-b')
            grid on
            xlabel('Hour Since Midnight (UTC)')
            ylabel('Infrasound Level (Pa)')

            subplot(2,1,2)
            plot(F(2:end),DQPxxdB(2:end),'-b')
            grid on
            xlabel('Frequency (Hz)')
            ylabel('Pa^2/Hz (dB)')
            titleStr = sprintf('Infrasound Power Spectrum');
            title(titleStr)

            pause(0.1)

        end
        
        % save the power spectral density for the current block/barometer
        PSDtime{b} = [PSDtime{b}, blockStartTime + ( blockEndTime - blockStartTime ) / 2];
        PSDdata{b} = [PSDdata{b}, DQPxxdB];
    
    end  % end for each barometer
    
    % advance to the next block
    blockStartTime = blockEndTime;
    blockEndTime = blockStartTime + blockSizeInSec;
    
end

%% =======================================================================
% plot the spectrogram for each barometer
%

for b = 1:numBarometers,
    
    if ( ~(numel(PSDtime{b}) > 1) ),
        continue
    end
    
    figure(b*1000)

    % plot the spectrogram data
    surf(PSDtime{b}./3600, F, PSDdata{b},'edgecolor','none');
    axis xy; axis tight; colormap(jet); view(0,90);

    % adjust the axis to the band-pass filter cutoff
    axis([xlim 0 cutoff_hi]);

    % add a title to the plot
    titleStr = sprintf('Spectrogram (Serial: %d) - %s\n(sample rate: %.1f Hz, filter band: [%.2f, %.2f] Hz)',...
        dqSNList(b), dqDirName(end-13:end), 1/samplePeriod(b), cutoff_lo, cutoff_hi);
    title( titleStr, 'fontsize', 14, 'fontweight', 'bold' );

    % label the plot axes
    xlabel('Time (UTC)', 'fontsize', 14, 'fontweight', 'bold');
    ylabel('Frequency (Hz)', 'fontsize', 14, 'fontweight', 'bold');

%     % put the UTC time on the x-axis
%     T1 = get(gca, 'xtick');  
%     T2 = unixtime2mat( T1 - 14400 );
%     T3 = datestr( T2, 13 );
%     set(gca, 'xticklabel', T3); 

    % add a colorbar
    hndl = colorbar;
    set(get(hndl,'ylabel'), 'string', 'Pa^2/Hz', 'fontsize', 14, 'fontweight', 'bold');


end  % end for each barometer




return


%% =======================================================================
%% =======================================================================
