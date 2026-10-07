import subprocess

exe = ".exe"
input = "input.pf"
output = "output.xml"

cmd = [exe, "/nc", input, output]

print(subprocess.list2cmdline(cmd))
subprocess.run(cmd)
