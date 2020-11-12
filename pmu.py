from synchrophasor.frame import *
from synchrophasor.pmu import Pmu
from estimator import *
from redlab import *
from datetime import datetime
import time
import RPi.GPIO as gpio

class MyPmu:
    '''
    Implements the communication protocol of the IEEE C37.118 synchrofphasor standard (IEC 61850) 
    using "pypmu" lib (synchrophasor in the imports).
    This class acts like a wrapper interfacing the lib. 
    Uses a callback function to handle the PPS as a trigger event on the GPIO 18 of the raspberry.
    '''

    def __init__(self, channelNames, nFreq = 50):
        '''
        channelNames = list of the Channels' Names
        nFreq = Nominal Frequency is needed for the configuration frame!
        '''
        self.pmu = Pmu(ip="127.0.0.1", port=1411)
        self.pmu.logger.setLevel("DEBUG")
        self.nFreq = nFreq

        ph_v_conversion = [(100000, "v")]*len(channelNames)  # Voltage phasor conversion factor

        self.cfg = ConfigFrame2(7,  # PMU_ID
                       1000000,  # TIME_BASE
                       1,  # Number of PMUs included in data frame
                       "Station A",  # Station name
                       7734,  # Data-stream ID(s)
                       15,  # Data format - Check ConfigFrame2 set_data_format()
                       len(channelNames),  # Number of phasors
                       0,  # Number of analog values
                       0,  # Number of digital status words
                       channelNames,  # Channel Names
                       ph_v_conversion,  # Conversion factor for phasor channels
                       [],  # Conversion factor for analog channels
                       [],  # Mask words for digital status words
                       nFreq,  # Nominal frequency
                       1,  # Configuration change count
                       1)  # Rate of phasor data transmission)

        self.hf = HeaderFrame(7,  # PMU_ID
                        "Hello I'm MyPMU!")  # Header Message

        self.pmu.set_configuration(self.cfg)
        self.pmu.set_header(self.hf)


    def run(self):
        '''
        Create TCP socket, bind port and listen for incoming connections
        '''

        self.pmu.run()
        while True:
            pass    
        self.pmu.join()


    def set_dataframe(self, synchrophasors, soc):
        '''
        Sets the new dataframe to be sent.
        '''

        sph = []
        rocof = []
        freq_dev = []
        for chan in synchrophasors: #for every chan is given a synchrophasor
            sph.append((synchrophasors[chan]['amplitude'], synchrophasors[chan]['phase']))
            rocof.append(synchrophasors[chan]['rocof']) #1 rocof for the whole datagram, the first is given
            freq_dev.append(abs(self.nFreq-synchrophasors[chan]['avg_freq']))# average frequency deviation from nominal

        self.current_dataframe = DataFrame(7,  # PMU_ID
            ("ok", True, "timestamp", False, False, False, 0, "<10", 0),  # STAT WORD - Check DataFrame set_stat()
            sph,  # PHASORS
            np.average(freq_dev),  # Frequency deviation from nominal in mHz
            np.average(rocof),  # Rate of Change of Frequency
            [],  # Analog Values
            [],  # Digital status word
            self.cfg,  # Data Stream Configuration
            soc=soc)  
    
    def send(self, redlab, sph, timestamp):
        '''
        This interface function for the lib sets the dataframe with the given arguments and if the PDC is connected start the communication.
        '''
        
        myPmu.set_dataframe(sph, timestamp)
        if myPmu.pmu.clients: #if PDC asked for frame / is connected
            myPmu.pmu.send(myPmu.current_dataframe)

def get_degrees(phasors):
    '''
    Returns the phase of the given phasor as rounded degrees.
    '''
    degrees = []

    for p in phasors:
        d = p[1]*180/np.pi
        if d < 0:
            d += 360
        degrees.append(round(d)) #unround for full digits
    return degrees

def make_callback(redlab, myPmu):
    '''
    Wraps the Callback method that accepts only 1 parameter.
    '''
    def callback(arg):
        '''
        The PPS is connected to the chosen general purpose I/O pin of the raspberry; 
        callback acts as an handler funcion every time the trigger occurs(once per second):
            1- gets the soc
            2- reads the samples,
            3- estimates synchrophasors
            4- sends the data Frame to the PDC if connected 
        '''
        T = time.time()

        scan = redlab.read()
        #scan = fake_scan(int(T)%10+1)  #for testing with no input available

        scan['timestamp'] = round(T)
        sph = estimate_phasors(scan)
        myPmu.send(redlab, sph, scan['timestamp'])
        print('Sent: ', myPmu.current_dataframe.get_phasors(), '   ', get_degrees(myPmu.current_dataframe.get_phasors()), '   ', datetime.fromtimestamp(round(T)))

    return callback



if __name__ == "__main__": 
    
    r = Redlab([1,2,3], 10000, 1600) #init redlab
    myPmu = MyPmu(["VA","VB","VC"]) #ìnit pmu

    #GPIO lib is used to attach the 18th pin of the raspberry
    gpio.setmode(gpio.BCM)
    gpio.setup(18, gpio.IN, pull_up_down=gpio.PUD_DOWN)
    gpio.add_event_detect(18, gpio.RISING)
    callback = make_callback(r, myPmu)
    gpio.add_event_callback(18, callback)

    myPmu.run() #start