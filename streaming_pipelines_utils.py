from io import BytesIO  
import requests  
import json  
from tempfile import NamedTemporaryFile

def put_to_objectstore(credentials, object_name, my_data):
    print('my_data', len(my_data))
    url1 = ''.join(['https://identity.open.softlayer.com', '/v3/auth/tokens'])
    data = {'auth': {'identity': {'methods': ['password'],
            'password': {'user': {'name': credentials['username'], 'domain': {'id': credentials['domain_id']},
            'password': credentials['password']}}}}}
    headers1 = {'Content-Type': 'application/json'}
    resp1 = requests.post(url=url1, data=json.dumps(data), headers=headers1)
    resp1_body = resp1.json()
    for e1 in resp1_body['token']['catalog']:
        if(e1['type']=='object-store'):
            for e2 in e1['endpoints']:
                        if(e2['interface']=='public'and e2['region']=='dallas'):
                            url2 = ''.join([e2['url'],'/', credentials['container'], '/', object_name])
    s_subject_token = resp1.headers['x-subject-token']
    headers2 = {'X-Auth-Token': s_subject_token, 'accept': 'application/json'}
    resp2 = requests.put(url=url2, headers=headers2, data = my_data )
    return resp2

def file2object(path):
    obj = {}
    with open(path, 'rb') as f:
        obj = f.read()  
    return obj

def gmodel2object(model):
    with NamedTemporaryFile() as f:
        model.save(f.name)
        obj = f.read()  
    return obj
