from dotenv import load_dotenv
import boto3
import os

# setting up aws credentials with .env lib
load_dotenv()

AWS_DB_REGION = os.getenv("AWS_DB_REGION")
IMAGE_ID = 'ami-0dd9f0e7df0f0a138'

DEFAULT_TAGS = [
    {
        'ResourceType': 'instance',
        'Tags': [
            {
                'Key': 'Name',
                'Value': 'postgreSQL Host Server'
            },
            {
                'Key': 'Owner',
                'Value': 'warlen'
            },
        ]
    }
]

userdata = '''#!/bin/bash
sudo apt update
sudo apt install postgresql postgresql-contrib -y
sudo -u postgres sh -c "psql -c \\"CREATE USER cloud WITH PASSWORD 'cloud';\\" && createdb -O cloud tasks"
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/10/main/postgresql.conf      
sudo sed -i "a\host all all 0.0.0.0/0 md5" /etc/postgresql/10/main/pg_hba.conf
sudo systemctl restart postgresql
'''

# Boto3 AWS entrypoints
db_aws_session = boto3.session.Session(region_name=AWS_DB_REGION)
ec2 = db_aws_session.resource('ec2')
client = db_aws_session.client('ec2', region_name=AWS_DB_REGION)

# Cleaning AWS env
# Get current running instances
running_instances = []

instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    running_instances.append(instance.id)

# Terminate all instances before start creation proccess
ec2.instances.filter(InstanceIds=running_instances).terminate()

# Deleting Security Groups
sg = client.describe_security_groups()
for sec in sg["SecurityGroups"]:
    if sec['GroupName'] == 'postgresDB':
        client.delete_security_group(
            GroupId=sec["GroupId"], GroupName=sec["GroupName"])

# Preparing AWS env
# Create Sec Group to give postgreSQL necessary iu and out permissions

response = client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')

response = None

try:
    response = client.create_security_group(
        Description='Allow all IPs to reach our postgres db',
        GroupName='postgresDB',
        VpcId=vpc_id,
        TagSpecifications=[
            {
                'ResourceType': 'security-group',
                'Tags': [
                    {
                        'Key': 'Owner',
                        'Value': 'warlen'
                    },
                ]
            },
        ],
        DryRun=True
    )
    print("Succeed @ creating Security Group postgresDB")

    security_group_id = response['GroupId']

    allowing_ingress = client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])

    allowing_egress = client.authorize_security_group_egress(
        GroupId=security_group_id,
        IpPermissions=[
            {'IpProtocol': 'tcp',
                'FromPort': 5432,
                'ToPort': 5432,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ])

    print("All permissions set @ postgresDB Security Group")
except:
    print("Failed @ creating Security Group postgresDB")


# Create Instance to run MySQL and provide DB
ec2.create_instances(
    InstanceType="t2.micro",
    ImageId=IMAGE_ID,
    MinCount=1,
    MaxCount=1,
    KeyName="db_servers",
    TagSpecifications=DEFAULT_TAGS,
    SecurityGroups=["postgresDB"],
    UserData=userdata
)
# must run $sudo chmod 600 /path/to/my/key.pem to ensure key security if wants to ssh the instance

running_instances = []

instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    print(instance.id, instance.instance_type)

res = client.describe_instances(InstanceIds=[running_instances[0], ])
ip = res['Reservations'][0]['Instances'][0]["PublicIpAddress"]

print(ip)
