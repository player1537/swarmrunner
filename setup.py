#!/usr/bin/env python3.7

from distutils.core import setup

setup(
	name='swarmrunner',
	version='0.1.0',
	packages=[
		'swarmrunner',
	],
	package_data={
		'swarmrunner': [
			'static/*',
			'templates/*',
		],
	},
	entry_points={
		'console_scripts': [
			'swarmrunner-client=swarmrunner.client:cli',
			'swarmrunner-server=swarmrunner.server:cli',
		],
	},
	install_requires=[
		'requests',
		'jinja2',
		'petname',
	],
)
