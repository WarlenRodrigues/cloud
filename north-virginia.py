from dotenv import load_dotenv
import boto3
import os

# setting up aws credentials with .env lib
load_dotenv()

AWS_CLIENTS_REGION = os.getenv("AWS_CLIENTS_REGION")

clients_aws_session = boto3.session.Session(region_name=AWS_CLIENTS_REGION)

ec2 = clients_aws_session.resource('ec2')

instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    print(instance.id, instance.instance_type)
