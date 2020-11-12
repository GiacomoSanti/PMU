import numpy as np
import math
from random import random
from pprint import pprint
from redlab import *

def zero_crossing_indexes(samples):
    '''
    samples = list of samples 
    returns: list of the samples' indexes after the sign change occurs. 
    Can be set from positive to negative or viceversa.
    '''
    last = -1
    zeroIndexes = []
    
    for i, current in enumerate(samples):
        if current < 0 and last >= 0:   #swap this two lines to change 
        #if current > 0 and last <= 0: 
            zeroIndexes.append(i)
        last = current

    return zeroIndexes

def zero_cross_offset(s1, s2, Ts):
    '''
    Interpolates the two samples s1 & s2.
    '''
    offset_b = (s2*Ts/(s2-s1))
    offset_a = Ts - offset_b

    return offset_a, offset_b

def zero_crossing_times(samples, frequency, zero_indexes):
    '''
    Returns the list of times where the zeros(only positive to negative or viceversa) occur.
    Interpolates the samples before and after the zeros.
    '''

    zero_crossing_times = []

    Ts = 1/frequency

    for zi in zero_indexes:
        a, b = zero_cross_offset(samples[zi-1], samples[zi], Ts)
        zero_crossing_times.append(zi*Ts-b)

    return zero_crossing_times

def get_periods(zero_crossing_times):
    '''
    Returns the list of periods found as the difference between two consecutives zero times
    '''
    
    ps = []

    for i in range(1, len(zero_crossing_times)):
        ps.append(zero_crossing_times[i] - zero_crossing_times[i-1])
        
    return ps

def get_rocof(periods):
    '''
    Calculates Rocof index as the difference between the reciprocal of the first period and the last found.
    '''
    if len(periods) >= 2:
        return 1/periods[0] - 1/periods[-1]
    else:
        print('Impossible to calculate rocof: less then 2 periods found')

def get_average_frequency(periods):
    '''
    Estimates the average frequency as the average of the reciprocal of the periods
    '''
    
    if len(periods) >= 1:
        return np.average(np.reciprocal(periods))
    else:
        print('Impossibile frequenza media: nessun periodo trovato')

def windowed_fft(samples, zero_crossing_indexes, s_freq, offset_a, offset_b, a_freq, nSamples):
    '''
    Calculates the DFT of the samples passed using FFT functions from numpy lib.
    Returns the array of phasors, the array of the frequencies corrisponding to the phasors calculated, and the index of the fondamental phasor.
    '''    
    Ts = 1/s_freq
    samples_per_period = int(s_freq/a_freq) # for best results s_freq and a_freq should be multiples
    periods_taken = (zero_crossing_indexes[-1] - (zero_crossing_indexes[0]-1))//samples_per_period  #number of periods taken

    window_length = periods_taken*samples_per_period #The window length is maximum multiple of the period
    window_start = zero_crossing_indexes[0]-1
    window_end = window_length + window_start
    window = samples[ window_start: window_end]

    frequencies = np.fft.fftfreq(len(window), d=Ts)
    phasors = np.fft.fft(window)

    imax = int(round(len(window)*Ts*a_freq)) #the index of the fondamental phasor is calculated aproximating windowLength*SamplingPeriod*AverageFrequency.

    phaseShift = 2*np.pi*frequencies[imax]*((zero_crossing_indexes[0])*Ts-offset_b) #the phase shift is calculated interpolating the samples where the window starts.
    phasors = phasors*np.exp(-1j*phaseShift)
    
    return phasors, frequencies, imax

def estimate_phasors(scan):
    '''
    Returns a dictionary containing all the channels' estimated fondamental phasors

        ( complex number 
        + amplitude 
        + phase_in_rad 
        + phase_in_degrees)
        + fft frequency, 
        + average frequency 
        + rocof )
                                                                
    Size: Channels*phasor
    '''

    result = {}

    for chan in scan['channels']: #cycles on channels
        samples = scan['channels'][chan]
        zc_indexes = zero_crossing_indexes(samples['volts']) #Step 1: indexes

        if len(zc_indexes) < 2:
            print('Not enough zero crossings found in channel ', chan)
            continue

        zc_times = zero_crossing_times(samples['volts'], scan['frequency'], zc_indexes) #Step 2: times
        
        periods = get_periods(zc_times) #Step 3: periods
        rocof = get_rocof(periods) #Step 4: Rocof & Average Frequency
        avg_freq = get_average_frequency(periods)

        s1 = samples['volts'][zc_indexes[0]-1]
        s2 = samples['volts'][zc_indexes[0]]
        Ts = 1/scan['frequency']
        offset_a, offset_b = zero_cross_offset(s1, s2, Ts) #Step 5: interpolation

        phasors, frequencies, imax = windowed_fft(  samples['volts'], #Step 6: FFT
                                                    zc_indexes, 
                                                    scan['frequency'], 
                                                    offset_a,
                                                    offset_b,
                                                    avg_freq, 
                                                    scan['samples'])

        p = phasors[imax]

        result[chan] = {    #Step 6: Dictionary filling
            'rocof': rocof,
            'avg_freq': avg_freq,
            'amplitude': 2*np.abs(p)/len(phasors),
            'phase_deg' : (np.angle(p, True) + 360) % 360,
            'phase' : np.angle(p, False),
            'fft_freq' : frequencies[imax],
            'phasor' : p
        }
        
    return result





def fake_cos(frequency, phase, sampleFrequency=10000, nSamples=1600, A=3):
    '''
    Simulates the sampling of a Cos signal. Use: for tests. Returns a volt type array of fake samples
    '''

    volts = []

    for i in range(nSamples):
        t = i/sampleFrequency
        volts.append( A*math.cos( 2*np.pi*frequency*t + phase))
    
    return volts

def fake_scan(sFreq, samples, nFreq):
    '''
    Returns a fake scan of 8 channels
    sFreq = sampling frequency
    samples = number of samples for each channel
    nFreq = nominal Frequency
    '''
    fake_scan = {
            'frequency': sFreq, 
            'samples': samples, 
            'nFreq': nFreq,
            'channels': {
                1: {
                    'volts': fake_cos(nFreq-0.05, 0, sFreq, samples)
                },
                2: {
                    'volts': fake_cos(nFreq-0.04, np.pi/4, sFreq, samples)
                },
                3: {
                    'volts': fake_cos(nFreq-0.03, np.pi/3, sFreq, samples)
                },
                4: {
                    'volts': fake_cos(nFreq-0.02, np.pi/2, sFreq, samples)
                },
                5: {
                    'volts': fake_cos(nFreq-0.01, np.pi/5, sFreq, samples)
                },
                6: {
                    'volts': fake_cos(nFreq, np.pi/6, sFreq, samples)
                },
                7: {
                    'volts': fake_cos(nFreq+0.01, np.pi/12, sFreq, samples)
                },
                8: {
                    'volts': fake_cos(nFreq+0.02, np.pi/18, sFreq, samples)
                }
            }
        }
    return fake_scan


if __name__ == "__main__":
    redlab = Redlab(channels=[1,2,3])
    
    
    t = time.time()
    data = redlab.read()
    data = redlab.read()
    time.sleep(0.3)

    pprint(estimate_phasors(data))