#!/usr/bin/env python3.7
"""

"""

from __future__ import annotations
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Union
from pathlib import Path
from datetime import datetime, timedelta
from threading import Event, Timer, Lock
from contextlib import contextmanager
from collections import defaultdict
import subprocess
import pkgutil
import json
from .util import continue_task_from_header

from eliot import (
	to_file, start_action, log_message, preserve_context, add_destinations,
)
try:
	from eliot.journald import JournaldDestination
	has_journald = True
except ImportError:
	has_journald = False
from jinja2 import Template


_g_clients: Dict[Client.name, Client] = None
_g_lock: Lock = None
_g_counts: Dict[str, int] = None


@dataclass
class Client:
	name: str
	env: Dict[str, str]
	timer: Timer
	event: Event
	body: bytes


@contextmanager
def lock():
	log_message('Acquire lock')
	with _g_lock:
		yield


def remove_client(client):
	with start_action(action_type='Remove client', name=client.name) as action:
		name = client.name

		with lock():
			del _g_clients[name]


def start_timer(client, interval=120.0):
	with start_action(action_type='Start timer', name=client.name, interval=interval):
		timer = Timer(interval, preserve_context(remove_client), args=(client,))
		client.timer = timer
		timer.start()


def cancel_timer(client):
	with start_action(action_type='Cancel timer', name=client.name) as action:
		timer = client.timer
		timer.cancel()


