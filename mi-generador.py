import sys, yaml

args = sys.argv
file_name = args[1]
client_num = int(args[2])

dic = {'name': 'tp0', 
       'services': 
            {'server': 
                {'container_name': 'server', 'image': 'server:latest', 'entrypoint': 'python3 /main.py', 'networks': ['testing_net'], 
                 'volumes': ['$/home/solmoon/distribuidos/tp0-base/server/config.ini:/config.ini']}, 
            'client1': 
                {'container_name': 'client1', 'image': 'client:latest', 'entrypoint': '/client','networks': ['testing_net'], 'depends_on': ['server'],
                 'volumes': ['$/home/solmoon/distribuidos/tp0-base/client/config.yaml:/config.yaml']
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
