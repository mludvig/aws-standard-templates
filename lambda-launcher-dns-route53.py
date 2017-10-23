#!/usr/bin/python

# AWS Lambda function that updates a given Route53 RR
# with Private IP of a newly launched instance in ASG.
# The ASG should be configured with min=1/max=1.

# The Route53 host name and zone id must be provided
# in the function environment, e.g.
# dns_name = aws.example.com
# hosted_zone_id = Z1234567890ABC
#
# The Instance IP will be figured out from the SNS notification

# By Michael Ludvig - https://aws.nz

import os
import json
import boto3

ec2 = boto3.client('ec2')
route53 = boto3.client('route53')

def update_dns(instance, hosted_zone_id, dns_name):
    print('%s - Updating %s to %s' % (instance['InstanceId'], dns_name, instance['PrivateIpAddress']))

    response = route53.change_resource_record_sets(
        HostedZoneId = hosted_zone_id,
        ChangeBatch = {
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': dns_name,
                        'Type': 'A',
                        'TTL': 60,
                        'ResourceRecords': [ { 'Value': instance['PrivateIpAddress'] } ]
                    }
                }
            ]
        }
    )
    if not response:
        print('%s - Update for %s to %s failed' % (instance['InstanceId'], dns_name, instance['PrivateIpAddress']))
        raise
    print('%s - Updated %s to %s' % (instance['InstanceId'], dns_name, instance['PrivateIpAddress']))
    return

def lambda_handler(event, context):
    try:
        hosted_zone_id = os.environ['hosted_zone_id']
        dns_name = os.environ['dns_name']
    except:
        print('Environment variables [hosted_zone_id, dns_name] must be set')
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
        update_dns(instance, hosted_zone_id, dns_name)
