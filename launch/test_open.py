import subprocess
subprocess.Popen(["explorer.exe", "http://localhost:8000/"])
print("test_open: Popen call returned, no exception")
