#!/bin/bash

instances=( $(aws ec2 describe-instances --filters  "Name=instance-state-name,Values=pending,running,stopped,stopping" --query "Reservations[].Instances[].[InstanceId]" --output text | tr '\n' ' ') )
aws ec2 terminate-instances --instance-ids "${instances[@]}"
