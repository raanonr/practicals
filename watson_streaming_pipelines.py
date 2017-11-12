from tempfile import NamedTemporaryFile
import requests  
import json  
import pickle
import numpy as np
from io import StringIO
import os

def serializeObject(pythonObj):
    return pickle.dumps(pythonObj, pickle.HIGHEST_PROTOCOL)

def deserializeObject(pickledObj):
    return pickle.loads(pickledObj)

def serializeKerasModel(model):
    with NamedTemporaryFile() as f:
        model.save(f.name)
        f.seek(0)
        obj = f.read() 
    return obj

def deserializeKerasModel(obj):
    from keras.models import Model,load_model
    with NamedTemporaryFile(mode='wb') as f:
        f.write(obj)
        f.flush()
        model = load_model(f.name)  
    return model
    
def serializeNumpyArray(arr):
    with NamedTemporaryFile() as f:
        np.save(f, arr)
        f.seek(0)
        obj = f.read()  
        f.close()
    return obj  
    
def serializeFile(path):
    with open(path, mode='rb') as f:
        obj = f.read()  
    return obj    

def put_to_objectstore(credentials, object_name, my_data, binary=True, region='dallas'):
    print('my_data', len(my_data))
    url1 = ''.join(['https://identity.open.softlayer.com', '/v3/auth/tokens'])
    data = {'auth': {'identity': {'methods': ['password'],
            'password': {'user': {'name': credentials['username'],'domain': {'id': credentials['domain_id']},
            'password': credentials['password']}}}}}
    headers1 = {'Content-Type': 'application/json'}
    resp1 = requests.post(url=url1, data=json.dumps(data), headers=headers1)
    resp1_body = resp1.json()
    for e1 in resp1_body['token']['catalog']:
        if(e1['type']=='object-store'):
            for e2 in e1['endpoints']:
                        if(e2['interface']=='public'and e2['region']==region):
                            url2 = ''.join([e2['url'],'/', credentials['container'], '/', object_name])
    s_subject_token = resp1.headers['x-subject-token']
    headers_accept = 'application/octet-stream' if (binary) else 'application/json' 
    headers2 = {'X-Auth-Token': s_subject_token, 'accept': headers_accept}
    resp2 = requests.put(url=url2, headers=headers2, data = my_data )

def get_from_objectstore(credentials, object_name, binary=True, region='dallas'):
    url1 = ''.join(['https://identity.open.softlayer.com', '/v3/auth/tokens'])
    data = {'auth': {'identity': {'methods': ['password'], 'password': {'user': {'name': credentials['username'],'domain': {'id': credentials['domain_id']}, 'password': credentials['password']}}}}}
    headers1 = {'Content-Type': 'application/json'}
    resp1 = requests.post(url=url1, data=json.dumps(data), headers=headers1)
    resp1_body = resp1.json()
    for e1 in resp1_body['token']['catalog']:
        if(e1['type']=='object-store'):
            for e2 in e1['endpoints']:
                        if(e2['interface']=='public'and e2['region']==region):
                            url2 = ''.join([e2['url'],'/', credentials['container'], '/', object_name])
    s_subject_token = resp1.headers['x-subject-token']
    headers_accept = 'application/octet-stream' if (binary) else 'application/json' 
    headers2 = {'X-Auth-Token': s_subject_token, 'accept': headers_accept}
    resp2 = requests.get(url=url2, headers=headers2)
    res = resp2.content if (binary) else StringIO(resp2.text)
    return res
    
    
# Make sure to install: ibm-cos-sdk
# !pip install ibm-cos-sdk
# https://github.com/IBM/ibm-cos-sdk-python
def get_cloud_object_storage(apikey, resource_instance_id, auth_endpoint = 'https://iam.bluemix.net/oidc/token', service_endpoint = 'https://s3-api.us-geo.objectstorage.softlayer.net'):
    import boto3
    from botocore.client import Config
    cos = boto3.resource('s3',
                          ibm_api_key_id = apikey,
                          ibm_service_instance_id = resource_instance_id,
                          ibm_auth_endpoint = auth_endpoint,
                          config=Config(signature_version='oauth'),
                          endpoint_url = service_endpoint)
    return cos
                         
def put_to_cloud_object_storage(cos, bucket_name, object_name, my_data): 
    with NamedTemporaryFile() as f:
        f.write(my_data)
        cos.Bucket(bucket_name).upload_file(f.name, object_name)
        
def get_from_cloud_object_storage(cos, bucket_name, object_name): 
    obj = None
    path = None
    with NamedTemporaryFile(mode='wb', delete=False) as f:
        path = f.name
        cos.Bucket(bucket_name).download_file(object_name, path) 
    with open(path, mode='rb') as f:
        obj = f.read()    
    os.remove(path)
    return obj
        

# Make sure to install: ibm-cos-sdk
# !pip install ibm-cos-sdk
# https://github.com/IBM/ibm-cos-sdk-python
def create_messagehub_producer(username, password, kafka_brokers_sasl = [], sasl_mechanism = 'PLAIN', security_protocol = 'SASL_SSL', value_serializer=lambda v: json.dumps(v).encode('utf-8')):
    import ssl
    from kafka import KafkaProducer 
    from kafka.errors import KafkaError 

    if (kafka_brokers_sasl == []):
        kafka_brokers_sasl = [
            "kafka01-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka02-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka03-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka04-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka05-prod01.messagehub.services.us-south.bluemix.net:9093" 
        ] 

    # Create a new context using system defaults, disable all but TLS1.2
    context = ssl.create_default_context()
    context.options &= ssl.OP_NO_TLSv1
    context.options &= ssl.OP_NO_TLSv1_1

    producer = KafkaProducer(bootstrap_servers = kafka_brokers_sasl,
                             sasl_plain_username = username,
                             sasl_plain_password = password,
                             security_protocol = security_protocol,
                             ssl_context = context,
                             sasl_mechanism = sasl_mechanism,
                             value_serializer=value_serializer)
                             
    return producer
    
    
def create_messagehub_consumer(username, password, kafka_brokers_sasl = [], sasl_mechanism = 'PLAIN', security_protocol = 'SASL_SSL', value_deserializer=lambda v: json.loads(v).encode('utf-8')):
    import ssl
    from kafka import KafkaConsumer 
    from kafka.errors import KafkaError 

    if (kafka_brokers_sasl == []):
        kafka_brokers_sasl = [
            "kafka01-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka02-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka03-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka04-prod01.messagehub.services.us-south.bluemix.net:9093",
            "kafka05-prod01.messagehub.services.us-south.bluemix.net:9093" 
        ] 

    # Create a new context using system defaults, disable all but TLS1.2
    context = ssl.create_default_context()
    context.options &= ssl.OP_NO_TLSv1
    context.options &= ssl.OP_NO_TLSv1_1

    consumer = KafkaConsumer(bootstrap_servers = kafka_brokers_sasl,
                             sasl_plain_username = username,
                             sasl_plain_password = password,
                             security_protocol = security_protocol,
                             ssl_context = context,
                             sasl_mechanism = sasl_mechanism,
                             value_deserializer=value_deserializer)
                             
    return consumer
