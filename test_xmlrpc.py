import sys
import subprocess
import time
import xmlrpc.client
import os
import soundfile as sf
import numpy as np
import tempfile

p = subprocess.Popen(
    ['c:\\Jarvis-assistant\\rvc_env\\Scripts\\python.exe', 'c:\\Jarvis-assistant\\rvc_server_xmlrpc.py', 'c:\\Jarvis-assistant\\rvc_env\\RVC', '54321'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print('Started XMLRPC server')

# wait for READY
while True:
    line = p.stdout.readline()
    print("Log:", line.strip())
    if "READY" in line:
        break
    if not line:
        print("Server died")
        sys.exit(1)

client = xmlrpc.client.ServerProxy("http://127.0.0.1:54321", allow_none=True)

sr = 24000
arr = np.random.randn(sr).astype(np.float32) * 0.1
in_fd, in_path = tempfile.mkstemp(suffix=".wav")
out_fd, out_path = tempfile.mkstemp(suffix=".wav")
os.close(in_fd)
os.close(out_fd)

sf.write(in_path, arr, sr)

print('Sending RPC request...')
res = client.infer(in_path, out_path, 0)
print('Result:', res)

p.terminate()
os.remove(in_path)
if os.path.exists(out_path):
    os.remove(out_path)
