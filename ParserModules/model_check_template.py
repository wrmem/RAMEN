# This parser module checks if a device is a 2960S switch.
# It expects to be passed the output of "show inventory"
# Modify it to match other device types in your organization

def function(device_output):

	#User-defined variables
	findit = "PID: WS-C2960S-"	#Specify the leading portion of the PID
	comment = ""	#Optionally, specify a description of the issue.
	fixit = ""		#Optionally, specify a fixit script if you have written one
	
	#Do not change below here
	valid = "Failed"
	spurious = ""
	device_lines = device_output.splitlines()
	for i in device_lines:
		if findit in i:
			valid = "Ok" 
	return valid, comment, fixit, spurious