#The module can be used to find unmanaged switches on your network
#This module finds ports with multiple MACs, excluding:
#	ports with a CDP neighbor 
#	port-channel logical interfaces
#	MACs belonging to Avaya phones
#	MACs belonging to VMware
#Pass it the output of "sho cdp neighbor" and "show mac address-table" for each device
#Returns list of interfaces with multiple MACs and the number of *extra* MACs 

def function(device_output):
	device_lines = device_output.splitlines()
	valid = ""
	comment = ""
	spurious = ""
	fixit = ""
	extra_mac_total = 0
	intlist = []
	maclist = []
	# Exculde MACs with the vendor ID belonging to Avaya or VMware. Add more as needed.
	vendoroui = ["00040D","001B4F","00073B","00E007","048A15","10CDAE","24D921","2CF4C5","3475C7","38BB3C","3C3A73",
	"3CB15B","44322A","506184","50CD22","581626","646A52","64A7DD","64C354","6CA849","6CFA58","703018",
	"7038EE","7052C5","801DAA","848371","90FB5B","A009ED","A01290","A051C6","A4251B","B0ADAA","B4475E",
	"B4A95A","B4B017","BCADAB","C057BC","C4BED4","C8F406","CCF954","D47856","D4EA0E","E45D52","F81547",
	"F873A2","FC8399","FCA841","000569","000C29","001C14","005056","000569","000C29","001C14","005056"]
	
	#Find CDP output
	cdpoutput = ""
	cdpstuff = False
	for i in device_lines:
		if "Local Intrfce" in i:
			#iterate until you get to the prompt
			cdpstuff = True
			continue
		if cdpstuff == True and (">" in i or "#" in i):
			#back to the prompt
			cdpstuff = False
			break
		if cdpstuff == True:
			cdpoutput = cdpoutput + i + "\n"

	
	#Find neighbors in CDP output
	cdp_lines = cdpoutput.splitlines()
	cdp_table = False
	longname = False
	cdp_int_speed_list = []
	cdp_int_num_list = []
	for i in cdp_lines:
		cdp_list = i.split()
		#print cdp_list
		if len(cdp_list) == 1:
			#Deal with long device name word wrap
			longname = True
			continue
		if len(cdp_list) < 2:
			continue
		if longname == True:
			cdp_int_speed = cdp_list[0] 
			cdp_int_num = cdp_list[1]
			cdp_int_speed_list.append(cdp_int_speed[0:2])
			cdp_int_num_list.append(cdp_int_num)
		else:
			cdp_int_speed = cdp_list[1] 
			cdp_int_num = cdp_list[2]
			cdp_int_speed_list.append(cdp_int_speed[0:2])
			cdp_int_num_list.append(cdp_int_num)
		longname = False
	
	#Print table of cdp neighbors
	#for i in range(0, len(cdp_int_speed_list)):
	#	print cdp_int_speed_list[i] + " " + cdp_int_num_list[i]

	
	# Start compiling MAC to interface mappings
	inshowmac = False
	for i in device_lines:
		if "Unicast Entries" in i or "Mac Address Table" in i or "mac address entry" in i:
			# Start of show mac command
			inshowmac = True
		
		if inshowmac == False:
			continue
	
		# Stop looking for more MACs
		if "Multicast Entries" in i or "Total Mac Addresses" in i or "#" in i or ">" in i:
			# End of show mac command
			break

		# Find interface names, location varies by platform
		if "Port" in i or "port" in i:
			chopped_line = i.split()
			for k in range(0,len(chopped_line)):
				#	print "k = %s" % k
				if "port" in chopped_line[k] or "Ports" in chopped_line[k]:
					intcol = k - 1
			continue
		
		# intcol won't get defined until it iterates to the required
		#   line in the command output
		try:
			intcol
		except:
			continue

		chopped_line = i.split()
		if len(chopped_line) < intcol:
			continue
		
		# Some MACs for system, not a port
		try:
			chopped_line[intcol]
		except:
			continue
		
		if "Gi" in chopped_line[intcol] or "Fa" in chopped_line[intcol] or "Te" in chopped_line[intcol]:
			# Find the MAC, always 2nd column
			chopped_line = i.split()
			macaddr = chopped_line[1]
			macaddr = macaddr.replace(".","")
			macaddr = macaddr.upper()
			intname = chopped_line[intcol]

			#Check if the interface name is already in the interface list
			addit = True
			for value in intlist:
				if value == intname:
					addit = False
					break
			
			# Add MAC addresses to list with index corresponding to intlist
			if addit == True:
				intlist.append(intname)
				maclist.append([macaddr])
			else:
				location = intlist.index(intname)
				maclist[location].append([macaddr])
			
			#Add the MAC to the interface's entry in the list
			location = intlist.index(intname)			


	# Remove interfaces and MACs of CDP neighbor ports
	i = 0
	while i < len(intlist):
		for j in range (0, len(cdp_int_speed_list)):
			if intlist[i].startswith(cdp_int_speed_list[j]) and intlist[i].endswith(cdp_int_num_list[j]):
				# Found a CDP neighbor interface, purge it
				del intlist[i]
				del maclist[i]
				i = i - 1
				break
		if len(cdp_int_speed_list) == 0:
			break
		i += 1
		
			
	
					
	extra_mac_count = 0
	# Look for ports with multiple MACs, excluding specified mfgs.
	for i in range(0, len(intlist)):
		int_mac_count = len(maclist[i])
		if int_mac_count > 1:
			# Multiple MACs found, iterate through them
			extramac = int_mac_count - 1 #one mac always allowed
			for k in range(0, len(maclist[i])):
				#Check for devices to ignore
				for j in vendoroui:
					macaddr = str(maclist[i][k])
					macaddr = macaddr.strip('[]\'')
					if macaddr[0:6] == j:
						extramac = extramac - 1
						break
			if extramac >= 1:
				int_name = str(intlist[i])
				if spurious == "":
					spurious = str(extramac) + " extra MACs found on " + int_name
				else:
					spurious = spurious + "\r\n" + str(extramac) + " extra MACs found on " + int_name
				extra_mac_total = extra_mac_total + extramac
	
	if extra_mac_total > 0:
		valid = "Failed"
		comment = "Total Extra MACs = " + str(extra_mac_total)
	else:
		valid = "Ok"

	return valid, comment, fixit, spurious