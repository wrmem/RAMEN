#Reliable AutoMation Engine for Networking (RAMEN) Parser Tool
#This tool reads the Execution Tool's CSV (lastrun.csv) and checks its content for specified strings
#The exam file contains the module names of each check you want run on the execution tool's output
#Exam modules are stored in RAMEN\ParserModules. Writing your own modules is encouraged. 
#
#RAMEN is released under the GNU General Public License
#
#Copyright Ryan Smith
#
#Disclaimer:
#THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
#SHALL THE CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
#CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF 
#USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#Version 1.00
vernum = "1.00"

import sys
import csv
import string
import argparse
import importlib
import time
import smtplib
import base64
import re

# Get CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("-input", "-i", type=str, help="Filename of Execution Tool's log file")
parser.add_argument("-exam", "-e", type=str, help="Filename of exam file")
parser.add_argument("-output", "-o", type=str, help="Filename of output CSV file")
parser.add_argument("-mailto", "-mt", type=str, help="Email output CSV to this address")
parser.add_argument("-mailfrom", "-mf", type=str, help="Email from this address")
parser.add_argument("-mailsubj", "-ms", type=str, help="Email subject line in quotes")
parser.add_argument("-mailrelay", "-mr", type=str, help="Email relay server")
parser.add_argument("-mailonlyfailures", action='store_true', help="Only email on failure")
parser.add_argument("-debug", "-d", action='store_true', help="Enable debugging of parser modules")
args = parser.parse_args()

def validator(device_output):
	#Get the list of exam conditions from the exam file
	examfile = open(exam_file, 'rb')
	examfileline = examfile.readline()
	spurious = ""
	fixit = ""
	valid = ""
	check_state = "Ok"
	crash_log = ""
	while examfileline:
		if examfileline.strip() == "":
			examfileline = examfile.readline()
			continue
		examfileline = "ParserModules." + examfileline.strip()
		if args.debug:
			examfileline = examfileline.strip()
			module = importlib.import_module(examfileline)
			valid, comment, fixit, spurious = module.function(device_output)
			plogger(examfileline, valid, output_file, comment, fixit, spurious)
		else:
			try:
				module = importlib.import_module(examfileline)
				# Test against the module named in the exam file
				valid, comment, fixit, spurious = module.function(device_output)
				plogger(examfileline, valid, output_file, comment, fixit, spurious)
			except Exception as crash_log:
				print "ERROR: Failed import or execution of %s" % examfileline
				plogger(examfileline, "Failed", output_file, "Failed import or execution of parser module", "", crash_log)
		#If any exam command doesn't return valid as "Ok", set check_state to "Failed" to trigger emailing
		if valid == "Ok":
			pass
		else:
			check_state = "Failed"
		examfileline = examfile.readline()
	examfile.close()
	return check_state

