class Command:

	def InputSize(self, size):
		if self.stop < 0:
			if size > 1:
				raise Exception("Too many input are given")
		elif size != 0:
			raise Exception("You can not specify any input if `stop' is set")

	OutputSize = 1
	MultiThreadable = False

	def __init__(self, stop=-1):
		self.counter = 0
		self.stop = int(stop)

	def routine(self, instream):
		c = self.counter
		if c == self.stop:
			return None
		self.counter += 1
		return (c,)
