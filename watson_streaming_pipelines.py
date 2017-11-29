from tempfile import NamedTemporaryFile
import requests  
import json  
import pickle
import gzip
import numpy as np
from io import StringIO
import os
import logging

logging.basicConfig( level=logging.ERROR, format='%(asctime)s : %(name)s.%(funcName)s : %(levelname)s : %(message)s')
wstpLogger = logging.getLogger('wstp')

def setLogLevel( logLevel):
    "Log levels: CRITICAL=50, ERROR=40, WARNING=30, INFO=20, DEBUG=10, NOTSET=0"
    wstpLogger.setLevel( logLevel)

def serializeObject(pythonObj):
    return pickle.dumps(pythonObj, pickle.HIGHEST_PROTOCOL)

def deserializeObject(pickledObj):
    return pickle.loads(pickledObj)

# Raanon
def pickleSerializer( data, zip=False):
    pickledData = None
    try:
        if data:
            pickledData = serializeObject( data)
            if zip:
                pickledData = gzip.compress( pickledData)
    except Exception as e:
        wstpLogger.error( str(e))
    return pickledData

# Raanon
def deserializePickle( pickledObj):
    depickledObj = None
    try:
        if pickledObj:
            if pickledObj.startswith(b"\x1f\x8b\x08"): # Magic signature for gzip
                pickledObj = gzip.decompress( pickledObj)
            depickledObj = deserializeObject( pickledObj)
    except Exception as e:
        wstpLogger.error( str(e))
    return depickledObj

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
    wstpLogger.warning('my_data ' + str(len(my_data)))
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
    
       
def put_to_cloud_object_storage(api_key, full_object_path, my_data, auth_endpoint="https://iam.ng.bluemix.net/oidc/token", service_endpoint="https://s3-api.us-geo.objectstorage.softlayer.net"): 
    wstpLogger.warning('my_data ' + str(len(my_data)))
    response=requests.post(
                url=auth_endpoint,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                params={"grant_type":"urn:ibm:params:oauth:grant-type:apikey","apikey":api_key},
                verify=True)
    access_token=response.json()["access_token"]

    response=requests.put(
                url=service_endpoint+"/"+full_object_path,
                headers={"Authorization": "bearer " + access_token},
                data = my_data)
                
    return response

def get_from_cloud_object_storage(api_key, full_object_path, auth_endpoint="https://iam.ng.bluemix.net/oidc/token", service_endpoint="https://s3-api.us-geo.objectstorage.softlayer.net"):
    response=requests.post(
                url=auth_endpoint,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                params={"grant_type":"urn:ibm:params:oauth:grant-type:apikey","apikey":api_key},
                verify=True)
    access_token=response.json()["access_token"]

    response=requests.get(
                url=service_endpoint+"/"+full_object_path,
                headers={"Authorization": "bearer " + access_token},
                params=None,
                verify=True)

    return response.content
        
# Raanon
def get_from_cos( credentials, full_object_path, serializer):

    serializedObj = None
    deserializedObj = None
    try:
        wstpLogger.warning( full_object_path)
        serializedObj = get_from_cloud_object_storage(
            api_key          = credentials['api_key'],
            full_object_path = full_object_path,
            auth_endpoint    = credentials['iam_url'],
            service_endpoint = credentials['endpoint']
        )
        deserializedObj = serializer( serializedObj) if serializer else serializedObj
        #wstpLogger.warning( deserializedObj)
    except Exception as e:
        wstpLogger.error( str(e))

    wstpLogger.warning( "Retrieved (" + str(len(serializedObj if serializedObj else "")) + 
                   "). Deserialized (" + str(len(str(deserializedObj) if deserializedObj else "")) + ")")

    return deserializedObj

# Raanon
def put_to_cos( credentials, full_object_path, serializedData):

    wstpLogger.warning( full_object_path + " (" + str(len(serializedData if serializedData else "")) + ")")
    try:
        if serializedData:
            response = put_to_cloud_object_storage(
                api_key          = credentials['api_key'],
                full_object_path = full_object_path,
                my_data          = serializedData,
                auth_endpoint    = credentials['iam_url'],
                service_endpoint = credentials['endpoint']
            )
            wstpLogger.warning( response)
    except Exception as e:
        wstpLogger.error( str(e) + "\n" + response if response else "")

# Raanon
def setStopWordList():

    stoplist = {}
    try:
        import nltk
        nltk.download("stopwords")
        stoplist = set(nltk.corpus.stopwords.words("english"))
    except:
        stoplist = {}

    if len(stoplist) == 0: # Default, just in case
        stoplist = {'because', 'during', 'was', 'itself', 'should', 'by', 'haven', 'yourself', 'been', 're', 'ain', 'hadn', 'had', 'again', 'what', 'they', 'themselves', 'whom', 'you', 'all', 'both', 'on', 'isn', 'his', 'ourselves', 'that', 't', 'm', 'is', 'this', 'how', 'when', 'will', 'against', 'her', 'with', 'couldn', 'being', 'hasn', 'be', 'it', 'but', 'no', 'than', 'don', 'most', 'now', 'while', 'doesn', 'our', 'from', 'are', 'he', 'so', 'shouldn', 've', 'y', 'as', 'we', 'll', 's', 'himself', 'my', 'about', 'more', 'where', 'down', 'there', 'just', 'nor', 'theirs', 'such', 'who', 'to', 'before', 'him', 'me', 'has', 'o', 'its', 'were', 'did', 'can', 'same', 'then', 'have', 'few', 'aren', 'd', 'other', 'further', 'and', 'off', 'these', 'an', 'wasn', 'hers', 'your', 'weren', 'until', 'only', 'does', 'shan', 'i', 'own', 'not', 'or', 'myself', 'through', 'some', 'didn', 'at', 'out', 'why', 'needn', 'doing', 'above', 'after', 'wouldn', 'yourselves', 'very', 'having', 'herself', 'a', 'the', 'am', 'if', 'into', 'once', 'won', 'too', 'up', 'ours', 'here', 'those', 'each', 'in', 'over', 'ma', 'them', 'under', 'for', 'mustn', 'yours', 'mightn', 'below', 'between', 'which', 'do', 'any', 'she', 'of', 'their'}

    return stoplist

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
