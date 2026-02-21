import time
import subprocess
import threading

def run_set(val):
    start = time.time()
    res = subprocess.run(['ddcutil', '--sleep-multiplier', '.1', '--noverify', '--bus', '4', 'setvcp', '0x10', str(val)], capture_output=True)
    print(f"set {val} took {time.time()-start:.3f}s, code {res.returncode}, err: {res.stderr.strip()}")

threads = []
for v in [30, 40, 50, 40, 30]:
    t = threading.Thread(target=run_set, args=(v,))
    t.start()
    threads.append(t)
    time.sleep(0.05) # simulate 50ms keypress interval

for t in threads:
    t.join()
