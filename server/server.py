from serial import Serial
from time import sleep
import sys
from graph import Graph
import math
from binary_heap import BinaryHeap


ser_states = {
	'WAIT_ON_REQ':'WAIT_ON_REQ', 
	'WAIT_ON_ACK':'WAIT_ON_ACK', 
	'RECIEVE_DATA':'RECIEVE_DATA',
	'PROCESS':'PROCESS',
	}
curr_mode = ser_states['WAIT_ON_REQ']

class server():
	'''This will load the graph of edmonton from "edmonton-roads-2.0.1.txt", 
		read a request from sys.stdin and print the output to sys.stdout.

		You can test your entire server using some of the files on eClass. 
		For example:
			python3 server.py < test00-input.txt > mysol.txt

		This will cause sys.stdin to read from test00-input.txt instead of the 
		keyboard and have sys.stdout print to the file mysol.txt instead of 
		the terminal.  You can examine the output by looking at mysol.txt. 
		You can quickly determine if the output agrees with with the provided expected
		output test00-output.txt by running

			diff mysol.txt test00-output.txt

		These test files are in the tests.tar.gz file on eClass. 
		There is also a script test server.py that includes the Python 
		code for testing individual functions in the example above. 
		The expected output for this is in test server output.py.

		NEEDS:
		-Load edmonton graph function
		-Dijkstras(with cost function)
		-

	'''

	
	def load_edmonton_graph(filename):#(DONE)
		"""
			Loads the graph of Edmonton from the given file.

			Returns two items

			graph: the instance of the class Graph() corresponding to the
			directed graph from edmonton-roads-2.0.1.txt

			location: a dictionary mapping the identifier of a vertex to
			the pair (lat, lon) of geographic coordinates for that vertex.
			These should be integers measuring the lat/lon in 100000-ths
			of a degree.

			In particular, the return statement in your code should be
			return graph, location
			(or whatever name you use for the variables).

			Note: the vertex identifiers should be converted to integers
			before being added to the graph and the dictionary.
		"""

		vertices = set()
		edges = list()

		#location dictionary 
		location = {}


		with open(filename, 'r') as text:
			lines = text.readlines()#contains all lines as array



			for line in lines:
				
				if line[0] == 'V':#if the line specifies a vertex
					ID = ""

					#reads the line after the first comma and before the second
					line = line.split(",");
				
					ID = line[1]

					#int(float(coord) ∗ 100000).
					lat = int(float(line[2])*100000)
					lon = int(float(line[3].strip("\n"))*100000)

					location[int(ID)] = lat, lon

					vertices.add(int(ID))#adds to vertices array


				elif line[0] == 'E':
					start = ""
					end = ""
					
					#reads from first comma to third, splitting at second
					line = line.split(",")
					
					start = line[1]
					end = line[2]
					u = int(start), int(end)
					
					edges.append(u)
					
			vertices = sorted(vertices)

			graph = Graph(vertices, edges)#combines vertices and edges in graph class

		return graph, location



	class CostDistance:#(DONE)
		"""
			A class with a method called distance that will return the Euclidean
			between two given vertices.
		"""

		def __init__(self, location):
			"""
				Creates an instance of the CostDistance class and stores the
				dictionary "location" as a member of this class.
			"""
			self.points = location



		def distance(self,e):
			"""
				Here e is a pair (u,v) of vertices.
				u:start
				v:end
				Returns the Euclidean distance between the two vertices u and v.
			"""
			u = self.points[e[0]]
			v = self.points[e[1]]

			return math.sqrt((v[0]-u[0])**2 + (v[1] - u[1])**2)





	def least_cost_path(graph, start, dest, cost):
		"""	Find and return a least cost path in graph from start
			vertex to dest vertex.

			Efficiency: If E is the number of edges, the run-time is
			O( E log(E) ).

			Args:
			graph (Graph): The digraph defining the edges between the
			vertices.

			start: The vertex where the path starts. It is assumed
			that start is a vertex of graph.

			dest: The vertex where the path ends. It is assumed
			that dest is a vertex of graph.

			cost: A class with a method called "distance" that takes
			as input an edge (a pair of vertices) and returns the cost
			of the edge. For more details, see the CostDistance class
			description below.

			Returns:

			list: A potentially empty list (if no path can be found) of
			the vertices in the graph. If there was a path, the first
			vertex is always start, the last is always dest in the list.
			Any two consecutive vertices correspond to some
			edge in graph.

		"""

		reached = {}#search tree
		events = BinaryHeap()#uses heap to store data on nodes and weights

		events.insert((start,start),0)#starting vertex burns at time 0


		edges = graph.get_edges

		while len(events) > 0:
			curr = events.popmin()

			u,v = curr[0][0],curr[0][1]
			time = curr[1]

			if v not in reached:
				reached[v] = u#burn the vertex v and add u to the record

				neighbors = graph.neighbours(v)

				for w in neighbors:

					newTime = time + cost.distance((v,w))#stores the time taken to reach new node from previous
					events.insert((v,w),newTime)

		shortest_path = []

		shortest_path.append(dest)
		next_node = reached[dest]

		while next_node != start:
			#iterates through the search tree from end to start,
			#collecting visited vertices and storing them in path array
			for el in reached:
				if el == next_node:
					shortest_path.append(next_node)
					next_node = reached[el]



		shortest_path.append(next_node)				

		#removes any doubles:
		newList = []
		for el in shortest_path:
			if el not in newList:
				newList.append(el)


		return list(reversed(newList))


