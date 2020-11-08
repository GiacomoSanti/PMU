from synchrophasor.frame import *
from synchrophasor.pmu import Pmu
from estimator import *
from redlab import *
import time
import RPi.GPIO as gpio

class MyPmu:

    def __init__(self, channelNames, nFreq = 50):
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
                        "Hello I'm nanoPMU!")  # Header Message

        self.pmu.set_configuration(self.cfg)
        self.pmu.set_header(self.hf)


    def run(self):

        self.pmu.run()
        while True:
            pass    
        self.pmu.join()


    def set_dataframe(self, synchrophasors, soc):

        sph = []
        rocof = []
        freq_dev = []
        for chan in synchrophasors:
            sph.append((synchrophasors[chan]['amplitude'], synchrophasors[chan]['phase']))
            rocof.append(synchrophasors[chan]['rocof'])
            freq_dev.append(abs(self.nFreq-synchrophasors[chan]['avg_freq']))

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
        
        myPmu.set_dataframe(sph, timestamp)
        if myPmu.pmu.clients:
            myPmu.pmu.send(myPmu.current_dataframe)

             
def test(x):

    scan = {
        'frequency': 10240, 
        'samples': 1024, 
        'nFreq': 50,
        'channels': {
            1: {
                'volts': fake_cos(49.95, np.pi/4, A=x)
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
                'volts': fake_cos(50.05, np.pi/3, A=x)
            }
        }
    }
    return scan

def make_callback(redlab, myPmu):
    def callback(arg):
        T = time.time()
        scan = redlab.read()
        scan = test(int(T)%10+1)  #for testing with no input available

        scan['timestamp'] = round(T)
        sph = estimate_phasors(scan)

        myPmu.send(redlab, sph, scan['timestamp'])
        print('Received: ', myPmu.current_dataframe.get_phasors(), 'Time: ',myPmu.current_dataframe.get_soc())

    return callback



if __name__ == "__main__":
    r = Redlab(8, 10240, 1024)
    myPmu = MyPmu(["VA", "VB", "VC", "VD", "VE", "VF", "VG", "VH"])

    gpio.setmode(gpio.BCM)
    gpio.setup(18, gpio.IN, pull_up_down=gpio.PUD_DOWN)
    gpio.add_event_detect(18, gpio.RISING)
    
    callback = make_callback(r, myPmu)
    gpio.add_event_callback(18, callback)

    myPmu.run()