import re
import queue
import threading
import shlex
from collections import defaultdict


class DistributorVariable:
	def __init__(self):
		self.target = set()

	def add_target(self, proc, i):
		self.target.add((proc, i))

	def push_stop_request(self, order):
		for proc, i in self.target:
			proc.put_stop_request(order)

	def push(self, data, order):
		for proc, i in self.target:
			proc.put_data(i, data, order)


class Processor:
	def __init__(self, commandname, argdict, threads=1, Qsize=100):
		try:
			if hasattr(__import__("plugins", fromlist=[commandname]), commandname):
				self.klass = getattr(__import__("plugins", fromlist=[commandname]), commandname).Command
			else:
				self.klass = getattr(__import__("core.commands", fromlist=[commandname]), commandname).Command
		except AttributeError:
			raise Exception("Command \"%s\" is not found" % commandname)

		self.command = [self.klass(**argdict) for i in range(1 if self.klass.ShareResources else threads)]
		self.inputqueue = queue.Queue()
		self.outputvariable = [DistributorVariable() for i in range(self.klass.OutputSize)]
		self.lock = threading.Lock()
		self.ackput_condition = threading.Condition()
		self.working_list = set()
		self.oldest_order = -1
		self.seqorder = 0
		self.Qsize = Qsize
		self.temp_input = defaultdict(lambda : [None] * self.klass.InputSize)
		self.stop_at = -1
		self.process_cnt = 0
		self.singlethread_order = 0
		self.threads = threads

	def put_stop_request(self, order):
		self.stop_at = order
		for i in range(self.threads):
			self.inputqueue.put((order, None))

	def put_data(self, i, data, order):
		with self.ackput_condition:
			while self.oldest_order != -2 and order > self.oldest_order + self.Qsize:
				self.ackput_condition.wait()
		with self.lock:
			self.temp_input[order][i] = data
		if self.klass.MultiThreadable:
			if None not in self.temp_input[order]:
				self.inputqueue.put((order, self.temp_input.pop(order)))
		else:
			while self.singlethread_order in self.temp_input:
				if None in self.temp_input[self.singlethread_order]:
					break
				self.inputqueue.put((self.singlethread_order, self.temp_input.pop(self.singlethread_order)))
				self.singlethread_order += 1

	def run_routine(self, thread_id_orig):
		thread_id = thread_id_orig
		if self.klass.ShareResources:
			thread_id = 0
		if self.klass.InputSize != 0:
			order, instream = self.inputqueue.get()
		else:
			with self.lock:
				order = self.seqorder
				self.seqorder += 1
			instream = ()
		with self.lock:
			self.working_list.add(order)
			self.oldest_order = min(self.working_list)
		outstream = self.command[thread_id].routine(instream) if instream is not None else None
		with self.lock:
			self.working_list.discard(order)
			self.oldest_order = min(self.working_list) if self.working_list else -2
		with self.ackput_condition:
			self.ackput_condition.notify_all()
		if outstream is not None:
			for i, v in enumerate(outstream):
				self.outputvariable[i].push(v, order)
		self.lock.acquire()
		cnt = self.process_cnt + 1 if instream is not None and outstream is not None else self.process_cnt
		if cnt == self.stop_at or outstream is None and instream is not None:
			if instream is not None and outstream is not None:
				self.process_cnt += 1
			self.lock.release()
			for ov in self.outputvariable:
				ov.push_stop_request(cnt)
			self.inputqueue.put((cnt, None))
			return False
		if instream is not None:
			self.process_cnt += 1
		self.lock.release()
		return True


