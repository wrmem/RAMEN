# This parser module checks if the one minute average CPU utilization is above 70%
# It expects to be passed the output of "show process cpu"

def function(device_output):
	valid = "Ok"
	spurious = ""
	comment = ""
	fixit = ""

	device_lines = device_output.splitlines()
	for i in device_lines:
		if "CPU utilization" in i:
			percentages = i.split(';')
			for j in percentages:
				if "one minute" in j:
					one_minute_usage = j.split(':')
					cpu_usage = one_minute_usage[1].strip('%')
					cpu_usage = cpu_usage.strip()
					try:
						if int(cpu_usage) >= 70:
							valid = "Failed"
							comment = "CPU usage high"
							spurious = "One minute CPU usage was %s" % cpu_usage + "%"
					except:
						valid = "Failed"
						comment = "Error occurred during module processing"
						spurious = i
	return valid, comment, fixit, spurious
	
