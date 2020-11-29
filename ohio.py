from dotenv import load_dotenv
import boto3
import os

# setting up aws credentials with .env lib
load_dotenv()

AWS_DB_REGION = os.getenv("AWS_DB_REGION")
DB_SEC_GROUP = os.getenv('DB_SEC_GROUP')

IMAGE_ID = 'ami-0dd9f0e7df0f0a138'
DEFAULT_TAGS = [
    {
        'ResourceType': 'instance',
        'Tags': [
            {
                'Key': 'Name',
                'Value': 'MySQL Host Server'
            },
            {
                'Key': 'Owner',
                'Value': 'warlen'
            },
        ]
    }
]

userdata = '''#!/bin/bash
echo "Starting environment settings..." > /home/ubuntu/logs.txt
echo "STARTING MySQL INSTALLATION..." > /home/ubuntu/logs.txt
echo "SUDO APT UPDATE" > /home/ubuntu/logs.txt
sudo apt update > /home/ubuntu/logs.txt
echo "SUDO APT INSTALL mysql-server" > /home/ubuntu/logs.txt
sudo apt install mysql-server -y > /home/ubuntu/logs.txt
echo "SUDO mysql_secure_installation" > /home/ubuntu/logs.txt
sudo mysql_secure_installation -y > /home/ubuntu/logs.txt
echo "SQL SHOULD BE WORKING FROM NOW ON" > /home/ubuntu/logs.txt
systemctl status mysql.service > /home/ubuntu/logs.txt
'''

db_aws_session = boto3.session.Session(region_name=AWS_DB_REGION)

ec2 = db_aws_session.resource('ec2')

# Get current running instances
running_instances = []

instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
for instance in instances:
    running_instances.append(instance.id)

# Terminate all instances before start creation proccess
ec2.instances.filter(InstanceIds=running_instances).terminate()

# Create Instance to run MySQL and provide DB
ec2.create_instances(
    InstanceType="t2.micro",
    # TODO add security group
    ImageId=IMAGE_ID,
    MinCount=1,
    MaxCount=1,
    KeyName="db_servers",
    TagSpecifications=DEFAULT_TAGS,
    SecurityGroups=[DB_SEC_GROUP],
    UserData=userdata
)
# must run $sudo chmod 600 /path/to/my/key.pem to ensure key security if wants to ssh the instance


# instances = ec2.instances.filter(
#     Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
# for instance in instances:
#     print(instance.id, instance.instance_type)
