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

def deregister_old_images(asg_name, retain_days):
    oldest_time = datetime.now() - timedelta(days = retain_days)
    oldest_timestamp = int(time.mktime(oldest_time.timetuple()))
    print('Purging images older than: %s' % oldest_time.strftime('%Y-%m-%d %H-%M-%S'))

    images = ec2.describe_images(Owners=['self'], Filters=[
        { 'Name': 'tag:AsgName', 'Values': [ asg_name ] },
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
        retain_days = int(os.environ['retain_days'])
    except:
        print('ERROR: Environment variables must be set: asg_name, retain_days')
        raise

    deregister_old_images(asg_name, retain_days)
