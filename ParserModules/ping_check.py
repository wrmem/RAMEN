# This parser module checks if a ping was successful
# Pass it the output of the ping command

def function(device_output):
	valid = "Failed"
	spurious = ""
	comment = "Ping failed"
	fixit = ""

	found_ping = False
	lines = device_output.splitlines()
	for i in lines:
		if "-byte ICMP Echos to" in i:
			found_ping = True
			continue
		if found_ping == True and "!" in i:
			valid = "Ok"
			continue
		if "Success rate" in i and valid == "Failed":
			spurious = i
			break
		if "Success rate" in i:
			break

	return valid, comment, fixit, spurious
