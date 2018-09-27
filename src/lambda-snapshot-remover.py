# AWS Lambda function for creating an image from a given instance.
# By Michael Ludvig - https://aws.nz

# Remove old snapshots created by lambda-snapshot-asg.py / lambda-snapshot-instance.py
# Pass the Autoscaling Group name in 'asg_name' environment variable, or
# Pass the Instance ID in 'instance_id' environment variable.

import os
import boto3
from datetime import datetime, timedelta
import time

ec2 = boto3.client('ec2')

def deregister_old_images(asg_name, instance_id, retain_days):
    oldest_time = datetime.now() - timedelta(days = retain_days)
    oldest_timestamp = int(time.mktime(oldest_time.timetuple()))
    print('Purging images older than: %s' % oldest_time.strftime('%Y-%m-%d %H-%M-%S'))

    filters = [
        { 'Name': 'tag-key', 'Values': [ 'SnapshotTimestamp' ] }
    ]
    if asg_name:
        filters.append({ 'Name': 'tag:AsgName', 'Values': [ asg_name ] })
    if instance_id:
        filters.append({ 'Name': 'tag:InstanceId', 'Values': [ instance_id ] })
    images = ec2.describe_images(Owners=['self'], Filters=filters)
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
        asg_name = os.environ.get('asg_name')
        instance_id = os.environ.get('instance_id')
        assert(asg_name or instance_id)
        retain_days = int(os.environ['retain_days'])
    except:
        print('ERROR: Environment variables must be set: asg_name or instance_id, retain_days')
        raise

    deregister_old_images(asg_name, instance_id, retain_days)
