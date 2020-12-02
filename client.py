import requests
import boto3
from botocore.exceptions import ClientError
import datetime
import json
from dotenv import load_dotenv
import os

load_dotenv()

region = os.getenv("AWS_CLIENTS_REGION")
ACCESS_ID = os.getenv("AWS_ACCESS_KEY_ID")
ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

client = boto3.client('elb', aws_access_key_id=ACCESS_ID,
                      aws_secret_access_key=ACCESS_KEY, region_name=region)
ip_load_balancer = client.describe_load_balancers(
    LoadBalancerNames=['WebServerLoadBalancer'])['LoadBalancerDescriptions'][0]['DNSName']

print(ip_load_balancer)
# url = 'http://{}:8080/tasks'.format(ip_load_balancer)
url = 'http://0.0.0.0:8080/tasks'
while True:
    try:
        print(''' 
0 - Create Task
1 - Get All Tasks
2 - Delete Tasks
3 - Sair
            ''')
        menu = int(input("Selecione: "))

        if menu == 0:
            # post task
            task = {
                "title": str(input("Titulo Task: ")),
                "pub_date": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "description": str(input("Descrição Task: "))
            }

            r = requests.post(url + "/create", json=task)
            print("\nResponse:", r.text)

        elif menu == 1:
            # get all tasks
            r = requests.get(url + "/get_all")
            print("\nResponse:", r.text)
            # for i in json.dumps(r.text):
            #     print(i)

        elif menu == 2:
            # delete all tasks
            r = requests.delete(url + "/delete_all")
            print("\nResponse:", r.text)
        else:
            break
    except:
        print("\nERROR")
        break
