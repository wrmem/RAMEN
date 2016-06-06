#This module checks for the presence of interfaces operating in half-duplex mode
#It expects to be passed the output of show interfaces
#It returns "Failed" for any device with at least one interface in half-duplex mode
#Spurious contains the list of half-duplex interfaces

def function(device_output):
	valid = "Ok"	
	comment = ""
	fixit = ""
	spurious = ""
	rdy_int_details = False
	
	device_lines = device_output.splitlines()
	for i in device_lines:
		if "line protocol" in i:
			#Found an interface
			line_items = i.split(" ")
			int_name = line_items[0] 
			rdy_int_details = True
			continue
		if i.startswith(" ") and rdy_int_details:
			#Search indented text for half-duplex
			if "Half-duplex" in i:
				valid = "Failed"
				if spurious == "":
					spurious = int_name + " is in half-duplex mode"
				else:
					spurious = spurious + "\r\n" + int_name + " is in half-duplex mode"
		else:
			#Other output or didn't find duplex for this interface
			rdy_int_details = False

	if valid != "Ok":
		valid = "Failed"
		comment = "Half-duplex interfaces found"
	return valid, comment, fixit, spurious