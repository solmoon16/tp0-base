import sys, yaml

args = sys.argv
file_name = args[1]
client_num = int(args[2])

with open(file_name, 'r') as f:
    dic = yaml.safe_load(f)

services = dic['services']
client = services['client1']

for i in range(0, client_num):
    name = 'client'+str(i+1)
    client['container_name'] = name
    services[name] = client.copy()

yaml.Dumper.ignore_aliases = lambda *args : True

with open(file_name, 'w') as f:
    yaml.dump(dic, f)