def findpath(lat, lon,location):
	'''creates a dictionary that maps the euclidian distance from the lat/lon of the passed
	values and then selects the smallest value, aka the closest lat/lon in the graph'''
	dist = {}
	for local in location:

		distance = math.hypot(lat-location[local][0],lon - location[local][1])
		dist[local] = distance
	closet = min(dist.items(), key=lambda x: x[1])

	return closet[0]



def waitOnRequest(ser):
	'''return some confirmation that the arduino has sent a request
		do try and catch for errors
	'''
	global curr_mode

	line = ser.readline()
	if not line:
		#timeout
		curr_mode = ser_states['WAIT_ON_REQ']
		print("timeout on request")
		return
	line_string = line.decode("ASCII")
	#print("This is the actual string:", line_string)
	#print("Stripping off the newline and carriage return")
	stripped = line_string.rstrip("\r\n")
	print("I read line from waitOnRequest: ", stripped)
	
	if stripped == "R":
		#send acknowledge to server
		sendAck(ser)
		curr_mode = ser_states['WAIT_ON_ACK']
		print(curr_mode)
	else:
		curr_mode = ser_states['WAIT_ON_REQ']


def waitOnAck(ser):
	global curr_mode
	print("waiting on ack")
	line = ser.readline()
	if not line:
		#timeout
		curr_mode = ser_states['WAIT_ON_REQ']
		print("timeout on acknowledge")
		return
	line_string = line.decode("ASCII")
	#print("This is the actual string:", line_string)
	#print("Stripping off the newline and carriage return")
	stripped = line_string.rstrip("\r\n")
	print("I read line from waitOnAck: ", stripped)
	if stripped == "A":
		#send acknowledge to server
		sendAck(ser)
		curr_mode = ser_states['RECIEVE_DATA']
		
	else:
		curr_mode = ser_states['WAIT_ON_REQ']
		

def sendAck(ser):

	out_line = "A" + "\n"

	encoded = out_line.encode("ASCII")
	# now encoded is a byte object we can
	# write to the arduino
	ser.write(encoded)


def recieveFromClient(ser):
	global curr_mode
	line = ser.readline()
	if not line:
		#timeout
		curr_mode = ser_states['WAIT_ON_REQ']
		return

	line_string = line.decode("ASCII")
	#print("This is the actual string:", line_string)
	#print("Stripping off the newline and carriage return")
	stripped = line_string.rstrip("\r\n")
	print("I read line from recieveFromClient: ", stripped)
	curr_mode = ser_states['PROCESS']
	stripped.split()
	return stripped[1],stripped[2],stripped[3],stripped[4]

def writeToClient(path,ser):
	# construct the line you want to print to the
	# Arduino, don't forget the newline

	sleep(5)#give time to process totaling 10 seconds

	'''need to give the server:
	1. # of nodes
	2. # vertices
	3. # end confirmation
	'''
	#node number
	length = str(len(path))
	out_line = "N" +  length +  "\n"#arduino will take this as no path if length > 500
	writeToArduino(out_line,ser)

	for i in range(len(path)):

		out_line = "W" + str(location[path[i]]) + "\n"
		writeToArduino(out_line,ser)

	out_line = "E"
	writeToArduino(out_line,ser)


def writeToArduino(out_line,ser):
	encoded = out_line.encode("ASCII")
	ser.write(encoded)








if __name__ == "__main__":
	# first load the edmonton graph
	edmonton_graph, location = server.load_edmonton_graph("edmonton-roads-2.0.1.txt")
	# create the CostDistance instance
	cost = server.CostDistance(location)
	#***THIS IS WHERE THE ARDUINO CODE WILL GO***
	'''high level overview:
		1.initiate communication with arduino
		2.recieve starting coords from client
		3.calculate waypoints using implemented algs
		4.pass coords to client
	'''
	
	with Serial("/dev/ttyACM0", baudrate=9600, timeout=5) as ser:
		while True:
			if curr_mode == 'WAIT_ON_REQ':
				waitOnRequest(ser)
			elif curr_mode == 'WAIT_ON_ACK':
				waitOnAck(ser)
			elif curr_mode == 'RECIEVE_DATA':
				startLat,startLon,endLat,endLon = recieveFromClient(ser)
			elif curr_mode == 'PROCESS':
				start = findpath(int(startLat),int(startLon),location)
				end = findpath(int(endLat),int(endLon),location)
				path = server.least_cost_path(edmonton_graph,start,end,cost)
				writeToClient(path,ser)


	#********************************************