class ScriptRunner:
	availablename_matcher = re.compile("[A-Za-z_]\w*$")
	esc_seq_matcher = re.compile(r"\\(.)")
	intfloat_matcher = re.compile(r"[+\-]?(\d*\.?\d+|\d+\.?\d*)$")

	def esc_replacer(m):
		esc_ch = m.group(1)
		if esc_ch == "n":
			return "\n"
		return esc_ch

	def __init__(self, lines, threads=1, buffersize=100):
		variables = {}
		alias = {}
		self.procs = []
		prevline = ""
		self.threads = threads
		for n, line in enumerate(lines):
			line = line.strip()

			# skip comment line
			if not line or line[0] == "#":
				continue

			# Concatinate
			line = prevline + line
			if line[-1] == "\\":
				prevline = line[:-1] + " "
				continue
			prevline = ""

			shline = shlex.shlex(line)
			shline.whitespace_split = False
			shline.escapedquotes = "\"'"
			try:
				tokens = list(shline)
			except ValueError:
				print("At line %d:" % (n+1), file=sys.stderr)

			for i, w in enumerate(tokens):
				if w in alias:
					tokens[i:i+1] = alias[w]

			command = tokens[0]

			if command == "Alias":
				if len(tokens) < 3:
					raise Exception("Syntax error at line %d" % (n+1))
				if not ScriptRunner.availablename_matcher.match(tokens[1]):
					raise Exception("Syntax error at line %d" % (n+1))
				alias[tokens[1]] = tokens[2:]
				continue

			options = {}
			invar_name = []
			outvar_name = []

			opt_tokens = tokens[1:] + [""]
			while True:
				token = opt_tokens.pop(0)
				if token == "<":
					if not ScriptRunner.availablename_matcher.match(opt_tokens[0]):
						raise Exception("Syntax error at line %d" % (n+1))
					while ScriptRunner.availablename_matcher.match(opt_tokens[0]):
						invar_name.append(opt_tokens.pop(0))
				elif token == ">":
					if not ScriptRunner.availablename_matcher.match(opt_tokens[0]):
						raise Exception("Syntax error at line %d" % (n+1))
					while ScriptRunner.availablename_matcher.match(opt_tokens[0]):
						outvar_name.append(opt_tokens.pop(0))
				elif token == ":":
					if not ScriptRunner.availablename_matcher.match(opt_tokens[0]):
						raise Exception("Syntax error at line %d" % (n+1))
					optname = opt_tokens.pop(0)
					if opt_tokens[0] == "=":
						opt_tokens.pop(0)
						optval = opt_tokens.pop(0)
						if optval == "True":
							options[optname] = True
						elif optval == "False":
							options[optname] = False
						elif len(optval) >= 2 and (optval[0] == optval[-1] == "\"" or optval[0] == optval[-1] == "'"):
							string = ScriptRunner.esc_seq_matcher.sub(ScriptRunner.esc_replacer, optval[1:-1])
							options[optname] = string
						elif ScriptRunner.intfloat_matcher.match(optval):
							options[optname] = float(optval)
						else:
							raise Exception("Syntax error at line %d" % (n+1))
					else:
						options[optname] = True
				elif token == "":
					break
				else:
					raise Exception("Syntax error at line %d" % (n+1))

			try:
				proc = Processor(command, options, threads=self.threads, Qsize=buffersize)
			except:
				print("At line %d:" % (n+1), file=sys.stderr)
				raise

			if len(invar_name) != proc.klass.InputSize:
				raise Exception("Input size mismatch (required %d, given %d) (line %d)" % (proc.klass.InputSize, len(invar_name), n+1))
			if len(outvar_name) != proc.klass.OutputSize:
				raise Exception("Output size mismatch (required %d, given %d) (line %d)" % (proc.klass.OutputSize, len(outvar_name), n+1))
			for i, varname in enumerate(invar_name):
				if varname not in variables:
					raise Exception("Variable \"%s\" is not defined (line %d)" % (varname, n+1))
				variables[varname].add_target(proc, i)
			for i, varname in enumerate(outvar_name):
				variables[varname] = proc.outputvariable[i]

			self.procs.append(proc)

	def run(self):
		def subWorker(proc, thread_id):
			while True:
				ret = proc.run_routine(thread_id)
				if not ret:
					return

		ts = []
		for proc in self.procs:
			for i in range(self.threads if proc.klass.MultiThreadable else 1):
				t = threading.Thread(target=subWorker, args=(proc, i))
				t.start()
				ts.append(t)
		for t in ts:
			t.join()
