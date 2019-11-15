import os

from yaml import load, Loader

with open('{0}/../static/swagger.yaml'.format(os.path.dirname(__file__)), 'r') as scheme_source:
    schemes = load(scheme_source, Loader=Loader)

AUTHENTICATE_CREATE = schemes['components']['schemas']['Authenticate_POST']

CREDENTIALS_CREATE = schemes['components']['schemas']['Common_Credential_POST']

INSTANCES_CREATE = schemes['components']['schemas']['Instance_POST']

PERMISSIONS_CREATE = schemes['components']['schemas']['Permission_POST']
PERMISSIONS_UPDATE = schemes['components']['schemas']['Permission_PUT']

USERS_CREATE = schemes['components']['schemas']['User_POST']
USERS_UPDATE = schemes['components']['schemas']['User_PUT']
