import threading
import logging
import os

class MyThread(threading.Thread):
	def __init__(self):
		super(MyThread, self).__init__()
		self.name = self.__class__.__name__
		self._log = logging.Logger(self.name)
		self._log.setLevel(logging.DEBUG)
		# assure that log dir exists
		print('cwd ' + os.getcwd())
		logdir = os.path.join(os.getcwd(), 'log')
		print('path exists' + str(os.path.exists(logdir)))
		if not os.path.exists(logdir):
			print 'creating log'
			os.mkdir(logdir)
		
		fh = logging.FileHandler(os.path.join('log', self.name + '.log'), mode='w')
		self._log.addHandler(fh)

		# try to add handlers from default log
		def_log = logging.getLogger()
		self._log.debug('default logger\'s handler count %d' % len(def_log.handlers))
		self._log.handlers += def_log.handlers

