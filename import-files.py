#!/usr/bin/env python3

# Very simple pre-processor for embedding AWS Lambda functions
# into CloudFormation templates.
# - Replace %%{filename.py}%% with properly quoted contents
#   of filename.py
#
# JSON Example:
#
#    "MyLambda": {
#      "Type": "AWS::Lambda::Function",
#      "Properties": {
#        "Code": {
#          "ZipFile":  { "Fn::Join": [ "\n", [
#            %%{lambda.py}%%                <== Here comes the lambda.py contents
#          ] ] }
#    [...]
#
# YAML Example:
#
#    LaunchLambda
#      Type: AWS::Lambda::Function
#      Properties:
#        Code:
#          ZipFile:
#            Fn::Join:
#            - '
#
#              '
#            - - "# Import external file"
#              - "%%{lambda-launcher-dns.py}%%"

import sys
import re
import argparse

mode = "json"

parser = argparse.ArgumentParser(description='Import external files to a JSON or YAML template.')
parser.add_argument('file', type=argparse.FileType('r', encoding='UTF-8'), help='Input file with %%{filename}%% macros.')
parser.add_argument('--json', dest='mode', action='store_const', const='json', help='JSON mode')
parser.add_argument('--yaml', dest='mode', action='store_const', const='yaml', help='YAML mode')
args = parser.parse_args()

if not args.mode:
    if args.file.name.endswith('yaml') or args.file.name.endswith('yml'):
        args.mode = 'yaml'
    elif args.file.name.endswith('json'):
        args.mode = 'json'
    else:
        sys.stderr.write('Unknown file type, use --json or --yaml to specify\n')
        sys.exit(1)

lineno = 0
for line in args.file.readlines():
    lineno += 1
    line = line.rstrip('\n\r')
    # Don't embed comment lines
    if line.startswith('#'):
        continue
    m = re.match('^([ \t"\'-]+)%%{(.*)}%%(["\',]*)$', line)
    if not m:
        print(line)
        continue
    ## Here we import the external file
    prefix = m.group(1)
    import_file = m.group(2)
    suffix = m.group(3)
    with open(import_file) as f2:
        l2_out = None
        for l2 in f2.readlines():
            # JSON needs ',' at the end of each line, YAML doesn't
            if l2_out:
                print('%s%s' % (l2_out, args.mode == 'json' and ',' or ''))
            l2 = l2.rstrip('\n\r')
            l2_out = '%s%s%s' % (prefix, l2.replace('"', '\\"'), suffix)
        if l2_out:
            print(l2_out)
