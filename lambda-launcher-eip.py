#!/usr/bin/python

# AWS Lambda function that (re)associates the provided
# Elastic IP to a newly started instance in an Auto Scaling Group
# The ASG must be configured with min=1/max=1 obviously.

# The EIP must be provided in the function environment, e.g.
# elastic_ip = 54.12.34.56

# By Michael Ludvig - https://aws.nz

import os
import json
import boto3

ec2 = boto3.client('ec2')

def assign_eip(instance, elastic_ip):
    print('%s - Associate EIP %s' % (instance['InstanceId'], elastic_ip))

    old_public_ip = instance['PublicIpAddress']

    if old_public_ip == elastic_ip:
        print('%s - Instance already has EIP %s' % (instance['InstanceId'], elastic_ip))
        return

    response = ec2.associate_address(InstanceId=instance['InstanceId'], PublicIp=elastic_ip, AllowReassociation=True)
    if not response:
        print('Elastic IP %s not found' % elastic_ip)
        raise

    try:
        instances = ec2.describe_instances(InstanceIds=[instance['InstanceId']])
        instance = instances['Reservations'][0]['Instances'][0]
    except IndexError, e:
        print('%s - Instance not found' % instance['InstanceId'])
        raise

    new_public_ip = instance['PublicIpAddress']
    if new_public_ip != elastic_ip:
        print('%s - Association of EIP %s failed (currrent Public IP: %s)' %
                (instance['InstanceId'], elastic_ip, new_public_ip))
        raise

    print('%s - Elastic IP %s assigned, old IP was %s' % (instance['InstanceId'], new_public_ip, old_public_ip))
    return

def lambda_handler(event, context):
    try:
        elastic_ip = os.environ['elastic_ip']
    except:
        print('Environment variables [elastic_ip] must be set')
        raise

    for record in event['Records']:
        message = record['Sns']['Message']
        j = json.loads(message)
        if j['Event'] != 'autoscaling:EC2_INSTANCE_LAUNCH':
            print('Ignoring event: ' + j['Event'])
            continue
        instance_id = j['EC2InstanceId']
        try:
            instances = ec2.describe_instances(InstanceIds=[instance_id])
            instance = instances['Reservations'][0]['Instances'][0]
        except IndexError, e:
            print('%s - Instance not found' % instance_id)
            raise
        print('%s - Processing launch actions' % (instance_id))
        assign_eip(instance, elastic_ip)
