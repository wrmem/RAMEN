# This parser module checks if a traceroute was successful
# It expects to be passed the output of the traceroute command

def function(device_output):
	valid = "Ok"
	spurious = ""
	comment = "Traceroute failed"
	fixit = ""

	output = ""
	found_tr = False
	lines = device_output.splitlines()
	for i in lines:
		if found_tr == True:
			output = output + "\n" + i
			if "#" in i or ">" in i:
				break
		if "Tracing the route to" in i:
			found_tr = True

	if " *" in output.split('\n')[-2] and "msec" not in output.split('\n')[-2] and "Tracing the route" in output:
		valid = "Failed"
		spurious = output
	else:
		valid = "Ok"
		spurious = output
		
	return valid, comment, fixit, spurious
