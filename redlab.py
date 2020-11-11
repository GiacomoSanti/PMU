from usb_20x import *
import numpy as np
import math
from random import random

class Redlab:
    '''
    This class implements all the methods for scanning the signals in input to the channels of the PMU.
    Uses the library usb_20x, part of the redlab drivers.
    '''
    
    STALL_ON_OVERRUN        = 0x0
    INHIBIT_STALL           = 0x1 << 7
    
    def __init__(self, channels=1, frequency=10000, nSamples=1600, options=0b10000000, trigger = 1):
        '''
        channels: number of channels or list of channels
        frequency: sampling frequency
        nSamples: number of samples for channel to read
        trigger: if set to 1 synchronizes the measurements with the PPS given by the GPS module
        options: first bit sets the stall options. Many other options are available(see USB_20x)
        '''
        if frequency < 1 or frequency > 12500:
            raise ValueError("The frequency must be in range 1 < f <= 12500 ") #100Ks/s is the maximum, but has to be split by the 8 channels

        try:
            self.device = usb_201() #Add control on the model here for future changes in the architecture.
            print("USB-201 device found.")
        except:
            print("USB-201 device not found.")

            
        self.nSamples = nSamples
        self.frequency = frequency
        self.options = options
        self.trigger = trigger

        self.set_num_channels(channels)
        self.setup_scan()
        
    def setup_scan(self):
        '''
        Setup the RedLab Continuous Analog Input Scan. Uses methods from the lib.
        '''
        self.device.AInScanStop()
        self.device.AInScanClearFIFO()
        self.device.AInScanStart(self.nSamples, self.frequency, self.channel_mask, self.options, self.trigger, 0)
           
    def set_num_channels(self, channels):
        '''
        Set how many channels to scan. channels is a list.
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

                    
        self.channel_mask = 0   #sets the mask for the channels. es. channel 1,2,3 -> 01110000
        for i in self.channels:
            self.channel_mask |= (0x1 << i)
            
        
    def read(self):
        '''
        Returns: a dictionary containing the sampled data in three different formats:
        raw_data, data and volts.
        The size of the dictionary is nSamples*channels. 
        '''
        raw_data = self.device.AInScanRead(self.nSamples)

        data = {}

        for c in self.channels: # init dict
            data[c] = {
                'rawData': [],
                'volts': [],
                'data': []
            }


        for scan in range(self.nSamples):
            '''
            Cycles on the scans, and fills the dictionary.
            '''
            for i, chan in enumerate(self.channels):
                ii = scan + i*self.nSamples
                data[chan]['rawData'].append(raw_data[ii])
                data[chan]['data'].append(raw_data[ii]*self.device.table_AIn[chan].slope + self.device.table_AIn[chan].intercept)


        for c in self.channels:
            data[c]['volts'] = [self.device.volts(x) for x in data[c]['data']]


        self.setup_scan()
        return { 'channels': data, 'frequency': self.frequency, 'samples': self.nSamples}



if __name__ == "__main__":
    from pprint import pprint
    redlab = Redlab(channels=[1,2,3])
    time.sleep(1)
    data = redlab.read()
    pprint(data, depth=3)
    #pprint(data['channels'][1]['volts'][:110])
    #pprint(data['channels'][2]['volts'][:110])
    #pprint(data['channels'][3]['volts'][:110])
    pass