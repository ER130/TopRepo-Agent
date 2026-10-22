import subprocess
proc = subprocess.Popen(["explorer.exe", "http://localhost:8000/"])
print(f"test_open: launched, pid {proc.pid}, waiting briefly")
try:
    proc.wait(timeout=5)
    print("test_open: launcher process exited on its own")
except subprocess.TimeoutExpired:
    print("test_open: still running after 5s, proceeding anyway")
