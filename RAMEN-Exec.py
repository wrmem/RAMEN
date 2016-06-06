#Reliable AutoMation Engine for Networking (RAMEN) Execution Tool
#This tool utilizes Paramiko to run scripted commands against a list of devices and log the results
#
#RAMEN is released under the GNU General Public License
#
#See the included tutorial for usage instructions
#Be sure to use -h to see all available arguments
#
#Leverage the RAMEN Parser Tool to find interesting information in command output and control 
#script execution. 
#
#This tool has only been tested with IOS / IOS-XE. Don't use it with ASAs, WLCs, IOS-XR, etc.
#
#Disclaimer:
#THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
#SHALL THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF 
#USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#Version 1.00
#Change log:

vernum = "1.00"

import paramiko
import logging
import time
import sys
import csv
import getpass
import string
import argparse
import re
import smtplib
import base64
import subprocess
import StringIO
import os.path

# Get CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("-script", "-s", type=str, help="Filename of scripted commands to execute")
parser.add_argument("-devices", "-d", type=str, help="Filename of device IPs/hostnames")
parser.add_argument("-results", "-r", type=str, help="Filename of results CSV file (default lastrun.csv)")
parser.add_argument("-username", "-u", type=str, help="Username for logging into devices")
parser.add_argument("-password", "-p", type=str, help="Password for logging into devices")
parser.add_argument("-alltext", "-t", action='store_true', help="Force all output to TXT files instead of embedding in the CSV")
parser.add_argument("-forcefail", "-f", action='store_true', help="Config mode errors abort script w/o continue option")
parser.add_argument("-fixit", type=str, help="Switch to fixit mode, provide filename of CSV generated by the Parser")
parser.add_argument("-batch", type=str, help="Switch to batch mode, provide filename of CSV with devices and commands")
parser.add_argument("-mailto", "-mt", type=str, help="Email output CSV to this address")
parser.add_argument("-mailfrom", "-mf", type=str, help="Email from this address")
parser.add_argument("-mailsubj", "-ms", type=str, help="Email subject line in quotes")
parser.add_argument("-mailrelay", "-mr", type=str, help="Email relay server")
parser.add_argument("-append", "-ap", action='store_true', help="Append results file rather than overwrite")
parser.add_argument("-parse", type=str, help="Optionally, start RAMEN-Parser on completion. Place quotes around the list of command options for it.\n Example: -parse \"-input lastrun.csv -exam exam.txt -output results.csv\"")
args = parser.parse_args()

def disclaimer():
	if os.path.isfile("masterlog.csv"):
		return
	else:
		print "\nDisclaimer:"
		print "Welcome to RAMEN, the Reliable AutoMation Engine for Networking\n"
		print "This software is released under the GNU GPL\n"
		print "THIS SOFTWARE IS PROVIDED \"AS IS\" AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF  USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
		print "\n"
		print "Press 'y' to accept the terms of this software"
		disclaimer_accept = raw_input("(y/n)")
		if disclaimer_accept == "y" or disclaimer_accept == "Y":
			return
		else:
			sys.exit()
	
