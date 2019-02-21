# sysmon

Monitors system statistics and saves it in a csv-file format.

# Installation

## Dependencies

 * python3
 * python-psutil [Lib] *- (Optional, but highly recommended)*

## Manual installation:

    # cp sysmon.py /usr/bin/sysmon
    # chmod 440 /usr/bin/sysmon
    # chmod +x /usr/bin/sysmon

Copy the service and timer scripts:

    # cp systemd/* /etc/systemd/system/
    # systemctl enable sysmon@eno1.timer

This enables `sysmon.py` to look at the NIC `eno1`.<br>

# Running sysmon

    # systemctl enable dumper@eno1.service
    # systemctl start dumper@eno1.service

Or simply via any command line:

    # python sysmon.py --output=/root/sysinfo.csv --interface=eno1 --partition=/

# What it does

By default, `sysmon@.service` will be executed by `sysmon@.timer` every **15 min**.<br>
The information gathered by `sysmon@.service` is:

 * Free disk space on `/`
 * CPU load percentage over 200ms per sampling time
 * Free memory space
 * Packets sent and recieved on `@<nic>` above

All this information is stored under `/root/sysinfo.csv` *(or whichever is configured upon launch)*.

# Help:

Run `python sysmon.py --help` for more information.<br>
Configuration can be done in `sysmon@.service`.