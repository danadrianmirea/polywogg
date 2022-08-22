# This program splices image data into a running WASM-4 program.
# It uses scanmem to search for sentinel values
# that are generated by png2src.sh and included into the program,
# on either side of the image data.

# For consistency, it uses `w4 png2src` to parse PNGs to image data bytes,
# rather than some Python library.

# TODO: look into using libscanmem, rather than the scanmem CLI

import argparse
import configparser
import re
import getpass
import os
from subprocess import run, Popen, PIPE, STDOUT


parser = argparse.ArgumentParser(description = "Splice data into memory between a start and end sentinel.")

parser.add_argument("target_file", metavar = "target-file", type = str, help = "png file to hot-swap in memory")

parser.add_argument("--w4", metavar = "path", type = str, help = "path to the WASM-4 binary 'w4'")

args = parser.parse_args()

recommended_cmd = 'sudo env "PATH=$PATH" python3 src/png2mem.py'

if args.w4:
    w4 = args.w4
else:
	w4_paths = run(["which", "w4"], capture_output=True).stdout.decode().splitlines()
	if len(w4_paths) == 0:
		print("w4 not found in PATH!")
		print("Note that this script must be run with `%s` in order to preserve the PATH." % (recommended_cmd,))
		print("PATH: ", os.environ["PATH"])
		exit(1)
	w4 = w4_paths[0]

target_file = args.target_file

if getpass.getuser() != "root":
	# print("This script must be run as root. Use `%s`" % (recommended_cmd,))
	# exit(1)
	print("This script should be run as root, using `%s`" % (recommended_cmd,))
	print("Continuing on, in case it works anyways...")


config = configparser.ConfigParser()
config.read('build/png2src-generated/png2mem.ini')


target_p_name = 'wasm4-linux'
matching_pids = run(['pgrep', target_p_name], capture_output=True).stdout.decode().splitlines()
if len(matching_pids) == 0:
	print("Target process %s not found!" % target_p_name)
	exit(1)

target_pid = matching_pids[0]

p = Popen(['scanmem', '--pid', target_pid], stdout=PIPE, stdin=PIPE, stderr=PIPE)

if target_file not in config.sections():
	print("File '%s' not found in ini file. Sections found: %a" % (target_file, config.sections()))
	exit(1)

# Get bytes for start and end sentinels, already formatted for use in scanmem
START_SENTINEL_BYTES_SCANMEM = config.get(target_file, "START_SENTINEL_BYTES_SCANMEM").strip()
END_SENTINEL_BYTES_SCANMEM = config.get(target_file, "END_SENTINEL_BYTES_SCANMEM").strip()

print("START_SENTINEL_BYTES_SCANMEM: ", START_SENTINEL_BYTES_SCANMEM)
print("END_SENTINEL_BYTES_SCANMEM:   ", END_SENTINEL_BYTES_SCANMEM)

scanmem_commands=[
	"option scan_data_type bytearray",
	"reset",
	START_SENTINEL_BYTES_SCANMEM,
	"list",
	"reset",
	END_SENTINEL_BYTES_SCANMEM,
	"list",
]
stdout_data, stderr_data = p.communicate(input="\n".join(scanmem_commands).encode())
print("stdout:\n    " + "\n    ".join(stdout_data.decode().splitlines()))
print("stderr:\n    " + "\n    ".join(stderr_data.decode().splitlines()))

matches = re.findall(r"\[\s*\d+\]\s([0-9a-fA-F]+),.*,\s*((?:[0-9a-fA-F]{2}\s*)+),\s*\[bytearray\]", stdout_data.decode())
print("matches:", matches)

starts = [] # start of range (i.e. location AFTER start sentinel), not location of start sentinel
ends = [] # end of range == location of end sentinel
NUM_START_SENTINEL_BYTES = len(START_SENTINEL_BYTES_SCANMEM.split(" "))
for match in matches:
	if match[1].lower().strip() == START_SENTINEL_BYTES_SCANMEM.lower().strip():
		starts.append(int(match[0], 16) + NUM_START_SENTINEL_BYTES)
	elif match[1].lower().strip() == END_SENTINEL_BYTES_SCANMEM.lower().strip():
		ends.append(int(match[0], 16))
	else:
		print("Warning: matched memory address that doesn't match the search bytes!")
		print("Address:                           "+match[0])
		print("Bytes at address:                  "+match[1])
		print("Expected bytes for start sentinel: "+START_SENTINEL_BYTES_SCANMEM)
		print("Expected bytes for end sentinel:   "+END_SENTINEL_BYTES_SCANMEM)

print("starts:", starts)
print("ends:", ends)

# get new bytes to splice in
ran = run([w4, "png2src", "--template", "src/png2src-template.txt.mustache", target_file], capture_output=True)
image_data_str = ran.stdout.decode().strip()
if len(ran.stderr) > 0:
	print("w4 png2src command failed:\n", ran.stderr.decode())
	exit(1)
# "0x00, 0xFF" -> "00 FF"
image_data_bytes = [int(byte_str, 0) for byte_str in image_data_str.split(",")]
image_data_bytes_scanmem = " ".join(re.findall(r"0x([0-9a-fA-F]{2})", image_data_str))
print("image_data_str:", image_data_str)
print("image_data_bytes_scanmem:", image_data_bytes_scanmem)

# match up starts and ends, and sanity-check length of ranges
valid_starts = []
for start in starts:
	valid = False
	for end in ends:
		if end - start == len(image_data_bytes):
			valid = True
	if valid:
		valid_starts.append(start)
	else:
		print("Warning: invalid range - didn't find an end sentinel %d bytes after the start sentinel %x" % (len(image_data_bytes), start))

# splice the bytes into the program's memory
scanmem_commands=["reset"]
for start in valid_starts:
	scanmem_commands.append("write bytearray %x %s" % (start, image_data_bytes_scanmem))

# need a new process if using communicate()
p = Popen(['scanmem', '--pid', target_pid], stdout=PIPE, stdin=PIPE, stderr=PIPE)

stdout_data, stderr_data = p.communicate(input="\n".join(scanmem_commands).encode())
print("stdout:\n    " + "\n    ".join(stdout_data.decode().splitlines()))
print("stderr:\n    " + "\n    ".join(stderr_data.decode().splitlines()))

# The end!
print("\nDone. Hot-swapped %s" % (target_file,))