def make_connection(device_ip, username, password, client):
	next_dev = False
	try: 
		client.connect(device_ip, username=username, password=password, look_for_keys=False, allow_agent=False)
		remote_con = client.invoke_shell()
		remote_con.settimeout(3)
	except KeyboardInterrupt:
		print "Keyboard interrupt received"
		sys.exit()
	except:
		print "\n\n*********Login or connection failure to %s*********" % device_ip
		with open('masterlog.csv', 'ab') as mastercsvfile:
			now = time.strftime("%c")
			master_writer = csv.writer(mastercsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			master_writer.writerow(["Failed", now, device_ip, "Login Failure","Login Failure"])
		with open(results_file, 'ab') as resultscsvfile:
			now = time.strftime("%c")
			results_writer = csv.writer(resultscsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			results_writer.writerow(["Failed", now, device_ip, "Login Failure","Login Failure"])
		time.sleep(1)	#Wait briefly so it's easier to kill the script before your account locks out
		next_dev = True
		remote_con = ""
		prev_ip = device_ip 
		login_fail = True
		return next_dev, remote_con, prev_ip, login_fail
	prev_ip = ""
	login_fail = False
	print "\n\n*********SSH connection established to %s*********" % device_ip
	return next_dev, remote_con, prev_ip, login_fail

def disable_paging(remote_con, rtr_prompt):
	# Disable paging
	try:
		remote_con.send("terminal length 0\n")
	except:
		print "         ERROR: SSH connection lost to device"
		logger("Failed",device_ip,"terminal length 0","SSH connection lost")
		failed_prompt()
		next_dev = True
		return next_dev
	
	# Check that the command was successful
	output = ""
	lastrxdatatime = time.time()
	while True:
		time.sleep(.5)
		try:
			#If no data, waits up to 3 seconds
			rcv_data = remote_con.recv(100000)
			if len(rcv_data) > 0: 
				lastrxdatatime = time.time()
		except:
			rcv_data = ""
		output = output + rcv_data
		returned_prompt = output.split('\n')[-1]
		if returned_prompt == rtr_prompt:
			next_dev, confmode, copy_mode = syntax_check(False, False, False, "terminal length 0", output, False, False)
			return next_dev
		#NX-OS workaround
		if returned_prompt.strip() == rtr_prompt:
			next_dev, confmode, copy_mode = syntax_check(False, False, False, "terminal length 0", output, False, False)
			return next_dev
		if 10 < (time.time() - lastrxdatatime):
			print "         ERROR: Failed setting terminal length 0, skipping this device"
			logger("Failed",device_ip,"terminal length 0","Failed to get prompt back")
			failed_prompt()
			next_dev = True
			return next_dev

def get_prompt(remote_con,results_file):
	# Get the prompt
	output = ""
	lastrxdatatime = time.time()
	while True:
		time.sleep(.5)
		try:
			#If no data, waits remote_con timeout value of 2 seconds
			rcv_data = remote_con.recv(100000)
			if len(rcv_data) > 0: 
				lastrxdatatime = time.time()                          
		except:
			rcv_data = ""
		output = output + rcv_data
		output_lines = output.split('\n')
		rtr_prompt = output_lines[-1].strip()
		if "#" in rtr_prompt or ">" in rtr_prompt:
			prompt_state = True
			return rtr_prompt, prompt_state
		if 10 < (time.time() - lastrxdatatime):
			print "         ERROR: Didn't find the router's prompt, stopping script on this device"
			log_login_state_failure(results_file)
			prompt_state = False
			return rtr_prompt, prompt_state

def logger(status, device_ip, command_entry, output):
	# Log to masterlog.csv and results file (lastrun.csv)
	with open('masterlog.csv', 'ab') as mastercsvfile:
		now = time.strftime("%c")
		master_writer = csv.writer(mastercsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		if bigoutput == False and args.alltext == False:
			master_writer.writerow([status, now, device_ip, command_entry.strip('\n'), output])
		elif bigoutput == False and args.alltext == True:
			master_writer.writerow([status, now, device_ip, command_entry.strip('\n'), output])
		else:
			master_writer.writerow([status, now, device_ip, command_entry.strip('\n'), "Truncated: " + output])

	with open(results_file, 'ab') as resultscsvfile:
		now = time.strftime("%c")
		results_writer = csv.writer(resultscsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		if bigoutput == False and args.alltext == False:
			results_writer.writerow([status, now, device_ip, command_entry.strip('\n'), output])
		else:
			results_writer.writerow([status, now, device_ip, command_entry.strip('\n'), "*See " + filename])

def biglogger(device_ip, output, command_entry, filename):
	# Append command output to per device text file
	print "         Saving full output to %s" % filename
	filename = "TextLogs\\" + str(filename)
	with open(filename, 'ab') as f:
		now = time.strftime("%c")
		header = "\r\n" + "******************* Executed " + command_entry + " at " + now + " *******************"
		f.write(header)
		f.write(" \r\n")
		f.write(output)
	
def failed_prompt():
	# Something failed, see if the user wants to continue on the next device
	if args.forcefail == True:
		sys.exit()
	else:
		print "\nThe script will stop on this device. Start script on next device (y/n)?" 
		answer = raw_input(">")
		while True:
			if answer == 'n' or answer == 'N':
				sys.exit()
			if answer == 'y' or answer == 'Y':
				break
			print "(y/n)?"
			answer = raw_input(">")
	
def startup():
	# Get info that wasn't provided by CLI arguments
	print "\n******************************"
	print "* RAMEN Execution Tool v%s *" % vernum
	print "******************************\n"
	disclaimer()
	if args.script and args.fixit:
		print "Can't specify a script and fixit mode"
		sys.exit()
	if args.devices and args.fixit:
		print "Can't specify a device list and fixit mode"
		sys.exit()
	if args.devices and args.batch:
		print "Can't specify a device list and batch mode"
		sys.exit()
	if args.script and args.batch:
		print "Can't specify a script and batch mode"
		sys.exit()
	if args.fixit and args.batch:
		print "Can't specify batch and fixit mode"
		sys.exit()
	if not args.username:
		print "Enter username for logging into devices"
		username = raw_input("username=")
	else:
		username = args.username
	if not args.password:
		print "Enter password for logging into devices"
		password1 = getpass.getpass("password=")
		print "Confirm password"
		password2 = getpass.getpass("password=")
		if password1 != password2:
			print "Passwords didn't match"
			sys.exit()
		else:
			password = password1
	else:
		password = args.password
	if not args.script and not args.fixit and not args.batch:
		print "Enter the filename of the script to execute"
		commands_file = raw_input("filename=")
	else:
		commands_file = args.script
	if not args.devices and not args.fixit and not args.batch:
		print "Enter the filename of device IPs to execute against"
		devices_file = raw_input("filename=")
	else:
		devices_file = args.devices
	if not args.results:
		results_file = 'lastrun.csv'
	else:
		results_file = args.results
	if args.fixit:
		fixitmode = True
	else:
		fixitmode = False
	if args.batch:
		batchmode = True
	else:
		batchmode = False

	if fixitmode == False and batchmode == False:
		print "\nThe commands in %s will be applied to the devices in %s." % (commands_file, devices_file)
	elif fixitmode == True and batchmode == False:
		print "\nThe devices in %s will be fixed with the specified fixit scripts." % args.fixit
	elif fixitmode == False and batchmode == True:
		print "\nThe batch file %s will be executed." % args.batch
	else:
		sys.exit()
	print "Press Ctrl+Break to abort...."
	print "\nExecuting..."
	bigoutput = False

	# Wipe results file
	if not args.append:
		with open(results_file, 'wb') as resultscsvfile:
			resultscsvfile.write("")

	# Add header to masterlog and results files
	if not args.append:
		with open('masterlog.csv', 'ab') as mastercsvfile:
			now = time.strftime("%c")
			master_writer = csv.writer(mastercsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			master_writer.writerow(["Executed by %s" % (username), now, "***********", "***********", "***********"])
			
		with open(results_file, 'ab') as resultscsvfile:
			now = time.strftime("%c")
			results_writer = csv.writer(resultscsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
			results_writer.writerow(["Executed by %s" % (username), now, "***********", "***********", "***********"])
		
	return username, password, commands_file, devices_file, results_file, fixitmode, batchmode

def log_login_state_success(results_file):
	# Log login success to files
	with open('masterlog.csv', 'ab') as mastercsvfile:
		now = time.strftime("%c")
		master_writer = csv.writer(mastercsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		master_writer.writerow(["Success", now, device_ip, "Login Success",rtr_prompt])

	with open(results_file, 'ab') as resultscsvfile:
		now = time.strftime("%c")
		results_writer = csv.writer(resultscsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		results_writer.writerow(["Success", now, device_ip, "Login Success",rtr_prompt])

def log_login_state_failure(results_file):
	# Log login failure to files
	with open('masterlog.csv', 'ab') as mastercsvfile:
		now = time.strftime("%c")
		master_writer = csv.writer(mastercsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		master_writer.writerow(["Failed", now, device_ip, "Failed to get router prompt after login",""])

	with open(results_file, 'ab') as resultscsvfile:
		now = time.strftime("%c")
		results_writer = csv.writer(resultscsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		results_writer.writerow(["Failed", now, device_ip, "Failed to get router prompt after login",""])

def banner_check(banner_mode, command_entry, banner_exit_char):	
	# Check if we need to exit banner mode during config
	if banner_mode == True:
		if banner_exit_char in command_entry:
			banner_mode = False
	
	# Check if we need to enter banner mode during config
	if confmode == True and command_entry.startswith("banner ") and banner_mode == False:
		banner_mode = True
		command_length = len(command_entry)
		for c in range(1, command_length):
			banner_exit_char = command_entry[-c:]
			banner_exit_char = banner_exit_char.strip()
			if banner_exit_char == "":
				continue 
			else:
				break
		if banner_exit_char == "":
			print "Didn't get the banner end char, exiting"
			sys.exit()
	return banner_mode, banner_exit_char

def copy_check(command_entry, banner_mode, copy_mode):
	# Check if we're being prompted for copy commands
	if command_entry.startswith("copy ") and banner_mode == False:
		copy_mode = True
		return copy_mode
	return copy_mode
	
def output_collector(output, command_entry, banner_mode, banner_mode_counter, copy_mode, pt_mode, rtr_prompt):
	# Get output from command, timeout if no output for 65 seconds
	# We wait 65 seconds since some commands (like file copies) have a 60 second timeout
	lastrxdatatime = time.time()
	while True:
		time.sleep(.5)
		# Check if more output has been returned from the device
		try:
			rcv_data = remote_con.recv(1000000)
			if len(rcv_data) > 0: 
				lastrxdatatime = time.time()                          
		except:
			rcv_data = ""
		output = output + rcv_data
		# Check that we got back to the prompt
		returned_prompt = output.split('\n')[-1]
		config_prompt = rtr_prompt.translate(None, ' >#') + "(config" 
		copy_prompt = "]?"
		if returned_prompt == rtr_prompt:
			pt_mode = False
			break
		#NX-OS workaround
		if returned_prompt.strip() == rtr_prompt:
			pt_mode = False
			break
		config_prompt2 = config_prompt.strip()
		returned_prompt2 = returned_prompt.strip()
		#Config mode prompt
		if returned_prompt.startswith(config_prompt):
			pt_mode = False
			break
		elif returned_prompt2.startswith(config_prompt2):
			pt_mode = False
			break
		#Enable password prompt
		if command_entry.startswith('en') and returned_prompt.startswith("Password:"):
			rtr_prompt = rtr_prompt.replace(">", "#")
			rtr_prompt = rtr_prompt.strip()
			break
		#Disabled
		if command_entry.startswith('disa') and returned_prompt == rtr_prompt.replace("#", ">"):
			rtr_prompt = rtr_prompt.replace("#", ">")
			rtr_prompt = rtr_prompt.strip()
			break
		#Other special modes
		if copy_mode == True:
			stripped_prompt = returned_prompt.strip()
			if stripped_prompt.endswith(copy_prompt):
				break
		elif pt_mode == True:
			stripped_prompt = returned_prompt.strip()
			if stripped_prompt.endswith(":"):
				break
		elif banner_mode == True:
			banner_mode_counter = banner_mode_counter + 1
			if banner_mode_counter > 65:
				print "         ERROR: Didn't get back the prompt during banner config, exiting"
				logger("Failed",device_ip,command_entry,"Time out:" + output)
				sys.exit()
			return output, returned_prompt, banner_mode, banner_mode_counter, pt_mode
		elif "% You already have RSA keys defined" in output:
			stripped_prompt = returned_prompt.strip()
			if stripped_prompt.endswith(":"):
				break
		elif "How many bits in the modulus" in output:
			stripped_prompt = returned_prompt.strip()
			if stripped_prompt.endswith(":"):
				break
		# Bail out if no new data received for 65 seconds		
		if 65 < (time.time() - lastrxdatatime):
			print "         ERROR: Didn't get the standard prompt back, exiting"
			print returned_prompt
			logger("Failed",device_ip,command_entry,"Time out:" + output)
			sys.exit()
	return output, returned_prompt, banner_mode, banner_mode_counter, copy_mode, pt_mode, rtr_prompt
			
def big_output_check(output, bigoutput, length_warn):
	# Write full output to text file, then truncate output variable to ~32K
    if len(output) > 32000 and args.alltext == False:
        print "         Warning: More than 32K returned, CSV will reference external file"
        length_warn = True
        biglogger(device_ip, output, command_entry, filename)
        output = output[0:32000]
        bigoutput = True	
    return bigoutput, length_warn, output

def shunt_txt(bigoutput, output):
	# Write all output to text files because the user told us to, still truncate if its over 32K
	if args.alltext == True:                     
		biglogger(device_ip, output, command_entry, filename)
		if len(output) > 32000:
			output = output[0:32000]
		bigoutput = True
	return bigoutput, output
	
def conf_check(confmode, command_entry, output, rtr_prompt, returned_prompt):
	# Check for configure mode 
	next_dev = False
	if "conf" in command_entry and "Enter configuration commands" in output:
		confmode = True
	if confmode == True:
		num_lines = output.count('\n')
		# Check for acceptable, multiline config responses
		if num_lines > 1:
			# Entered config mode
			if "Enter configuration commands" in output:
				pass
			# Ignore portfast config
			elif "portfast should only" in output:
				pass
			# Ignore exit of config mode
			elif "SYS-5-CONFIG_I: Configured from" in output:
				pass
			# Ignore key generation for https and ssh
			elif "You already have RSA keys defined" in output or "Choose the size of the key modulus" in output or "keys will be non-exportable" in output:
				pass
			# Ignore banner config
			elif "Enter TEXT message" in output:
				pass
			# Ignore SSH warning
			elif "Please create RSA keys to enable SSH" in output:
				pass
			# Ignore BGP timer warning
			elif "Warning: A hold time of less" in output:
				pass
			# Ignore VTP config
			elif "Setting device to VTP" in output:
				pass
			# Ignore defaulting interface
			elif "set to default configuration" in output:
				pass
			# Ignore VLAN change message
			elif "Applying VLAN changes may take few minutes" in output:
				pass
			else:
				# Something else happened, it may not be ok so it's best to fail
				print output
				print "\nERROR: Syntax error or unhandled response during config."
				logger("Failed",device_ip,command_entry,output)
				failed_prompt()
				next_dev = True
				return confmode, next_dev
		# Check if we're exiting config mode
		if returned_prompt == rtr_prompt or returned_prompt.strip() == rtr_prompt:
			confmode = False

	return confmode, next_dev

def syntax_check(confmode, next_dev, failure, command_entry, output, copy_mode, pt_mode):
	# Check for syntax failures 
	if "Invalid input" in output:
		print "         ERROR: \"Invalid input\" returned from device"
		if confmode == True:
			logger("Failed",device_ip,command_entry,output)
			failed_prompt()
			next_dev = True
			return next_dev, confmode, copy_mode
		else:
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check for unknown command
	if "Unknown command" in output:
		print "         ERROR: \"Unknown command\" returned from device"
		if confmode == True:
			logger("Failed",device_ip,command_entry,output)
			failed_prompt()
			next_dev = True
			return next_dev, confmode, copy_mode
		else:
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check for incomplete command
	if "Incomplete command" in output:
		print "         ERROR: \"Incomplete command\" returned from device"
		if confmode == True:
			logger("Failed",device_ip,command_entry,output)
			failed_prompt()
			next_dev = True
			return next_dev, confmode, copy_mode
		else:
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check for ambiguous command
	if "Ambiguous command" in output:
		print "         ERROR: \"Ambiguous command\" returned from device"
		if confmode == True:
			logger("Failed",device_ip,command_entry,output)
			failed_prompt()
			next_dev = True
			return next_dev, confmode, copy_mode
		else:
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check for unrecognized command
	if "% Unrecognized command" in output:
		print "         ERROR: \"Unrecognized command\" returned from device"
		if confmode == True:
			logger("Failed",device_ip,command_entry,output)
			failed_prompt()
			next_dev = True
			return next_dev, confmode, copy_mode
		else:
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check for failed copy command:
	if copy_mode == True and "%Error" in output:
		print "         ERROR: Error during file copy"
		logger("Failed",device_ip,command_entry,output)
		copy_mode = False
		failed_prompt()
		next_dev = True
		return next_dev, confmode, copy_mode
	if copy_mode == True and "[OK" in output:
		copy_mode = False
	# Check ping
	if (command_entry.startswith("pi") and confmode == False) or pt_mode == True:
		if "]:" in output or "address:" in output:
			logger("Indeterminate",device_ip,command_entry,output)
			return next_dev, confmode, copy_mode
	if "!" not in output and "-byte ICMP Echos to" in output:
			print "         ERROR: Ping unsuccessful"
			logger("Failed",device_ip,command_entry,output)
			failure = True
	# Check traceroute
	if (command_entry.startswith("tra") and confmode == False) or pt_mode == True:
		if "]:" in output or "address:" in output:
			logger("Indeterminate",device_ip,command_entry,output)
			return next_dev, confmode, copy_mode
	if " *" in output.split('\n')[-2] and "msec" not in output.split('\n')[-2] and "Tracing the route" in output and output.split('\n')[-1] == rtr_prompt:
		print "         ERROR: Traceroute returned timeout on last hop" 
		logger("Failed",device_ip,command_entry,output)
		failure = True
	# Catch other errors
	if "% Error" in output or "% Unknown" in output or ("is not an open connection" in output and "%" in output):
		print "         ERROR: Unexpected output received"
		logger("Failed",device_ip,command_entry,output)
		failure = True
	# All above checks ok, log success
	if failure == False and command_entry != "terminal length 0":
		logger("Success",device_ip,command_entry,output)
		
	return next_dev, confmode, copy_mode

def check_module(device_ip, results_file, check_script, username, password):
	failure = False
	fail_action = "quit"
	check_script_items = check_script.split(",")
	if len(check_script_items) == 2: 
		check_script_name = check_script_items[0].strip()
		check_script_exam = check_script_items[1].strip()
		fail_action = "quit"
	elif len(check_script_items) == 3:
		check_script_name = check_script_items[0].strip()
		check_script_exam = check_script_items[1].strip()
		fail_action = check_script_items[2].strip()
		fail_action = fail_action.lower()
		if fail_action == "quit" or fail_action == "skip" or fail_action == "continue":
			pass
		else:
			print "Invalid action specified, defaulting to \"quit\""
			fail_action = "quit"
	else:
		return "Failure", fail_action 
	temp_devices = open("device.tmp", 'w')
	temp_devices.write(device_ip)
	temp_devices.close()
	try:
		if os.path.isfile(check_script_name) and os.path.isfile(check_script_exam):
			#Given a script file and exam file
			cmd = "python RAMEN-Exec.py -append -devices device.tmp -script %s -results %s -username %s -password %s -forcefail -parse \"-input %s -exam %s -output temp-parse.csv\"" % (check_script_name, results_file, username, password, results_file, check_script_exam)
			p = subprocess.Popen(cmd, shell = True, stdout=subprocess.PIPE)
			p.wait()
		elif not os.path.isfile(check_script_name) and os.path.isfile(check_script_exam):
			#Given a command and exam file
			temp_script = open('script.tmp', 'w')
			temp_script.write(check_script_name)
			temp_script.close()
			cmd = "python RAMEN-Exec.py -append -devices device.tmp -script script.tmp -results %s -username %s -password %s -forcefail -parse \"-input %s -exam %s -output temp-parse.csv\"" % (results_file, username, password, results_file, check_script_exam)
			p = subprocess.Popen(cmd, shell = True, stdout=subprocess.PIPE)
			p.wait()
			os.remove('script.tmp')
		elif os.path.isfile(check_script_name) and not os.path.isfile(check_script_exam):
			#Given a script file and an exam module
			temp_exam = open("exam.tmp", 'w')
			temp_exam.write(check_script_exam)
			temp_exam.close()
			cmd = "python RAMEN-Exec.py -append -devices device.tmp -script %s -results %s -username %s -password %s -forcefail -parse \"-input %s -exam %s -output temp-parse.csv\"" % (check_script_name, results_file, username, password, results_file, check_script_exam)
			p = subprocess.Popen(cmd, shell = True, stdout=subprocess.PIPE)
			p.wait()
			os.remove('exam.tmp')
		else:
			#Given a command and an exam module
			temp_exam = open("exam.tmp", 'w')
			temp_exam.write(check_script_exam)
			temp_exam.close()
			temp_script = open('script.tmp', 'w')
			temp_script.write(check_script_name)
			temp_script.close()
			cmd = "python RAMEN-Exec.py -append -devices device.tmp -script script.tmp -results %s -username %s -password %s -forcefail -parse \"-input %s -exam exam.tmp -output temp-parse.csv\"" % (results_file, username, password, results_file)
			p = subprocess.Popen(cmd, shell = True, stdout=subprocess.PIPE)
			p.wait()
			os.remove('script.tmp')
			os.remove('exam.tmp')
		os.remove("device.tmp")
		with open("temp-parse.csv", 'rb') as parsedresults:
			reader = csv.reader(parsedresults)
			for line in reader:
				if "Device IP" in line[0]:
					continue
				if line[2] != "Ok":
					failure = True
		if failure == True:
			return "Failure", fail_action
		else:
			return "Ok", fail_action
			os.remove("temp-parse.csv")
	except:
		print "Error processing check script. Faulty module?\n"
		os.remove("device.tmp")
		return "Failure", fail_action

def email_results(results_file):
	#Email the results if asked to
	if not args.mailto:
		return
	else:
		receiver = args.mailto
	
	if not args.mailrelay:
		mailrelay = "localhost"
	else:
		mailrelay = args.mailrelay
	
	if not args.mailfrom:
		sender = "RAMEN-Exec@domain.com"
	else:
		sender = args.mailfrom
		
	if not args.mailsubj:
		subj = "RAMEN-Exec Results"
	else:
		subj = args.mailsubj
	
	now = time.strftime("%c")
	body = "RAMEN-Exec Results attached. Execution time %s" % now
	marker = "3jkd8sk3d0fkg9gkem23m29d90cv98b8ws"
	
	# Read in the attachment and encode it
	fo = open(results_file, "rb")
	filecontent = fo.read()
	encodedcontent = base64.b64encode(filecontent)  

	# Define the main headers.
	part1 = """From: RAMEN-Exec Parser <%s>
To: <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (sender, receiver, subj, marker, marker)

	# Define the message action
	part2 = """Content-Type: text/plain
Content-Transfer-Encoding:8bit

%s

--%s
""" % (body, marker)

	# Define the attachment section
	part3 = """Content-Type: multipart/mixed; name=\"%s\"
Content-Transfer-Encoding:base64
Content-Disposition: attachment; filename=%s

%s
--%s--
""" %(results_file, results_file, encodedcontent, marker)

	
	# Assemble message
	message = part1 + part2 + part3

	# Send message
	try:
		smtpObj = smtplib.SMTP(mailrelay)
		smtpObj.sendmail(sender, receiver, message)
		print "\n  Successfully sent email"
	except Exception:
		print "Error: unable to send email"
	
	return



# Main
if __name__ == '__main__':

	#Unpack args, get missing info
	username, password, commands_file, device_file, results_file, fixitmode, batchmode = startup()
	
	# Initiate SSH connection
	logging.basicConfig()
	client = paramiko.SSHClient()
    
	# Add untrusted hosts
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	
    # Start logging into devices and running commands
	if fixitmode == True:
		devices_file = open(args.fixit,"rb")
	elif batchmode == True:
		devices_file = open(args.batch,"rb")
	else:
		devices_file = open(device_file,"rb")
	length_warn = False
	prev_ip = ""
	login_fail = False
	commands = ""
	multiline = False
	for device_ip in devices_file:
		#Exclude banner of Parser's results file
		if "Device IP," in device_ip:
			continue
		#Empty line, get next line
		if device_ip.strip() == "" or device_ip.strip('\"') == "":
			continue
		next_dev = False
		banner_exit_char = ""

		#If not in fixit mode, text of device_ip should be an IP or hostname
		if fixitmode == False and batchmode == False:
			#Normal mode
			device_ip = device_ip.strip()
		elif batchmode == True:
			#Batch mode
			batch_fields = device_ip.split(",")
			if multiline == False:
				device_ip = batch_fields[0].strip()
				device_ip = device_ip.strip('\"')
				batch_fields[1] = batch_fields[1].strip()
				if batch_fields[1].startswith('\"') and not batch_fields[1].endswith('\"'):
					multiline = True
					commands = batch_fields[1].strip('\"') + "\r\n"
				else:
					commands = batch_fields[1].strip('\"') + "\r\n"

			else:
				device_ip = prev_ip
				batch_fields[0] = batch_fields[0].strip()
				if batch_fields[0].endswith('\"'):
					multiline = False
					commands = batch_fields[0].strip('\"')
				else:
					commands = batch_fields[0].strip('\"')
		else:
			#Fixit mode
			fixit_fields = device_ip.split(",")
			if fixit_fields[2].strip('\"') == "Failed" and fixit_fields[4].strip('\"') != "":
				device_ip = fixit_fields[0].strip()
				device_ip = device_ip.strip('\"')
			else:
				#This device doesn't need fixing, continue to top of loop
				continue

		filename = device_ip + "-" + time.strftime("%m%d%Y-") + time.strftime("%H%M%S") + ".txt"
		
        # Open connection, keep the client channel open if same IP
		if fixitmode == True or batchmode == True:
			if prev_ip == device_ip and login_fail == True:
				continue
			elif prev_ip == device_ip:
				pass
			else:
				#Close the previous session
				client.close()
				#Reset variables
				confmode = False
				banner_mode = False
				banner_mode_counter = 0
				copy_mode = False
				pt_mode = False
				#Open the new connection
				next_dev, remote_con, prev_ip, login_fail = make_connection(device_ip, username, password, client)
				if next_dev == True:
					continue
				# Get router prompt
				rtr_prompt, prompt_state = get_prompt(remote_con,results_file)
				if prompt_state == False:
					logger("Failed",device_ip,"No prompt","Failed to get the device's prompt")
					continue
				# Log successful login
				log_login_state_success(results_file)	
				# Disable paging
				next_dev = disable_paging(remote_con, rtr_prompt)
				if next_dev == True:
					continue
		else:
			#Set variables
			confmode = False
			banner_mode = False
			banner_mode_counter = 0
			copy_mode = False
			pt_mode = False
			#Open the new connection
			next_dev, remote_con, prev_ip, login_fail = make_connection(device_ip, username, password, client)
			if next_dev == True:
				continue
			# Get router prompt
			rtr_prompt, prompt_state = get_prompt(remote_con,results_file)
			if prompt_state == False:
				logger("Failed",device_ip,"No prompt","Failed to get the device's prompt")
				continue
			# Log successful login
			log_login_state_success(results_file)	
			# Disable paging
			next_dev = disable_paging(remote_con, rtr_prompt)
			if next_dev == True:
				continue


        # Load command script 
		if fixitmode == False and batchmode == False:
			script = open(commands_file)
		elif batchmode == True:
			script = StringIO.StringIO(commands)
		else:
			fixit_filename = fixit_fields[4].strip('\"')
			fixit_script = "FixitScripts\\" + fixit_filename
			script = open(fixit_script)
			if fixit_fields[4] == "Login Failure":
				continue

        # Start processing command script
		command_entry = script.readline()
		bigoutput = False
		if fixitmode == True:
			print "On %s, running script: %s" % (device_ip, fixit_filename)
			logger("Success", device_ip, "Starting script %s" % fixit_filename, "")
		
		#Iterate through command script
		while command_entry:
			failure = False
			if command_entry.startswith("do ") and banner_mode == False:
				print "Do command not supported in this program"
				logger("Failed",device_ip,command_entry,"Do command not supported in this program")
				sys.exit()
			if '\n' not in command_entry and command_entry != "":
				command_entry = command_entry + '\n'
			if command_entry.strip() == "" and pt_mode == False and banner_mode == False:
				command_entry = script.readline()
				continue
			if (command_entry.startswith("pi") or command_entry.startswith("tra")) and banner_mode == False and confmode == False:
				pt_mode = True
			if banner_mode == False and command_entry.startswith('>>'):
				check_script = command_entry.replace('>>', '')
				check_script = check_script.strip()
				logger("Success", device_ip, "Starting check script %s" % check_script, "")
				print "Starting check %s" % check_script
				status, fail_action = check_module(device_ip, results_file, check_script, username, password)
				fail_action = fail_action.lower()
				if status != 'Ok':
					logger("Failure", device_ip, "Failure during %s"  % check_script, "")
					if fail_action == 'skip':
						print "Check script returned \"Failure\", fail action \"skip\", trying next device"
						break
					elif fail_action == 'continue':
						print "Check script returned \"Failure\", fail action \"continue\", resuming script"
						command_entry = script.readline()
						continue
					else:
						print "Check script returned \"Failure\", fail action \"quit\", exiting"
						sys.exit()
				else:
					logger("Success", device_ip, "Starting check script %s" % check_script, "")
					print "Check script returned \"Ok\""
					command_entry = script.readline()
					continue
			if banner_mode == False:
				print "On %s, running command: %s" % (device_ip, command_entry.strip())
			output = ""
			bigoutput = False
					
			# Check if configuring banner
			banner_mode, banner_exit_char = banner_check(banner_mode, command_entry, banner_exit_char)
			
			# Check if performing copy operation
			copy_mode = copy_check(command_entry, banner_mode, copy_mode)
						
			# Send the command to the device
			try:
				remote_con.send(command_entry)
			except:
				print "         ERROR: SSH connection lost to device"
				logger("Failed",device_ip,command_entry,"SSH connection lost")
				failed_prompt()
				break

            # Get router response
			output, returned_prompt, banner_mode, banner_mode_counter, copy_mode, pt_mode, rtr_prompt = output_collector(output, command_entry, banner_mode, banner_mode_counter, copy_mode, pt_mode, rtr_prompt)
			
			# Excel has limit of 32K per cell, log to separate file and truncate output
			bigoutput, length_warn, output = big_output_check(output, bigoutput, length_warn)

			# Check if user wants all output shunted to TXT files
			bigoutput, output = shunt_txt(bigoutput, output)
			
			# Validate response from device - Config mode checks
			confmode, next_dev = conf_check(confmode, command_entry, output, rtr_prompt, returned_prompt)
			if next_dev == True:
				break

            # Validate response from device - Check for syntax errors
			next_dev, confmode, copy_mode = syntax_check(confmode, next_dev, failure, command_entry, output, copy_mode, pt_mode)
			if next_dev == True:
				break

			# Get the next command
			command_entry = script.readline()

		# Done with script file, close it
		script.close()
		
		# Done with this device, close the SSH session to it
		if fixitmode == False and batchmode == False:
			client.close()
		else:
			prev_ip = device_ip	#We don't know until the next line is read if we're done with this device
		
		# Clear commands variable before next loop
		commands = ""
	
	# Finish Execution Tool
	print "\n***********************************************************************"
	print "* Script complete. Check %s for log of results." % results_file
	if length_warn is True:
		print "* Some output too large for %s. Additional txt files created."	% results_file
	print "***********************************************************************"
	devices_file.close()
	
	# Optionally send email on completion
	if args.mailto:
		email_results(results_file)
	
	# Start Parser Tool if user asked to do so
	if args.parse:
		print "\n Starting parser..."
		quote_args = '""' + args.parse + '""'
		p1 = subprocess.Popen("%s %s" % ("python \"RAMEN-Parser.py\" ", quote_args))
		p1.wait()
		print "\nParser finished, exiting execution tool"

