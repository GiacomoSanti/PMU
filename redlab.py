from usb_20x import *
import numpy as np
import math
from random import random

class Redlab:
    
    STALL_ON_OVERRUN        = 0x0
    INHIBIT_STALL           = 0x1 << 7
    
    def __init__(self, channels=1, frequency=10000, nSamples=1600, options=0b10000000, nFreq = 50, trigger = 1):
        '''
        channels: number of channels or list of channels
        frequency: sampling frequency
        nSamples: number of samples for channel for read
        '''
        if frequency < 1 or frequency > 12500:
            raise ValueError("The frequency must be in range 1 < f <= 12500 ")

        try:
            self.device = usb_201()
            print("USB-201 device found.")
        except:
            print("USB-201 device not found.")

            
        self.nSamples = nSamples
        self.frequency = frequency
        self.options = options
        self.nFreq = nFreq
        self.trigger = trigger

        self.set_num_channels(channels)
        self.setup_scan()
        
    def setup_scan(self):
        '''
        Setup the RedLab Continuous Analog Input Scan.
        '''
        self.device.AInScanStop()
        self.device.AInScanClearFIFO()
        self.device.AInScanStart(self.nSamples, self.frequency, self.channel_mask, self.options, self.trigger, 0)
           
    def set_num_channels(self, channels):
        '''
        Set how many channels to scan.
        '''
        if isinstance(channels, int):
            if channels <= 0 or channels > 8:
                raise ValueError("The redlab supports 1-8 channels.")
            self.channels = list(range(channels))
        elif isinstance(channels, list):
            if len(channels) > 8:
                raise ValueError("The redlab supports only 8 channels at max.")
            if len(channels) == 0:
                raise ValueError("You must provide at least one channel")
            self.channels = channels
        else:
            raise ValueError("Channels must be an int or a list")

                    
        self.channel_mask = 0
        for i in self.channels:
            self.channel_mask |= (0x1 << i)
            
        
    def read(self):
        '''
        Returns: an array containing the sampled data. The size of the array is nSamples*channels.
        '''
        raw_data = self.device.AInScanRead(self.nSamples)

        data = {}

        for c in self.channels:
            data[c] = {
                'rawData': [],
                'volts': [],
                'data': []
            }


        for scan in range(self.nSamples):
            for i, chan in enumerate(self.channels):
                ii = scan * len(self.channels) + i
                data[chan]['rawData'].append(raw_data[ii])
                data[chan]['data'].append(raw_data[ii]*self.device.table_AIn[chan].slope + self.device.table_AIn[chan].intercept)


        for c in self.channels:
            data[c]['volts'] = [self.device.volts(x) for x in data[c]['data']]


        self.setup_scan()
        return { 'channels': data, 'frequency': self.frequency, 'samples': self.nSamples, 'nFreq': self.nFreq}



if __name__ == "__main__":
    from pprint import pprint
    redlab = Redlab(channels=[1])
    time.sleep(0.1)

    for j in range(5):
        data = redlab.read()
        d = data['channels'][1]['volts']
        for i in range(1, len(d)):
            if abs(d[i]-d[i-1]) > 0.1:
                print("Leakage? Pacchetto perso?", i)
        print(j)
    


    pprint(data, depth=3)
    pprint(data['channels'][1]['volts'][:220])


    pass