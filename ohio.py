from dotenv import load_dotenv
import boto3
import os
import time

# setting up aws credentials with .env lib
load_dotenv()


class PostgresProvider():
    def __init__(self):
        print("Setting variables... \n")
        self.region = os.getenv("AWS_DB_REGION")
        self.image_id = 'ami-0dd9f0e7df0f0a138'
        self.ec2_tags = [
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
        self.created_sg_id = None
        self.instances = None

        self.userdata = '''#!/bin/bash
                            sudo apt update
                            sudo apt install postgresql postgresql-contrib -y
                            sudo -u postgres sh -c "psql -c \\"CREATE USER cloud WITH PASSWORD 'cloud';\\" && createdb -O cloud tasks"
                            sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" /etc/postgresql/10/main/postgresql.conf      
                            sudo sed -i "a\host all all 0.0.0.0/0 md5" /etc/postgresql/10/main/pg_hba.conf
                            sudo ufw allow 5432/tcp
                            sudo systemctl restart postgresql
                            '''

        # Boto3 AWS entrypoints
        print("Creating AWS connections... \n")
        self.session = boto3.session.Session(region_name=self.region)
        self.client = self.session.client('ec2', region_name=self.region)
        self.ec2 = self.session.resource('ec2')
        print("AWS connections created... \n")

    def clean_aws_env(self):
        print(f"Cleaning {self.region} region... \n")
        running_instances = []

        # Cleaning AWS env
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'tag:Owner', 'Values': ['warlen']}])
        for instance in instances:
            running_instances.append(instance.id)

        # Terminate all instances before start creation proccess
        self.ec2.instances.filter(InstanceIds=running_instances).terminate()
        print(f"Killing {self.region} instances... \n")

        self.client.get_waiter('instance_terminated').wait(
            InstanceIds=running_instances)

        print(f"{self.region} instances killed... \n")
        # Deleting Security Groups
        sg = self.client.describe_security_groups()
        for sec in sg["SecurityGroups"]:
            if sec['GroupName'] == 'postgresDB':
                self.client.delete_security_group(
                    GroupId=sec["GroupId"], GroupName=sec["GroupName"])
        print(f"{self.region} security groups deleted... \n")

    def create_sg(self, name):
        print(f"Creating security group... \n")

        res = self.client.describe_vpcs()
        vpc_id = res.get('Vpcs', [{}])[0].get('VpcId', '')

        try:
            response = self.client.create_security_group(
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
                ])

            self.created_sg_id = response['GroupId']

            try:
                allowing_ingress = self.client.authorize_security_group_ingress(
                    GroupId=self.created_sg_id,
                    IpPermissions=[
                        {'IpProtocol': 'tcp',
                            'FromPort': 5432,
                            'ToPort': 5432,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                    ])

                allowing_egress = self.client.authorize_security_group_egress(
                    GroupId=self.created_sg_id,
                    IpPermissions=[
                        {'IpProtocol': 'tcp',
                            'FromPort': 5432,
                            'ToPort': 5432,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                    ])

                print("All permissions set @ postgresDB Security Group... \n")
            except:
                print("Failed setting permissions to postgresDB Security Group! \n")

            print("Succeed @ creating Security Group postgresDB... \n")

        except:
            print("Failed @ creating Security Group postgresDB! \n")

    def create_instace(self):
        print("Creating EC2 instance postgreSQL Host Server... \n")
        self.instances = self.ec2.create_instances(
            InstanceType="t2.micro",
            ImageId=self.image_id,
            MinCount=1,
            MaxCount=1,
            KeyName="db_servers",
            TagSpecifications=self.ec2_tags,
            SecurityGroups=['postgresDB'],
            UserData=self.userdata
        )
        print("Created EC2 instance postgreSQL Host Server... \n")

    def setting_env_up(self):
        # Create Sec Group to give postgreSQL necessary iu and out permissions
        self.create_sg('postgresDB')
        # Create Instance to run PostgreSQL and provide DB
        self.create_instace()
        # must run $sudo chmod 600 /path/to/my/key.pem to ensure key security if wants to ssh the instance

    def get_instance_ip(self):
        print("Getting server public IP Address... This may take a while... \n")
        time.sleep(30)
        response = self.client.describe_instances(
            InstanceIds=[self.instances[0].id])
        instance = response['Reservations'][0]['Instances'][0]
        ip = instance['PublicIpAddress']
        print(f"PostgreSQL running at {ip}")
        return ip
