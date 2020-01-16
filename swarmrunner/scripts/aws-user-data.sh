#!/bin/bash

mkdir -p /etc/systemd/system/swarmrunner.service.d
{
printf $'[Service]\n'
keys=( $(curl http://169.254.169.254/latest/meta-data/) )
for key in "${keys[@]}"; do
	case "$key" in
	(*/*) continue;;
	esac

	value=$(curl http://169.254.169.254/latest/meta-data/$key)
	key=${key^^}
	key=${key//-/_}
	eval "AWS_$key=\$value"
	printf $'Environment="%s=%s"\n' AWS_$key "$value"
done
AWS_INSTANCE_NUMBER=$(curl http://accona.eecs.utk.edu:8810/count/$AWS_INSTANCE_TYPE --data-binary '')
printf $'Environment="%s=%s"\n' AWS_INSTANCE_NUMBER "$AWS_INSTANCE_NUMBER"
} |
tee /etc/systemd/system/swarmrunner.service.d/local.conf

systemctl daemon-reload
systemctl restart swarmrunner