def plogger(examfileline, valid, output_file, comment, fixit, spurious):
	with open(output_file, 'ab') as outputcsvfile:
		output_writer = csv.writer(outputcsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		if "ParserModules." in examfileline:
			examfileline = re.sub(re.escape("ParserModules."), '', examfileline)
		if valid == "Ok":
			output_writer.writerow([ip, examfileline, valid])
		else:
			valid == "Failed"
			output_writer.writerow([ip, examfileline, valid, comment, fixit, spurious])

def breader(row_ref, returned_output):
	filename = row_ref[5:]
	filename = "TextLogs\\" + filename
	try:
		with open(filename, 'rb') as biglogfile:
			returned_output = biglogfile.read()
	except:
		print "  ERROR: Unable to open %s" % filename
		sys.exit()
	return returned_output

def startup():
	# Get required options not set on command line 
	print "\n***************************"
	print "* RAMEN Parser Tool v%s *" % vernum
	print "***************************\n"
	if not args.input:
		print "Enter filename of Execution tool's log file"
		input_file = raw_input("filename=")
	else:
		input_file = args.input
	if not args.exam:
		print "Enter filename of the exam file"
		exam_file = raw_input("filename=")
	else:
		exam_file = args.exam
	if not args.output:
		print "Enter filename for saving output"
		output_file = raw_input("filename=")
	else:
		output_file = args.output
	return input_file, exam_file, output_file

def email_results(output_file):
	#Email the results if asked to
	if not args.mailto:
		return
	else:
		receiver = args.mailto
	
	if not args.mailrelay:
		mailrelay = "localhost"
	else:
		mailrelay = args.mailrelay
	
	if not args.mailfrom:
		sender = "RAMEN-Parser@domain.com"
	else:
		sender = args.mailfrom
		
	if not args.mailsubj:
		subj = "RAMEN-Parser Results"
	else:
		subj = args.mailsubj
	
	now = time.strftime("%c")
	body = "RAMEN-Parser results attached. Execution time %s" % now
	marker = "3jkd8sk3d0fkg9gkem23m29d90cv98b8ws"
	
	# Read in the attachment and encode it
	fo = open(output_file, "rb")
	filecontent = fo.read()
	encodedcontent = base64.b64encode(filecontent)  

	# Define the main headers.
	part1 = """From: Log Parser <%s>
To: <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (sender, receiver, subj, marker, marker)

	# Define the message action
	part2 = """Content-Type: text/plain
Content-Transfer-Encoding:8bit

%s

--%s
""" % (body, marker)

	# Define the attachment section
	part3 = """Content-Type: multipart/mixed; name=\"%s\"
Content-Transfer-Encoding:base64
Content-Disposition: attachment; filename=%s

%s
--%s--
""" %(output_file, output_file, encodedcontent, marker)

	
	# Assemble message
	message = part1 + part2 + part3

	# Send message
	try:
		smtpObj = smtplib.SMTP(mailrelay)
		smtpObj.sendmail(sender, receiver, message)
		print "\n  Successfully sent email"
	except Exception:
		print "ERROR: unable to send email"
	
	return


	
# Main	
if __name__ == '__main__':
	
	# Get required options not set on command line 
	input_file, exam_file, output_file = startup()
	
	#Write header to output file
	with open(output_file, 'wb') as outputcsvfile:
		output_writer = csv.writer(outputcsvfile, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
		output_writer.writerow(["Device IP", "Exam", "Validity", "Comment", "Fixit script", "Spurious"])
	
	
	#Get a unique set of device IPs from the input file
	device_ip = []
	afailure = False
	with open(input_file, 'rb') as inputfile:
		inputreader = csv.reader(inputfile, delimiter=',', quotechar='"')
		for row in inputreader:
			if row[3] == "Login Failure":
				print "  Login Failure recorded for %s" % row[2]
				examfileline = ""
				ip = row[2]
				plogger("Login Failure", "Failed", output_file, "Login Failure", "Login Failure", "Login Failure")
				afailure = True
			else:
				device_ip.append(row[2])
	device_ip.remove('***********')
	unique_ips = set(device_ip)
	

	#Iterate through the input file 
	device_output = ""
	valid = ""
	returned_output = ""
	check_state = ""
	with open(input_file, 'rb') as inputfile:
		inputreader = csv.reader(inputfile, delimiter=',', quotechar='"')
		for ip in unique_ips:
			print "  Analyzing logs for %s" % ip
			inputfile.seek(0)
			device_output = ""
			for row in inputreader:
				if ip == row[2]:
					if row[4].startswith("*See "):
						returned_output = breader(row[4],returned_output)
						device_output = device_output + returned_output
					else:
						device_output = device_output + row[4]
			check_state = validator(device_output)
			if check_state == "Failed":
				afailure = True

	#Email the results if asked to
	if args.mailonlyfailures and afailure == False:
		pass
	else:
		email_results(output_file)
		
	print "\n  Parser complete. Check %s for log of results." % output_file

	
