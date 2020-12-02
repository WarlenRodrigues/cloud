from dotenv import load_dotenv
from botocore.exceptions import ClientError
import boto3
import os
import time

# setting up aws credentials with .env lib
load_dotenv()


class ClientProvider():
    def __init__(self, db_ip):
        print("Setting variables... \n")
        self.region = os.getenv("AWS_CLIENTS_REGION")
        self.image_id = 'ami-08f4fc689c28118cf'
        self.ec2_tags = [
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'Django Client Model'
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

        self.userdata = f'''#!/bin/bash
                            cd /home/ubuntu/
                            sudo apt update
                            sudo apt install python3-pip -y
                            git clone https://github.com/WarlenRodrigues/tasks.git
                            cd tasks
                            cd portfolio
                            sudo sed -i "s/node1/{db_ip}/g" settings.py
                            cd ..
                            ./install.sh
                            sudo reboot
                            '''

        # Boto3 AWS entrypoints
        print("Creating AWS connections... \n")
        self.session = boto3.session.Session(region_name=self.region)
        self.client = self.session.client('ec2', region_name=self.region)
        self.ec2 = self.session.resource('ec2')
        self.elb = self.session.client('elb')
        self.autoscalling = self.session.client('autoscaling')

        self.ami_id = None
        print("AWS connections created... \n")

    def clean_aws_env(self):
        print(f"Cleaning {self.region} region... \n")

        images = self.client.describe_images(
            Filters=[{'Name': 'name', 'Values': ['WebServerAMI']}])

        if len(images['Images']) > 0:
            self.client.deregister_image(
                ImageId=images['Images'][0]['ImageId'])

        running_instances = []

        # Cleaning AWS env
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}, {'Name': 'tag:Owner', 'Values': ['warlen']}])
        for instance in instances:
            running_instances.append(instance.id)

        # Terminate all instances before start creation proccess

        print(f"Killing {self.region} instances... \n")
        waiter = self.client.get_waiter('instance_terminated')
        destroyer = self.ec2.instances.filter(
            InstanceIds=running_instances).terminate()
        waiter.wait(InstanceIds=running_instances)

        print(f"{self.region} instances killed... \n")
        # Deleting Security Groups
        try:
            sg = self.client.describe_security_groups()
            if len(sg["SecurityGroups"]):
                for sec in sg["SecurityGroups"]:
                    if sec['GroupName'] == 'clientsSG2':
                        self.client.delete_security_group(
                            GroupId=sec["GroupId"], GroupName=sec["GroupName"])
                print(f"{self.region} security groups deleted... \n")
        except:
            print(f"{self.region} security groups were not deleted!!! \n")

    def create_sg(self, name):
        print(f"Creating security group... \n")

        res = self.client.describe_vpcs()
        vpc_id = res.get('Vpcs', [{}])[0].get('VpcId', '')

        try:
            response = self.client.create_security_group(
                Description='Allow SSH',
                GroupName='clientsSG2',
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
                            'FromPort': 22,
                            'ToPort': 22,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
                            'FromPort': 8080,
                            'ToPort': 8080,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                    ])

                allowing_egress = self.client.authorize_security_group_egress(
                    GroupId=self.created_sg_id,
                    IpPermissions=[
                        {'IpProtocol': 'tcp',
                            'FromPort': 22,
                            'ToPort': 22,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                        {'IpProtocol': 'tcp',
                            'FromPort': 8080,
                            'ToPort': 8080,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                    ])

                print("All permissions set @ clientsSG2 Security Group... \n")
            except:
                print("Failed setting permissions to clientsSG2 Security Group! \n")

            print("Succeed @ creating Security Group clientsSG2... \n")

        except:
            print("Failed @ creating Security Group clientsSG2! \n")

    def create_instace(self):
        waiter = self.client.get_waiter('instance_status_ok')
        print("Creating Client Model EC2 instance... \n")
        self.instances = self.ec2.create_instances(
            InstanceType="t2.micro",
            ImageId=self.image_id,
            MinCount=1,
            MaxCount=1,
            KeyName="warlen",
            TagSpecifications=self.ec2_tags,
            SecurityGroups=['clientsSG2'],
            UserData=self.userdata
        )
        waiter.wait(InstanceIds=[self.instances[0].id])
        print("Created Client Model EC2 instance... \n")

    def setting_env_up(self):
        # Create Sec Group to give clients necessary iu and out permissions
        self.create_sg('clientsSG2')
        # Create Instance to run clients and provide DB
        self.create_instace()

    def get_instance_ip(self):
        print("Getting server public IP Address... This may take a while... \n")
        time.sleep(30)
        response = self.client.describe_instances(
            InstanceIds=[self.instances[0].id])
        instance = response['Reservations'][0]['Instances'][0]
        ip = instance['PublicIpAddress']
        print(f"Client running at {ip} \n")

    def create_ami(self):
        print("Started image creation proccess... \n")
        try:
            waiter = self.client.get_waiter('image_available')
            image = self.client.create_image(
                InstanceId=self.instances[0].id, Name="WebServerAMI")
            waiter.wait(ImageIds=[image['ImageId']])

            print("Webserver image creation complete... \n")
            self.ami_id = image['ImageId']
            return image['ImageId']
        except ClientError as e:
            print("Webserver image failed!!! \n")
            print(f"ERROR: {e}")

    def create_load_balancer(self):
        print("Creating Load Balancer... \n")
        try:
            subnets = self.ec2.subnets.all()
            subnets_id = [s.id for s in subnets]
            load_balancer = self.elb.create_load_balancer(
                LoadBalancerName='WebServerLoadBalancer',
                Listeners=[
                    {
                        'Protocol': 'HTTP',
                        'LoadBalancerPort': 8080,
                        'InstancePort': 8080,
                    },
                ],
                Subnets=subnets_id,
                SecurityGroups=[self.created_sg_id],
                Tags=[
                    {
                        'Key': 'Name',
                        'Value': 'WebServerLoadBalancer'
                    },
                    {
                        'Key': 'Owner',
                        'Value': 'warlen'
                    },
                ])
            time.sleep(40)
            print("Created Load Balancer... \n")

        except ClientError as e:
            print('\nERRO:', e)

    def create_launch_configuration(self):
        print("Creating Launch Configuration... \n")
        try:
            launch_configuration = self.autoscalling.create_launch_configuration(
                LaunchConfigurationName='WebServerConfigs',
                ImageId=self.ami_id,
                KeyName='warlen',
                SecurityGroups=[self.created_sg_id],
                InstanceType='t2.micro',
                InstanceMonitoring={'Enabled': True},
            )
            print("Still working in Lauch Configuration creation... \n")
            time.sleep(40)
            print("Launch Configuration created... \n")
        except ClientError as e:
            print('\nERRO:', e)

    def create_autoscaling(self):
        print("Creating AutoScaling... \n")
        try:
            AvailabilityZones = [zone['ZoneName'] for zone in self.client.describe_availability_zones()[
                'AvailabilityZones']]
            response = self.autoscalling.create_auto_scaling_group(
                AutoScalingGroupName='WebServerAutoScalling',
                LaunchConfigurationName='WebServerConfigs',
                LoadBalancerNames=['WebServerLoadBalancer'],
                AvailabilityZones=AvailabilityZones,
                DesiredCapacity=2,
                MinSize=2,
                MaxSize=5,
            )
            print("AutoScalling completelly set... \n")

        except ClientError as e:
            print('Error', e)
