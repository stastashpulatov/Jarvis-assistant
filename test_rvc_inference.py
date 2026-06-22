import sys
import subprocess
import json
import time

p = subprocess.Popen(
    ['c:\\Jarvis-assistant\\rvc_env\\Scripts\\python.exe', 'c:\\Jarvis-assistant\\rvc_server.py', 'c:\\Jarvis-assistant\\rvc_env\\RVC'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print('Started')

while True:
    out = p.stdout.readline()
    print('Got:', repr(out))
    try:
        j = json.loads(out)
        if j.get('status') == 'ready':
            print('Server is ready!')
            break
    except:
        pass

# Now send a command
import shutil
import os
import tempfile
import numpy as np
import soundfile as sf

# Create a dummy 1-second wav file
sr = 24000
arr = np.random.randn(sr).astype(np.float32) * 0.1
in_fd, in_path = tempfile.mkstemp(suffix=".wav")
out_fd, out_path = tempfile.mkstemp(suffix=".wav")
os.close(in_fd)
os.close(out_fd)

sf.write(in_path, arr, sr)

req = {
    "input_wav": in_path,
    "output_wav": out_path,
    "pitch_shift": 0
}

print('Sending request...')
p.stdin.write(json.dumps(req) + "\n")
p.stdin.flush()

while True:
    out = p.stdout.readline()
    print('Got after req:', repr(out))
    try:
        j = json.loads(out)
        if j.get('status') in ['ok', 'error']:
            print('Result:', j)
            break
    except:
        pass

p.terminate()
os.remove(in_path)
if os.path.exists(out_path):
    os.remove(out_path)
