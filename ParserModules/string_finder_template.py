#This template module checks for the presence of a specific string in command output and returns "Failure" if found. 
#For example, pass it the output of show log and alert if "Traceback" is found
#Set the value of the "findit" variable to the desired command you want to check for.
#Set the value of the "comment" variable to describe the issue
#If you have written a fixit script, specify its name in the fixit variable

def function(device_output):

	#User-defined variables
	findit = "Traceback"	#Specify the text you are checking for in device output
	comment = "Traceback found"	#Optionally, specify a description of the issue.
	fixit = ""		#Optionally, specify a fixit script if you have written one
	
	#Do not change below here
	valid = "Ok"
	spurious = ""
	device_lines = device_output.splitlines()
	for i in device_lines:
		if findit in i:
			valid = "Failed"
			if spurious == "":
				spurious = i 
			else:
				spurious = spurious + "\r\n" + i
	if valid == "Ok":
		comment = ""
	return valid, comment, fixit, spurious