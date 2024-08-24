import sys, yaml

args = sys.argv
file_name = args[1]
client_num = int(args[2])

dic = {'name': 'tp0', 
       'services': 
            {'server': 
                {'container_name': 'server', 'image': 'server:latest', 'entrypoint': 'python3 /main.py', 'environment': ['PYTHONUNBUFFERED=1', 'LOGGING_LEVEL=DEBUG'], 'networks': ['testing_net']}, 
            'client1': 
                {'container_name': 'client1', 'image': 'client:latest', 'entrypoint': '/client', 'environment': ['CLI_ID=1', 'CLI_LOG_LEVEL=DEBUG'], 'networks': ['testing_net'], 'depends_on': ['server']
                }
            }, 
        'networks': 
            {'testing_net': 
                {'ipam': {'driver': 'default', 'config': [{'subnet': '172.25.125.0/24'}]}}}}

services = dic['services']
client = services['client1']

for i in range(0, client_num):
    name = 'client'+str(i+1)
    client['container_name'] = name
    services[name] = client.copy()

yaml.Dumper.ignore_aliases = lambda *args : True

with open(file_name, 'w') as f:
    yaml.dump(dic, f)
