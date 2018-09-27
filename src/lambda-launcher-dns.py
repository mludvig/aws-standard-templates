#!/usr/bin/python

# AWS Lambda function that updates a given CFN Parameter
# with Private IP of a newly launched instance in ASG.
# The ASG should be configured with min=1/max=1.
#
# The Instance IP will be figured out from the SNS notification

# By Michael Ludvig - https://aws.nz

import os
import json
import boto3

ec2 = boto3.client('ec2')
cfn = boto3.client('cloudformation')

def update_cfn_stack(stack_name, param_name, param_value):
    stack = cfn.describe_stacks(StackName = stack_name)
    params_new = []
    for param in stack['Stacks'][0]['Parameters']:
        if param['ParameterKey'] != param_name:
            params_new.append(param)
        else:
            params_new.append({'ParameterKey': param_name, 'ParameterValue': param_value})
    cfn.update_stack(StackName = stack_name, UsePreviousTemplate = True, Parameters = params_new, Capabilities=['CAPABILITY_IAM'])
    print('%s - Updated parameter %s to %s' % (stack_name, param_name, param_value))

def lambda_handler(event, context):
    try:
        cfn_stack_name = os.environ['cfn_stack_name']
        cfn_param_name = os.environ['cfn_param_name']
    except:
        print('Environment variables [cfn_stack_name, cfn_param_name] must be set')
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
            print('%s - Processing launch actions' % (instance_id))
            #print('%r' % instance)
            update_cfn_stack(cfn_stack_name, cfn_param_name, instance['PrivateIpAddress'])
        except IndexError as e:
            print('%s - Instance not found' % instance_id)
            raise
