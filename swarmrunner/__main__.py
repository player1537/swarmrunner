"""

"""

from .server import cli as server_cli


def main(command, args):
	if command == 'server':
		server_cli(args)
	else:
		raise NotImplementedError


def cli(args=None):
	import argparse

	parser = argparse.ArgumentParser()
	parser.add_argument('command', choices=('client', 'server'))
	parser.add_argument('args', nargs=argparse.REMAINDER)
	args = vars(parser.parse_args(args))

	main(**args)


if __name__ == '__main__':
	cli()
