# Copyright 2016 The Johns Hopkins University Applied Physics Laboratory
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Script to turn the boss on and off.
   ASG are shut down. Only execute this code if you are certain the boss will not
   be running for another hour."""

import boto3
import sys
import json
import argparse
import os

import alter_path
from lib import aws, utils

def main():

    choice = utils.get_user_confirm("Are you sure you want to switch the boss?")
    if choice:
        if len(sys.argv) < 2:
            sys.exit(0)
        else:
            action = sys.argv[1]

        if action == "on":
            print("Turning the BossDB on...")
            startInstances()

        if action == "off":
            print("Turning the BossDB off...")
            stopInstances()
        else:
            print("Usage: python bossSwitch.py {on|off}\n")
    elif choice == False:
        print("Action cancelled")
    else:
        print("Please respond with 'yes' or 'no'")

#Executed actions
def startInstances():
    print("Starting Instances...")

    client.update_auto_scaling_group(AutoScalingGroupName=endpoint, MinSize = 1 , MaxSize = 1 , DesiredCapacity = 1)
    client.resume_processes(AutoScalingGroupName=endpoint,ScalingProcesses=['HealthCheck'])

    client.update_auto_scaling_group(AutoScalingGroupName=activities, MinSize = 1 , MaxSize = 1 , DesiredCapacity = 1)
    client.resume_processes(AutoScalingGroupName=activities,ScalingProcesses=['HealthCheck'])

    client.update_auto_scaling_group(AutoScalingGroupName=auth, MinSize = 1 , MaxSize = 1 , DesiredCapacity = 1)
    client.resume_processes(AutoScalingGroupName=auth,ScalingProcesses=['HealthCheck'])

    # client.update_(instance_ids= "i-0506aeebdf1a9ac0e") #Developement endpoint
    print("The BossDB is on.")

def stopInstances():
    print("Stopping the Instances...")

    client.update_auto_scaling_group(AutoScalingGroupName=endpoint, MinSize = 0 , MaxSize = 0 , DesiredCapacity = 0)
    client.suspend_processes(AutoScalingGroupName=endpoint,ScalingProcesses=['HealthCheck'])

    client.update_auto_scaling_group(AutoScalingGroupName=activities, MinSize = 0 , MaxSize = 0 , DesiredCapacity = 0)
    client.suspend_processes(AutoScalingGroupName=activities,ScalingProcesses=['HealthCheck'])

    client.update_auto_scaling_group(AutoScalingGroupName=auth, MinSize = 0 , MaxSize = 0 , DesiredCapacity = 0)
    client.suspend_processes(AutoScalingGroupName=auth,ScalingProcesses=['HealthCheck'])

    print("The BossDB is off.")


if __name__ == '__main__':

    #Loading AWS configuration files.
    creds = json.load(open('../config/aws-credentials'))
    aws_access_key_id = creds["aws_access_key"]
    aws_secret_access_key = creds["aws_secret_key"]

    if creds is None:
        print("Error: AWS credentials not provided and AWS_CREDENTIALS is not defined")

    # specify AWS keys, sets up connection to the client.
    auth = {"aws_access_key_id": aws_access_key_id, "aws_secret_access_key": aws_secret_access_key}
    client = boto3.client('autoscaling', **auth)

    #Loading ASG configuration files. Please specify your ASG names on asg-cfg found in the config file.
    asg = json.load(open('../config/asg-cfg'))
    activities = asg["activities"]
    endpoint = asg["endpoint"]
    auth = asg["auth"]

    main()
