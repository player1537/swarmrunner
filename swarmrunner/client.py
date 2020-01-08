#!/usr/bin/env python3.7
"""

"""

from __future__ import annotations
from typing import List, Dict, Tuple, Union
from pathlib import Path

import requests
from eliot import start_action, to_file, current_action
import petname


_g_session: requests.Session = None
_g_netloc: str = None
_g_name: str = None
_g_env: str = None


def eliot_request(*args, session=None, **kwargs):
	with start_action(action_type='eliot_request') as context:
		if session is None:
			context.log('Using global session')
			session = _g_session

		r = requests.Request(*args, **kwargs)
		r.headers['X-Eliot-Task'] = current_action().serialize_task_id()

		r = session.prepare_request(r)
		return _g_session.send(r)


def register():
	netloc = _g_netloc
	name = _g_name
	env = _g_env

	data = env

	with start_action(action_type='Register', name=name) as context:
		with eliot_request('POST', f'http://{netloc}/register/{name}', data=data) as r:
			content = r.content
			assert content == b'ok\r\n'


def listen():
	netloc = _g_netloc
	name = _g_name

	with start_action(action_type='Listen', name=name) as context:
		with eliot_request('GET', f'http://{netloc}/listen/{name}') as r:
			content = r.content
		
		return content


def main(command, netloc, logfile, name):
	to_file(open(logfile, 'ab'))
	session = requests.Session()
	
	env = 'x=y'
	
	global _g_session
	_g_session = session

	global _g_netloc
	_g_netloc = netloc

	global _g_name
	_g_name = name

	global _g_env
	_g_env = env

	with start_action(action_type='Client') as context:
		register()
		while True:
			content = listen()
			from time import sleep
			print('execute')
			sleep(10)
			

def cli():
	def random_name():
		return petname.Generate(2, '_')

	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument('command')
	parser.add_argument('netloc')
	parser.add_argument('--logfile', type=Path, default=Path.cwd() / 'log-client.txt')
	parser.add_argument('--name', default=random_name())
	args = vars(parser.parse_args())

	main(**args)


if __name__ == '__main__':
	cli()
