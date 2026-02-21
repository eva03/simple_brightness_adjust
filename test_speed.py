import time
import subprocess

def test(cmd):
    start = time.time()
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.time() - start

print(f"getvcp sleep-mult .1: {test(['ddcutil', '--sleep-multiplier', '.1', '--bus', '4', 'getvcp', '0x10']):.3f}s")
print(f"setvcp sleep-mult .1 + noverify: {test(['ddcutil', '--noverify', '--sleep-multiplier', '.1', '--bus', '4', 'setvcp', '0x10', '30']):.3f}s")
