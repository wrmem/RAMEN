#This template module checks that an access list is properly configured and applied
#It expects to be passed the output of show running-config
#Specify the ACL command and each entry within it. Each line is expected in the proper sequential order. 
#Also specify the interface on which it is applied and the relevant access-group command

def function(device_output):

	#User-defined variables
	interface = "GigabitEthernet0/0"	#The interface where the ACL should be applied
	applied_command = " ip access-group testacl in"		#The applied ACL command, with leading space
	acl_name = "ip access-list standard testacl"		#The expected ACL
	#A list of required ACL entries in the expected order, include the leading space
	correct_acl_entries = [" permit 10.0.0.0 0.255.255.255", " permit 192.168.0.0 0.0.255.255", " permit 172.16.0.0 0.0.15.255"]
	fixit = "testacl_fixit.txt"	#Optionally, specify a fixit script if you have written one
	
	
	
	#Do not change below here
	device_lines = device_output.splitlines()
	valid = "Failed"
	comment = ""
	spurious = ""
	actual_access_list = []
	check1 = "Failed"
	check2 = "Failed"
	check3 = "Failed"
	check4 = "Failed"
	for i in device_lines:
		#Find the ACL
		if i == acl_name:
			check1 = "Ok"	
			# Extract the ACL
			q = device_lines.index(i) + 1
			for j in device_lines[q:]:
				if j.startswith(" "):
					actual_access_list.append(j)
				else:
					break
	
	for i in device_lines:
		#Find the interface
		if i == interface:
			# Search the interface's config for the ACL's application
			q = device_lines.index(i) + 1
			for j in device_lines[q:]:
				if j.startswith(" "):
					if j == applied_command:
						check2 = "Ok"
				else:
					break

	# Check the length of the ACL
	if len(actual_access_list) == len(correct_acl_entries):
		check3 = "Ok"

	# Check contents of access_list
	acl_index = 0
	if len(actual_access_list) > 0:
		while True:
			if actual_access_list[acl_index] == correct_acl_entries[acl_index]:
				check4 = "Ok"
			else:
				check4 = "Failed"
				break
			if (acl_index + 1) == len(actual_access_list) or (acl_index + 1) == len(correct_acl_entries):
				break
			acl_index += 1
			
	# Validate the above
	if check1 != "Ok":
		if comment = "":
			comment = "ACL not found"
		else:
			comment = comment + "\r\nACL not found"
		valid = "Failed"
	if check2 != "Ok":
		if comment = "":
			comment = "ACL not applied"
		else:
			comment = comment + "\r\nACL not applied"
		valid = "Failed"
	if check3 != "Ok":
		if comment = "":
			comment = "ACL has incorrect number of lines"
		else:
			comment = comment + "\r\nACL has incorrect number of lines"
		valid = "Failed"
	if check4 != "Ok":
		if comment == "":
			comment = "ACL has incorrect entry"
		else:
			comment = comment + "\r\nACL has incorrect entry"
		valid = "Failed"
	if check1 == "Ok" and check2 == "Ok" and check3 == "Ok" and check4 == "Ok":
		valid = "Ok"

	return valid, comment, fixit, spurious



