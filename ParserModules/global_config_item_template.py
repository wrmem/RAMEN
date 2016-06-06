#This template module checks for the presence of a specific command in global config mode. 
#It expects to be passed the output of show running-config
#Set the value of the "device_command" variable to the exact command you want to find.
#The script will report "Failure" if the command isn't found. 
#If you have written a fixit script, specify its name in the fixit variable

def function(device_output):

	#User-defined variables
	device_command = "service password-encryption"	#Specify the line of text you are checking for in device output
	comment = "password encryption service not enabled"	#Optionally, specify a comment telling what issue was found
	fixit = "service_password_encryption_fixit.txt"	#Optionally, specify a fixit script if you have written one
	
	#Do not change below here
	valid = ""	
	spurious = ""	
	device_lines = device_output.splitlines()
	for i in device_lines:
		if i.startswith(' '):
			#Ignore sub commands, only checking global
			continue
		if i.strip() == device_command:
			valid = "Ok"
			comment = ""
	if valid != "Ok":
		valid = "Failed"
	return valid, comment, fixit, spurious
