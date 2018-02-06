# AWS Lambda function for creating an image from a given instance.
# By Michael Ludvig - https://aws.nz

# Remove old snapshots created by lambda-snapshot-asg.py
# Pass the Autoscaling Group name in 'asg_name' environment variable.

from __future__ import print_function
import os
import boto3
from datetime import datetime, timedelta
import time

ec2 = boto3.client('ec2')
cfn = boto3.client('cloudformation')
asc = boto3.client('autoscaling')

def deregister_old_images(instance_id, retain_days):
    oldest_time = datetime.now() - timedelta(days = retain_days)
    oldest_timestamp = int(time.mktime(oldest_time.timetuple()))
    print('Purging images older than: %s' % oldest_time.strftime('%Y-%m-%d %H-%M-%S'))

    images = ec2.describe_images(Owners=['self'], Filters=[
        { 'Name': 'tag:InstanceId', 'Values': [ instance_id ] },
        { 'Name': 'tag-key', 'Values': [ 'SnapshotTimestamp' ] }
    ])
    for image in images['Images']:
        try:
            tags = {item['Key']:item['Value'] for item in image['Tags']}
            snapshot_timestamp = int(tags['SnapshotTimestamp'])
        except:
            continue
        if snapshot_timestamp < oldest_timestamp:
            print('%s: Deregistering image' % image['ImageId'])
            ec2.deregister_image(ImageId = image['ImageId'])
        else:
            print('%s: Retaining image: name=%s created=%s' % (image['ImageId'], image['Name'], image['CreationDate']))

def lambda_handler(event, context):
    try:
        asg_name = os.environ['asg_name']
        cfn_stack_name = os.environ['cfn_stack_name']
        cfn_ami_parameter = os.environ['cfn_ami_parameter']
        retain_days = int(os.environ['retain_days'])
    except:
        print('ERROR: Environment variables must be set: asg_name, cfn_stack, cfn_ami_parameter')
        raise

    ids = find_asg_instances(asg_name)
    if len(ids) < 1:
        print('%s - No instances InService found' % asg_name)
        raise
    if len(ids) > 1:
        print('%s - Too many InService instances in ASG. This only works with min=max=1 ASGs!' % asg_name)
        raise

    instance_id = ids[0]
    deregister_old_images(instance_id, retain_days)

    return image_id
