# AWS Lambda function for creating an image from a given instance.
# By Michael Ludvig - https://aws.nz

# Trigger this function from CloudWatch Scheduler (cron-like)
# Pass the Instance ID in 'instance_id' environment variable.

from __future__ import print_function
import os
import boto3
from datetime import datetime, timedelta
import time

ec2 = boto3.client('ec2')
cfn = boto3.client('cloudformation')
asc = boto3.client('autoscaling')

def find_asg_instances(asg_name):
    ids = []
    try:
        r = asc.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        asg = r['AutoScalingGroups'][0]
        for i in asg['Instances']:
            if i['LifecycleState'] == 'InService':
                ids.append(i['InstanceId'])
        return ids
    except:
        print('%s - Unable to list InService instances' % asg_name)
        raise

def create_image(instance_id):
    def _print_log(message):
        print('%s @ %s: %s' % (instance_id, snapshot_timestamp, message))

    snapshot_timestamp = datetime.strftime(datetime.now(), '%s')
    _print_log('Snapshotting instance')
    instance = ec2.describe_instances(InstanceIds=[instance_id])
    description = ''
    tags = {}

    try:
        tags = {item['Key']:item['Value'] for item in instance['Reservations'][0]['Instances'][0]['Tags']}
    except:
        pass

    if 'Name' in tags:
        description = tags['Name']
    elif 'aws:cloudformation:stack-name' in tags:
        description = tags['aws:cloudformation:stack-name']
    else:
        description = instance_id

    name = instance_id + '_' + snapshot_timestamp
    description = description + ' ' + datetime.strftime(datetime.now(), '%Y-%m-%d %H-%M-%S')
    r = ec2.create_image(InstanceId = instance_id, Name = name, Description = description, NoReboot = False)
    image_id = r['ImageId']
    _print_log('Created image: id=%s name=%s' % (image_id, name))
    image_tags = [
        {'Key': 'SnapshotTimestamp', 'Value': snapshot_timestamp },
        {'Key': 'InstanceId', 'Value': instance_id }
    ]
    if 'Name' in tags:
        image_tags.append({ 'Key': 'Name', 'Value': tags['Name'] })
    ec2.create_tags(Resources = [image_id], Tags = image_tags)
    image_tags_string = ' '.join(map(lambda x: '%(Key)s=%(Value)s' % x, image_tags))
    _print_log('Created tags: %s' % (image_tags_string))

    return (image_id, snapshot_timestamp)

def update_cfn_stack(stack_name, image_id_param, image_id):
    stack = cfn.describe_stacks(StackName = stack_name)
    params_new = []
    for param in stack['Stacks'][0]['Parameters']:
        if param['ParameterKey'] != image_id_param:
            params_new.append(param)
        else:
            params_new.append({'ParameterKey': image_id_param, 'ParameterValue': image_id})
    cfn.update_stack(StackName = stack_name, UsePreviousTemplate = True, Parameters = params_new, Capabilities=['CAPABILITY_IAM'])
    print('%s - Updated parameter %s to %s' % (stack_name, image_id_param, image_id))

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
        print('Environment variables [asg_name, cfn_stack, cfn_ami_parameter, retain_days] must be set')
        raise

    ids = find_asg_instances(asg_name)
    if len(ids) < 1:
        print('%s - No instances InService found' % asg_name)
        raise
    if len(ids) > 1:
        print('%s - Too many InService instances in ASG. This only works with min=max=1 ASGs!' % asg_name)
        raise

    instance_id = ids[0]

    image_id, snapshot_timestamp = create_image(instance_id)
    update_cfn_stack(cfn_stack_name, cfn_ami_parameter, image_id)
    deregister_old_images(instance_id, retain_days)

    return image_id
