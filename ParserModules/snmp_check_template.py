#This module checks for incorrect SNMP community strings
#It expects to be passed the output of show running-config
#Set the value of the "snmp_command" variable to the proper snmp community command for your environment
#The script will report "Failure" if the command isn't found. 
#The spurious field will be populated with the "no'd" version of any extra community strings
#Use RAMEN-Exec in batch mode to remove these extra community strings

def function(device_output):
	
	#User-defined variables
	snmp_command = "snmp-server community public RO"
	
	#Do not change below here
	valid = ""
	comment = ""
	fixit = ""
	spurious = "configure terminal"	#Added to simplify conversion of data to batch script
	check1 = ""
	check2 = "Ok"
	device_lines = device_output.splitlines()
	for i in device_lines:
		if i == snmp_command:
			check1 = "Ok"
			continue
		elif i.startswith("snmp-server community "):
			spurious = spurious + "\r\n" + "no " + i
			check2 = "Failed"
			continue
			
	# Validate the result
	if check1 == "Ok" and check2 == "Ok":
		valid = "Ok"
	if check1 != "Ok":
		valid = "Failed"
		if comment == "":
			comment = "Correct SNMP string not found"
		else:
			comment = comment + "\r\nCorrect SNMP string not found"
	if check1 != "Ok":
		valid = "Failed"
		if comment == "":
			comment = "Spurious SNMP strings found"
		else:
			comment = comment + "\r\nSpurious SNMP strings found"
		valid = "Failed"
	
	return valid, comment, fixit, spurious

