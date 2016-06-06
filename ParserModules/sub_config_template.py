#This template module checks for the presence of a specific sub-command. 
#It expects to be passed the output of show running-config
#Set the value of the "parent_command" variable to the top level command
#Set the value of the "subcommand" variable to the desired sub-command you want to check for. 
#If you have written a fixit script, specify its name in the fixit variable

def function(device_output):

	#User-defined variables
	parent_command = "interface GigabitEthernet1/0/10"
	subcommand = "speed 100"
	fixit = ""	#Optionally, specify a fixit script if you have written one
	
	#Do not change below here
	device_lines = device_output.splitlines()
	valid = ""
	comment = ""
	spurious = ""
	sub_config = []
	check1 = "Failed"
	check2 = "Failed"
	# Find the parent command
	for i in device_lines:
		if i.strip() == parent_command:
			#Found the parent command
			check1 = "Ok"
			# Extract the sub config
			q = device_lines.index(i) + 1
			for j in device_lines[q:]:
				if j.startswith(" "):
					sub_config.append(j)
				else:
					break
			break	

	# Check contents of sub_config for the sub-command
	if len(sub_config) > 0:
		for l in sub_config:
			if l.strip() == subcommand:
				check2 = "Ok"
	
	# Validate the above
	if check1 != "Ok":
		if comment == "":
			comment = "Parent command not found"
		else:
			comment = comment + "\r\nParent command not found"
		valid = "Failed"
	if check2 != "Ok":
		if comment == "":
			comment = "Sub command not found"
		else:
			comment = comment + "\r\nSub command not found"
		valid = "Failed"
	
	if check1 == "Ok" and check2 == "Ok":
		valid = "Ok"
	
	return valid, comment, fixit, spurious
					