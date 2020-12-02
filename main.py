from ohio import PostgresProvider
from northVirginia import ClientProvider

print("\n\n ====== PROVISIONING DATABASE SERVER ====== \n\n")
db = PostgresProvider()
db.clean_aws_env()
db.setting_env_up()
db_ip = db.get_instance_ip()

print("\n\n ====== PROVISIONING WEBSERVER ====== \n\n")
webserver = ClientProvider(db_ip)
webserver.clean_aws_env()
webserver.setting_env_up()
webserver.get_instance_ip()
webserver.create_ami()
webserver.create_load_balancer()
webserver.create_launch_configuration()
webserver.create_autoscaling()