class RequestHandler(SimpleHTTPRequestHandler):
	protocol_version = 'HTTP/1.1'

	def do_GET(self):
		if self.path == '/':
			content = pkgutil.get_data('swarmrunner', 'static/index.html')
			self.send('text/html', content)
		elif self.path == '/static/main.js':
			content = pkgutil.get_data('swarmrunner', 'static/main.js')
			self.send('application/javascript', content)
		elif self.path == '/favicon.ico':
			content = pkgutil.get_data('swarmrunner', 'static/favicon.ico')
			self.send('image/x-icon', content)
		elif self.path.startswith('/listen/'):
			self.do_GET_listen()
		elif self.path == '/clients/':
			self.do_GET_clients()
		else:
			print('GET', self.path)
			raise NotImplementedError

	def do_GET_clients(self):
		"GET /clients/"
		_, _clients, _2 = self.path.split('/')
		assert _ == ''
		assert _clients == 'clients'
		assert _2 == ''
		
		clients = _g_clients
		
		with start_action(action_type='GET /clients/') as context:
			with lock():
				data = {
					'clients': [
						{
							'name': c.name,
							'env': json.loads(c.env),
						}
						for c in clients.values()
					],
				}
			
			content = json.dumps(data).encode('utf-8')
			self.send('application/json', content)
	
	@continue_task_from_header(action_type='Server')
	def do_GET_listen(self):
		"GET /listen/:name"
		_, _listen, name = self.path.split('/')
		assert _ == ''
		assert _listen == 'listen'

		with start_action(action_type='GET /listen/:name', name=name) as context:
			with lock():
				client = _g_clients[name]

			cancel_timer(client)
			start_timer(client)

			timeout = 60  # seconds
			context.log('Waiting for event', timeout=timeout)
			event = client.event
			was_set = event.wait(timeout=timeout)
			if not was_set:
				context.log('Event not set during timeout')
				self.send('text/plain', b'timeout\r\n', response=408)
				return

			event.clear()

			body = client.body
			self.send('text/plain', body)
	
	def do_POST(self):
		length = self.headers['content-length']
		nbytes = int(length)
		data = self.rfile.read(nbytes)
		# throw away extra data? see Lib/http/server.py:1203-1205
		self.data = data

		if self.path.startswith('/register/'):
			self.do_POST_register()
		elif self.path.startswith('/send/'):
			self.do_POST_send()
		elif self.path.startswith('/count/'):
			self.do_POST_count()
		elif self.path.startswith('/create/'):
			self.do_POST_create()
		elif self.path == '/killall/':
			self.do_POST_killall()
		else:
			print('POST', self.path)
			raise NotImplementedError
	
	@continue_task_from_header(action_type='Server')
	def do_POST_register(self):
		"POST /register/:name"
		_, _register, name = self.path.split('/')
		assert _ == ''
		assert _register == 'register'
		assert name != ''

		with start_action(action_type='POST /register/:name', name=name) as context:
			env = self.data.decode('utf-8')
			timer = None
			event = Event()
			body = None

			with lock():
				if name in _g_clients:
					context.log('client already exists with name', name=name)
					self.send('text/plain', b'client already exists with name', response=409)
					return

				client = Client(name, env, timer, event, body)
				_g_clients[name] = client

			start_timer(client)

			self.send('text/plain', b'ok\r\n')

	@continue_task_from_header(action_type='Server')
	def do_POST_send(self):
		"POST /send/:name"
		_, _send, name = self.path.split('/')
		assert _ == ''
		assert _send == 'send'
		assert name != ''

		with start_action(action_type='POST /send/:name', name=name) as context:
			body = self.data

			with lock():
				client = _g_clients[name]

			event = client.event

			client.body = body
			event.set()

			self.send('text/plain', b'ok\r\n')
	
	@continue_task_from_header(action_type='Server')
	def do_POST_count(self):
		"POST /count/:id"
		_, _count, id = self.path.split('/')
		assert _ == ''
		assert _count == 'count'
		assert id != ''

		counts = _g_counts

		with start_action(action_type='POST /count/:id', id=id) as context:
			with lock():
				count = counts[id]
				counts[id] = count + 1

			self.send('text/plain', b'%d' % (count,))

	@continue_task_from_header(action_type='Server')
	def do_POST_create(self):
		"POST /count/:type"
		_, _create, type = self.path.split('/')
		assert _ == ''
		assert _create == 'create'
		assert type != ''

		count = int(self.data)
		assert 0 < count < 16

		with start_action(action_type='POST /create/:type', type=type) as context:
			with lock():
				user_data = pkgutil.get_data('swarmrunner', 'scripts/aws-user-data.sh')
				args = [
					'aws', 'ec2', 'run-instances',
					'--image-id', 'ami-09aeadf521cc24feb',
					'--count', f'{count}',
					'--instance-type', f'{type}',
					'--key-name', 'Accona',
					'--subnet-id', 'subnet-250d584d',
					'--security-group-ids', 'sg-0a0349d5d30aff8a7',
					'--user-data', user_data,
				]
				kwargs = {
					'args': args,
					'cwd': '/tmp',
					'capture_output': True,
					'check': True,
				}

				with start_action(action_type='subprocess.run', **kwargs) as action:
					process = subprocess.run(**kwargs)
					action.add_success_fields(stdout=process.stdout, stderr=process.stderr)

			self.send('text/plain', b'ok\r\n')

	@continue_task_from_header(action_type='Server')
	def do_POST_killall(self):
		"POST /killall/"
		_, _killall, _2 = self.path.split('/')
		assert _ == ''
		assert _killall == 'killall'
		assert _2 == ''

		with start_action(action_type='POST /killall/') as context:
			with lock():
				script = pkgutil.get_data('swarmrunner', 'scripts/aws-kill-all-instances.sh')
				args = [
					'bash', '-c',
					script,
					'aws-kill-all-instance.sh',
				]
				kwargs = {
					'args': args,
					'cwd': '/tmp',
					'capture_output': True,
					'check': True,
				}

				with start_action(action_type='subprocess.run', **kwargs) as action:
					process = subprocess.run(**kwargs)
					action.add_success_fields(stdout=process.stdout, stderr=process.stderr)

			self.send('text/plain', b'ok\r\n')

	def send(self, content_type, content, *, response=200):
		use_keep_alive = self._should_use_keep_alive()
		use_gzip = self._should_use_gzip()

		if use_gzip:
			import gzip
			content = gzip.compress(content)
		
		self.send_response(response)
		self.send_header('Content-Type', content_type)
		self.send_header('Content-Length', str(len(content)))
		if use_keep_alive:
			self.send_header('Connection', 'keep-alive')
		if use_gzip:
			self.send_header('Content-Encoding', 'gzip')
		self.end_headers()
		self.wfile.write(content)

	def _should_use_keep_alive(self):
		connection = self.headers['connection']
		if connection is None:
			return False
		if connection != 'keep-alive':
			return False
		return True
	
	def _should_use_gzip(self):
		accept_encoding = self.headers['accept-encoding']
		if accept_encoding is None:
			return False
		if 'gzip' not in accept_encoding:
			return False
		return True


def main(bind, port, logfile, journald):
	to_file(open(logfile, 'ab'))

	print((datetime.utcnow() - timedelta(seconds=5)).isoformat())

	if journald:
		if has_journald:
			dest = JournaldDestination()
			dest._identifier = b'swarmrunner'
			add_destinations(dest)
		else:
			log_message("Requested journald support, but it's not available")
	
	clients = {}

	lock = Lock()

	counts = defaultdict(int)

	global _g_clients
	_g_clients = clients

	global _g_lock
	_g_lock = lock

	global _g_counts
	_g_counts = counts

	address = (bind, port)
	print(f'Listening on {address}')
	server = ThreadingHTTPServer(address, RequestHandler)
	server.serve_forever()


def cli(args=None):
	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument('--bind', default='')
	parser.add_argument('--port', type=int, default=8800)
	parser.add_argument('--logfile', type=Path, default=Path.cwd() / 'log-server.txt')
	parser.add_argument('--journald', action='store_true')
	args = vars(parser.parse_args(args))

	main(**args)


if __name__ == '__main__':
	cli()
