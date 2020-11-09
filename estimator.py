import numpy as np
import math
from random import random
from pprint import pprint

def zero_crossing_indexes(samples):
    '''
    samples = lista di sample (una lista sola)

    returns: la lista di indici dei sample dopo uno zero crossing da positivo a negativo
    '''
    last = -1
    zeroIndexes = []
    
    for i, current in enumerate(samples):
        if current < 0 and last >= 0:
            zeroIndexes.append(i)
        last = current

    return zeroIndexes

def zero_cross_offset(s1, s2, Ts):
    offset_b = (s2*Ts/(s2-s1))
    offset_a = Ts - offset_b

    return offset_a, offset_b

def zero_crossing_times(samples, frequency, zero_indexes):

    zero_crossing_times = []

    Ts = 1/frequency

    for zi in zero_indexes:
        a, b = zero_cross_offset(samples[zi-1], samples[zi], Ts)
        zero_crossing_times.append(zi*Ts-b)

    return zero_crossing_times

def get_periods(zero_crossing_times):
    
    ps = []

    for i in range(1, len(zero_crossing_times)):
        ps.append(zero_crossing_times[i] - zero_crossing_times[i-1])
        
    return ps

def get_rocof(periods):
    if len(periods) >= 2:
        return 1/periods[0] - 1/periods[-1]
    else:
        print('Impossibile calcolare rocof: meno di 2 periodi trovati')

def get_average_frequency(periods):
    
    if len(periods) >= 1:
        return np.average(np.reciprocal(periods))
    else:
        print('Impossibile frequenza media: nessun periodo trovato')

def windowed_fft(samples, zero_crossing_indexes, Ts, offset_a, offset_b, n_freq, nSamples):

    window = samples[zero_crossing_indexes[0]-1 : zero_crossing_indexes[-1]]

    frequencies = np.fft.fftfreq(len(window), d=Ts)
    phasors = np.fft.fft(window)

    imax = round(len(window)*Ts*n_freq)
    #imax = np.argmax(np.abs(phasors[0:int(len(frequencies)/2)]))

    phaseShift = 2*np.pi*frequencies[imax]*((zero_crossing_indexes[0])*Ts-offset_b)
    phasors = phasors*np.exp(-1j*phaseShift)
    
    return phasors, frequencies, imax

def estimate_phasors(scan):

    result = {}

    for chan in scan['channels']:
        samples = scan['channels'][chan]
        zc_indexes = zero_crossing_indexes(samples['volts'])
        zc_times = zero_crossing_times(samples['volts'], scan['frequency'], zc_indexes)
        
        periods = get_periods(zc_times)
        rocof = get_rocof(periods)
        avg_freq = get_average_frequency(periods)

        s1 = samples['volts'][zc_indexes[0]-1]
        s2 = samples['volts'][zc_indexes[0]]
        Ts = 1/scan['frequency']
        offset_a, offset_b = zero_cross_offset(s1, s2, Ts)

        phasors, frequencies, imax = windowed_fft(samples['volts'], zc_indexes, Ts, offset_a, offset_b, scan['nFreq'], scan['samples'])

        p = phasors[imax]

        result[chan] = {
            'rocof': rocof,
            'avg_freq': avg_freq,
            'amplitude': 2*np.abs(p)/len(phasors),
            'phase_deg' : np.angle(p, True),
            'phase' : np.angle(p, False),
            'fft_freq' : frequencies[imax],
            'phasor' : p
        }
        
    return result





def fake_cos(frequency, phase, sampleFrequency=10240, nSamples=1024, A=3):

    volts = []

    for i in range(nSamples):
        t = i/sampleFrequency
        volts.append( A*math.cos( 2*np.pi*frequency*t + phase))
    
    return volts



if __name__ == "__main__":
    fake_scan = {
        'frequency': 10240, 
        'samples': 1024, 
        'nFreq': 50,
        'channels': {
            1: {
                'volts': fake_cos(49.95, np.pi/4)
            },
            2: {
                'volts': fake_cos(50.02, np.pi/4)
            },
            3: {
                'volts': fake_cos(50.01, np.pi/4)
            },
            4: {
                'volts': fake_cos(50.03, np.pi/4)
            },
            5: {
                'volts': fake_cos(49.98, np.pi/4)
            },
            6: {
                'volts': fake_cos(49.97, np.pi/4)
            },
            7: {
                'volts': fake_cos(49.99, np.pi/4)
            },
            8: {
                'volts': fake_cos(50.05, np.pi/3)
            }
        }
    }

    pprint(estimate_phasors(fake_scan))