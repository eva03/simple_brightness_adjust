import time
import subprocess
import threading

def run_set(val):
    start = time.time()
    action = 'up' if val > 0 else 'down'
    res = subprocess.run(['./bin/brightness-control', '-m', '1', '-a', action], capture_output=True, text=True)
    print(f"action {action} took {time.time()-start:.3f}s, code {res.returncode}, err: {res.stderr.strip()}")

threads = []
for v in [1, -1, 1, -1, 1]:
    t = threading.Thread(target=run_set, args=(v,))
    t.start()
    threads.append(t)
    time.sleep(0.05)

for t in threads:
    t.join()
