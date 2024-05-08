import math
import time
from pylsl import StreamInfo, StreamOutlet

def sine_wave_example():
    # Create a new StreamInfo and StreamOutlet
    info = StreamInfo('SineWave', 'EEG', 1, 10, 'float32', 'myuid34234')
    outlet = StreamOutlet(info)

    print("Sending data...")
    start_time = time.time()
    while True:
        elapsed_time = time.time() - start_time
        # Generate a sine wave
        sample = [math.sin(2 * math.pi * elapsed_time)]
        # Push sample to LSL
        outlet.push_sample(sample)
        time.sleep(0.1)

if __name__ == '__main__':
    sine_wave_example()
