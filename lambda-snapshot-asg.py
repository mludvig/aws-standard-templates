# AWS Lambda function for creating an image from a given instance.
# By Michael Ludvig - https://aws.nz

# Trigger this function from CloudWatch Scheduler (cron-like)
# Pass the Autoscaling Group name in 'asg_name' environment variable.

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

def create_image(asg_name, instance_id, reboot):
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

    name = asg_name+'_'+snapshot_timestamp
    description = description + ' ' + datetime.strftime(datetime.now(), '%Y-%m-%d %H-%M-%S')
    r = ec2.create_image(InstanceId = instance_id, Name = name, Description = description, NoReboot = not reboot)
    image_id = r['ImageId']
    _print_log('Created image: id=%s name=%s' % (image_id, name))
    image_tags = [
        {'Key': 'SnapshotTimestamp', 'Value': snapshot_timestamp },
        {'Key': 'InstanceId', 'Value': instance_id },
        {'Key': 'AsgName', 'Value': asg_name },
    ]
    if 'Name' in tags:
        image_tags.append({ 'Key': 'Name', 'Value': tags['Name'] })
    if 'aws:cloudformation:stack-name' in tags:
        image_tags.append({ 'Key': 'StackName', 'Value': tags['aws:cloudformation:stack-name'] })

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

def lambda_handler(event, context):
    try:
        asg_name = os.environ['asg_name']
        cfn_stack_name = os.environ['cfn_stack_name']
        cfn_ami_parameter = os.environ['cfn_ami_parameter']
    except:
        print('ERROR: Environment variables must be set: asg_name, cfn_stack, cfn_ami_parameter')
        raise

    try:
        reboot = event.get('reboot', True)
        assert(type(event['reboot']) in [ bool, int ])
    except:
        print('ERROR: Event JSON expected: { "reboot": true / false }')
        raise

    ids = find_asg_instances(asg_name)
    if len(ids) < 1:
        print('%s - No instances InService found' % asg_name)
        raise
    if len(ids) > 1:
        print('%s - Too many InService instances in ASG. This only works with min=max=1 ASGs!' % asg_name)
        raise

    instance_id = ids[0]

    image_id, snapshot_timestamp = create_image(asg_name, instance_id, reboot)
    update_cfn_stack(cfn_stack_name, cfn_ami_parameter, image_id)

    return image_id
