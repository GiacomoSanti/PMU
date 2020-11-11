from synchrophasor.pdc import Pdc
import numpy as np
from datetime import datetime
'''
This file contains a simple implementation of a PDC used for testing the communication protocol. 
'''

pdc = Pdc(pdc_id=7, pmu_ip="127.0.0.1", pmu_port=1411)

pdc.run()  # Connect to PMU

header = pdc.get_header()  # Get header message from PMU
config = pdc.get_config()  # Get configuration from PMU

pdc.start()  # Request to start sending measurements

def get_degrees(phasors):
    degrees = []

    for p in phasors:
        d = p[1]*180/np.pi
        if d < 0:
            d += 360
        degrees.append(round(d))
    return degrees

while True:
    data = pdc.get()  # Keep receiving data
    phasors = data.get_phasors()
    degrees = get_degrees(phasors)


    print('Received: ', data.get_phasors(), '   ', degrees, '   ', datetime.fromtimestamp(data.get_soc()))
    
    if not data:
        pdc.quit()  # Close connection
        break