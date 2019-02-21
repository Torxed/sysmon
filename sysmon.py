import json, sys, os, time
from subprocess import Popen, PIPE, STDOUT
try:
	import psutil
except:
	## Create a neat handle to execute system commands
	class cmd(Popen):
		def __init__(self, c, shell=True):
			self.c = c
			self.shell = shell
			self.stdout = None
			self.stdin = None
			self.stderr = None

		## Saves us a bunch of code later if we contextulize this bad boy.
		def __enter__(self, *args, **kwargs):
			super(cmd, self).__init__(self.c, shell=self.shell, stdout=PIPE, stderr=STDOUT, stdin=PIPE)
			return self

		def __exit__(self, *args, **kwargs):
			if self.stdout and self.stdin:
				self.stdin.close()
				self.stdout.close()

		def __iter__(self, *args, **kwargs):
			if not self.stdin:
				# Not opened yet
				return None

			for line in self.stdout:
				if len(line) <= 0:
					# Data was empty, return and break the iter
					return line
				yield line

	## Time to monkey patch in all the stat-functions as if the real psutil existed.
	class mem():
		def __init__(self, free, percent=-1):
			self.free = free
			self.percent = percent

	class disk():
		def __init__(self, size, free, percent):
			self.size = size
			self.free = free
			self.percent = percent

	class iostat():
		def __init__(self, interface, bytes_sent=0, bytes_recv=0):
			self.interface = interface
			self.bytes_recv = int(bytes_recv)
			self.bytes_sent = int(bytes_sent)
		def __repr__(self, *args, **kwargs):
			return f'iostat@{self.interface}[bytes_sent: {self.bytes_sent}, bytes_recv: {self.bytes_recv}]'

	class psutil():
		def cpu_percent(interval=0):
			## TODO: This just counts the ammount of time the CPU has spent. Find a better way!
			with cmd("grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'") as output:
				for line in output:
					return float(line.strip().decode('UTF-8'))
		
		def virtual_memory():
			with cmd("grep 'MemFree: ' /proc/meminfo | awk '{free=($2)} END {print free}'") as output:
				for line in output:
					return mem(float(line.strip().decode('UTF-8')))

		def disk_usage(partition):
			disk_stats = os.statvfs(partition)
			free_size = disk_stats.f_bfree * disk_stats.f_bsize
			disk_size = disk_stats.f_blocks * disk_stats.f_bsize
			percent = (100/disk_size)*disk_free
			return disk(disk_size, free_size, percent)

		def net_if_addrs():
			interfaces = {}
			for root, folders, files in os.walk('/sys/class/net/'):
				for name in folders:
					interfaces[name] = {}
			return interfaces

		def net_io_counters(pernic=True):
			data = {}
			for interface in psutil.net_if_addrs().keys():
				with cmd("grep '{interface}:' /proc/net/dev | awk '{{recv=$2}}{{send=$10}} END {{print send,recv}}'".format(interface=interface)) as output:
					for line in output:
						data[interface] = iostat(interface, *line.strip().decode('UTF-8').split(' ',1))
			return data

## Parse command-line arguments:
args = {}
positionals = []
for arg in sys.argv[1:]:
	if '--' == arg[:2]:
		if '=' in arg:
			key, val = [x.strip() for x in arg[2:].split('=')]
		else:
			key, val = arg[2:], True
		args[key] = val
	else:
		positionals.append(arg)

## And add some defaults if they are missing
if not 'output' in args: args['output'] = None
if not 'partition' in args: args['partition'] = '/'
if not 'interface' in args: args['interface'] = sorted([x for x in psutil.net_if_addrs().keys() if not x == 'lo'])[0]
if not 'verbose' in args: args['verbose'] = False

if 'help' in args:
	print("""
    Here's a short introduction:
        --output=<filename> - *appends* the data into a CSV formatted file

        --partition=/ - Which partition to get disk info from

        --interface=<name> - Which NIC to get network traffic info from

        --verbose - Enables printed output for the developer.

    Example usage:
        python sysmon.py --output=stats.csv --interface=eno1
""")
	exit(1)

info = {
	'cpu_load' : 0,
	'mem_free' : 0
}

info['cpu_load'] = psutil.cpu_percent(interval=0.5) # Grab 0.5 sec worth of sample time
info['mem_free'] = psutil.virtual_memory().free # .percent is also a thing
info['disk_free'] = psutil.disk_usage(args['partition']).free / (1024.0 ** 3) # Convert to gigabyte
packet_info = psutil.net_io_counters(pernic=True)[args['interface']]
info['packets_sent'] = packet_info.bytes_sent
info['packets_recv'] = packet_info.bytes_recv

if args['verbose']:
	print(json.dumps(info, indent=4))

if args['output']:
	birth = False
	if not os.path.isfile(args['output']):
		birth = True
	with open(args['output'], 'a') as output:
		if birth:
			output.write(','.join(["snapshot_time"]+[str(x[0]) for x in sorted(info.items(), key=lambda kv: kv[0])])+'\n')
		# Join the JSON struct into a CSV line (Sorted by keys so they stay the same)
		#         Separator                      str(value)  key,val              sorting key=[key,val][0] <- aka key and not value
		output.write(','.join([str(time.time())]+[str(x[1]) for x in sorted(info.items(), key=lambda kv: kv[0])])+'\n')