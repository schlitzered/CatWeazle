Introduction
------------
CatWeazle is an application that will help you to register systems, in dynamic environments 
like AWS, to DNS (including A and PTR records) and RedHat IdM / FreeIPA.

DNS and IdM/IPA handling is mostly done using the "Smart Proxy" of the 
["The Foreman"](https://github.com/theforeman/smart-proxy) project. 
The Smart Proxy offers integration with most common DNS Servers, as well as RedHat IdM and FreeIPA.

AWS Route 53 integration is done directly in the API Server, using the AWS boto3 library. 
The reason for this is that the Smart Proxy Plugin for AWS will not support "Private hosted zones".

The API is described using the openapi, aka swagger, definition.
The definition can be found, when running the api server, [here](http://localhost:9000/static/swagger/index.html)

The FQDN is constructed based on an so called "dns_indicator" which currently must contain the 
placeholder "NUM", as well as on the "domain_suffix/" from the configuration.

The placeholder NUM will be replaced with the next free number, based on what other instances already 
use the same indicator.

For example, lets say the "domain_suffix" is ".example.com", and the "dns_indicator" is "www-NUM".

The first instance we create, will get the name "www-1.example.com".
The second instance we create will get "www-2.example.com".
If we now delete the first instance, www-1.example.com will be freed.
So the next instance we create with this indicator will get the FQDN "www-1.example.com",
which can help in dynamic environments like auto scaling groups.


Components
----------

API Server
----------

Provides an RESTful API that that will be used to register new systems.
The API stores its data in a MongoDB, Sessions are hosted in an redis instance.

it has the following features:
 - User management
 - API Keys for each user
 - Permissions management
 - completely described using swagger
 - use foreman smart proxy to register instances in DNS, and RedHat IdM/Freeipa
 - optionally register instances in AWS Route 53
 - can talk to multiple foreman smart proxy and AWS Route 53, for example if reverse PTR records are 
 hosted in a different DNS server then A records, or if a different smart proxy should be used for REALM handling.
 Technically, this can be (ab)used to write A and PTR records into multiple DNS servers, if desired.
 REALM is the only part, that only allows one backend, because there can only be one "OneTimePassword" per instance.
 
 The API server is written using Python asyncio, and has been tested with Python 3.6.
 
AWS Lambda function
----------------------

This project includes an lambda function that will listen for EC2 lifecycle events.

If the event is "pending", which is the first state a EC2 instance is in. 
The lambda function will check if a special tag is present on the instance.
If the tag is absent, it will ignore the instance and quit.
If the tag is present, the Lambda function will fetch the instance ip_address, instance_id 
and the value of the tag and create the instance in the API server using a POST request.

If the requests succeeds, the response will contain the designated FQDN for this instance.
The Lambda function will then try to set the "Name" tag on the instance, to match the fqdn from the response.

If the event is "terminated", the lambda function will try to remove the instance-id from the API Server.
This is done, even if the special tag is absent. this is to ensure that instances get cleaned up, even 
if someone or something deleted the special tag.

The lambda function is written in Python, and tested with python 3.6, but > 3.4 should also work.

"catweazle_register.py
----------------------
This is a helper script, that will try to register the instance. 

This script is intended to be called via cloud-init userdata.

The scripts takes exactly one argument, which is the url to the API endpoint.

It will fetch the instance id, using the link local info endpoint which most cloud providers offer 
(http://169.254.169.254/latest/meta-data/instance-id).

The scrips issues a GET request to the API endpoint like this:

https://catweazle.example.com/api/v1/instances/$INSTANCEID

The result will contain the FQDN that has been created for this instance, as well as the OneTimePassword, 
that is needed to enroll the instance to RedHad IdM/Freeipa.

With this information, the script will call all scripts in the folder '/etc/catweazle/register.d/' in order.
Each of these scripts gets called with the FQDN and OTP as first and second argument.

These scripts are intended to change the hostname of the instance, and call "ipa-client-install"

It is up to the user to create these scripts.

The user can also add scripts, that will do other things needed to enroll the system.
For example a script that connects the system to there favorite configuration management, 
or monitoring system. Or send an email, that the system has been successfully created.

The script is written in Python, and tested with python 3.6, but > 3.4 should also work.


MongoDB and Redis
-----------------
MongoDB is used as a persistent store for the API.

Redis is used as a Session store, for user sessions.

Status
------
The application under active development, and in a working status. But it is not battle tested, 
and most likely contains bugs.

The external API´s are fairly stable, and i do not expect a need for breaking changes.

the AWS Route 53, is much less tested then the Foreman Backends. But it is also in a working state.

There are currently no tests at all, but i will work on creating some.

The OpenAPI definition lists all endpoints, which should be more or less self explaining.
But they could need some more detailed description, which i will provide in the future.


Installing
----------
The application can be installed using pip.

```
pip install catweazle
```

Configure the API
-----------------

The API configuration is expected to be placed in /etc/catweazle/catweazle.ini

an example configuration looks like this

If using AWS Route 53, it is expected that the AWS credentials are placed in usual places, like:
- environment variables
- in ~/.aws/
- or and attached IAM role on the instance running the API

```
[main]
# listen host
host = 0.0.0.0
# listen port
port = 9000
# domain suffix, that is attached to the dns_indicator.
# technically this can also stay empty, which would allow for arbitrary domains.
# but this is not a supported setup
domain_suffix = .example.com
# and regex that is matched against the dns_indicator, can be used to limit what indicators can be used.
indicator_regex = ^([a-z0-9-]+)$
# if set to True, we will not talk to Foreman, or Route 53. we will only make changes to MongoDB
# this is usefull for developement, if you do not have these backends available.
# dry_run = false

# where to log
[file:logging]
acc_log = catweazle_rest_access.log
acc_retention = 7
app_log = catweazle_rest.log
app_retention = 7
app_loglevel = DEBUG

# this defines an "aws" backend with the name "default"
[default:aws]
# this backend should create A records
dns_forward_enable = true
# the AWS Zone ID that should be used
dns_forward_zone = ZONE_ID
# this backend should also create PTR records
dns_arpa_enable = true
# The subnets and zone id´s of ARPA zones.
dns_arpa_zones = 192.168.0.0/24:ZONE_1_ID 192.168.1.0/24:ZONE_2_ID

# this defines an "foreman" smart proxy backend with the name "default"
[default:foreman]
# the url to the foreman smart proxy
url = https://fmsmart.example.com:8443
# this is the ssl client cert and key, that is needed to authenticate to the foreman.
# (i am using FreeIPA to issue these certifcated and i am mostly using puppet, this why the path)
ssl_crt = /etc/puppetlabs/puppet/ssl/certs/catweazle.example.com.pem
ssl_key = /etc/puppetlabs/puppet/ssl/private_keys/catweazle.example.com.pem
# this backend should create A records
dns_forward_enable = true
# this backend should create PTR records
dns_arpa_enable = true
# these are the subnets that are managed by this backend.
# you can set this to 0.0.0.0/0 if this backend should be used for all PTR requests
dns_arpa_zones = 192.168.2.0/24 192.168.3.0/24
# this backend should manage RedHat IdM/Freeipa
realm_enable= true
# the name of the REALM used
realm_name = EXAMPLE.COM

# redis connection details
[session:redispool]
host = 192.168.33.12
#pass = dummy

# The main mongo pool
[main:mongopool]
# this also accepts the mongodb URI scheme ('mongodb://host1,host2/?replicaSet=my-replicaset-name')
hosts = 192.168.33.12
# the db to use
db = catweazle
# optionally username and password
#pass =
#user =

# These are the mongodb collections that are used.
# it is technically possible to define more then one "mongopool"
# and place each collection on a different pool.

# this is something that is common for API´s I created, but most likely not needed for this project.
# simply keep the following as a default.
[instances:mongocoll]
coll = instances
pool = main

[permissions:mongocoll]
coll = permissions
pool = main

[users:mongocoll]
coll = users
pool = main

[users_credentials:mongocoll]
coll = users_credentials
pool = main

```

Before you start the API, you have to call two commands, to initialize the MongoDB database, 
and create a default user:


```
schlitzer@schlitzer-XPS-13-9360:~$ catweazle indices
schlitzer@schlitzer-XPS-13-9360:~$ catweazle create_admin
creating admin user...
done...
```

This will create the required indices, as well as the default admin user:

```
user: admin 
pass: password
```

It is strongly advised that you add create your own user, and delete the admin user, 
or at least change the admin password.

You can now start the API server like this:
```
schlitzer@schlitzer-XPS-13-9360:~$ catweazle indices run
======== Running on http://0.0.0.0:9000 ========
(Press CTRL+C to quit)

```

You should now be able to connect to the swagger API, and use the service:

http://localhost:9000/static/swagger/index.html


Configuring AWS Lambda
----------------------
To make the lambda function work, you have to configure AWS CloudWatch to trigger the Catweazle Lambda function
on EC2 lifecycle events of type 'pending' and 'terminated'. Other event types will be ignored by the Lambda function.

Configuring AWS CloudWatch and the creation of the lambda function is out of scope, 
i might add the information later on how to do this with something like terraform.

The Lambda function itself is configured using the following environment variables:

- CatWeazleLogLevel: Optional, defaults to INFO
- CatWeazleEndpoint: the url to the API, example: 'http://catweazle.example.com'
- CatWeazleIndicatorTag:: the tag that is used for the dns_indicator, example "DNS_indicator"
- CatWeazleRoleArn: the role arn that should be used by the lambda functions to fetch and set tags on the 
instance, example: 'arn:aws:iam::{0}:ROLE/NAME', the '{0}' is a placeholder, which will be 
replaced with the account_id of the AWS EC2 event. This allows that you can have the Lambda function running 
in a central account, and send events from other accounts. The Lambda function will then assume the role
in the account the AWS EC2 event originates from.
- CatWeazleSecret: the CatWeazle API Secret
- CatWeazleSecretID: the CatWeazle API SecretID
- CAtWeazleRoleSessionName: Optional: AWS RoleSession name that is going to be used, defaults to catweazle_session


the tricky part is now the create a non admin user, permissions, and API secrets, that can be used by 
the lambda function.

For this, we are going to use curl:

```
# log in as user 'admin' with password 'password', saving the session cookie to disk
curl -c cookie.store -X POST "http://localhost:9000/api/v1/authenticate" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"user\":\"admin\",\"password\":\"password\"}}"
{"data": {"id": "af38500b-57b2-43b0-886e-290d6751fc21"}}

# retrieving info about current user, to check if it worked
curl -L -b cookie.store -X GET "http://localhost:9000/api/v1/users/_self" -H  "accept: */*"
{"data": {"admin": true, "backend": "internal", "backend_ref": "default_admin", "email": "default_admin@internal", "name": "Default Admin User", "id": "admin"}}

# creating new non admin user 'aws_lambda:
curl -L -b cookie.store -X POST "http://localhost:9000/api/v1/users/aws_lambda" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"admin\":false,\"email\":\"catweazle_lambda_at_example.com\",\"name\":\"Technical Catweazle AWS Lambda User\",\"password\":\"SuperSecurePassword\"}}"
{"data": {"admin": false, "email": "catweazle_lambda_at_example.com", "name": "Technical Catweazle AWS Lambda User", "backend": "internal", "backend_ref": "aws_lambda", "id": "aws_lambda"}}

# create permission with the name 'aws_lambda' for user 'aws_lambda', with INSTANCE:DELETE and INSTANCE:CREATE permissions
curl -L -b cookie.store -X POST "http://localhost:9000/api/v1/permissions/aws_lambda" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"permissions\":[\"INSTANCE:DELETE\",\"INSTANCE:POST\"],\"users\":[\"aws_lambda\"]}}"
{"data": {"permissions": ["INSTANCE:DELETE", "INSTANCE:POST"], "users": ["aws_lambda"], "id": "aws_lambda"}}

# log in as user 'aws_lambda'
curl -c cookie.store -X POST "http://localhost:9000/api/v1/authenticate" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"user\":\"aws_lambda\",\"password\":\"SuperSecurePassword\"}}"
{"data": {"id": "5c03e5d7-3d6b-45a0-9b1d-137c127dd384"}}

# create API credentials for the user 'aws_lambda'
# you have to remember this, you will not be able to retrieve the secred again!
curl -L -b cookie.store -X POST "http://localhost:9000/api/v1/users/_self/credentials" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"description\":\"AWS Lambda API Credentials\"}}"
{"data": {"id": "c7e5ac60-d6aa-422c-a588-4e4844d36b3e", "created": "2019-11-15 19:43:40.678784", "description": "AWS Lambda API Credentials", "secret": "fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj"}}

# out secret is: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj
# out secret id is: c7e5ac60-d6aa-422c-a588-4e4844d36b3e
# export the credentials:
export X_ID=c7e5ac60-d6aa-422c-a588-4e4844d36b3e
export X_SECRET=fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj

# test the api credentials for user 'aws_lambda':

# lets try to create some dummy instances (set dry_run to true in the config)
# we create instance i-0815, i-0816, i-0817, i-0818,
# then we delete i-0816, then we create i-0819
# lets see what happens:
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X POST "http://localhost:9000/api/v1/instances/i-0815" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"dns_indicator\":\"www-NUM\",\"ip_address\":\"192.168.0.10\"}}"
{"data": {"dns_indicator": "www-NUM", "ip_address": "192.168.0.10", "id": "i-0815", "fqdn": "www-1.example.com"}}schlitzer@schlitzer-XPS-13-9360:~$ 
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X POST "http://localhost:9000/api/v1/instances/i-0816" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"dns_indicator\":\"www-NUM\",\"ip_address\":\"192.168.0.11\"}}"
{"data": {"dns_indicator": "www-NUM", "ip_address": "192.168.0.11", "id": "i-0816", "fqdn": "www-2.example.com"}}schlitzer@schlitzer-XPS-13-9360:~$ 
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X POST "http://localhost:9000/api/v1/instances/i-0817" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"dns_indicator\":\"www-NUM\",\"ip_address\":\"192.168.0.12\"}}"
{"data": {"dns_indicator": "www-NUM", "ip_address": "192.168.0.12", "id": "i-0817", "fqdn": "www-3.example.com"}}schlitzer@schlitzer-XPS-13-9360:~$ 
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X POST "http://localhost:9000/api/v1/instances/i-0818" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"dns_indicator\":\"www-NUM\",\"ip_address\":\"192.168.0.13\"}}"
{"data": {"dns_indicator": "www-NUM", "ip_address": "192.168.0.13", "id": "i-0818", "fqdn": "www-4.example.com"}}schlitzer@schlitzer-XPS-13-9360:~$ 
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X DELETE "http://localhost:9000/api/v1/instances/i-0816" -H  "accept: */*"
nullschlitzer@schlitzer-XPS-13-9360:~$ 
schlitzer@schlitzer-XPS-13-9360:~$ curl -H 'X-ID: c7e5ac60-d6aa-422c-a588-4e4844d36b3e' -H 'X-SECRET: fok-VShjsdDoiwQ1ePG3MAUtxUODOd3g.3qYPNm--qXMbyL3ZYyGj-Y7tu8gI8iYnH.VIaBUMka-8PJ5sSwZI0AEouLmcsbSAIGNx.zHg5VPGQgfaK5.L-iF6uoUVAcj' -X POST "http://localhost:9000/api/v1/instances/i-0819" -H  "accept: */*" -H  "Content-Type: application/json" -d "{\"data\":{\"dns_indicator\":\"www-NUM\",\"ip_address\":\"192.168.0.14\"}}"
{"data": {"dns_indicator": "www-NUM", "ip_address": "192.168.0.14", "id": "i-0819", "fqdn": "www-2.example.com"}}schlitzer@schlitzer-XPS-13-9360:~$ 

# this is what happens:
# i-0815 gets name www-1.example.com
# i-0816 gets name www-2.example.com
# i-0817 gets name www-3.example.com
# i-0818 gets name www-4.example.com
# i-0816 is deleted (which will free fqdn www-2.example.com)
# i-0819 gets name www-2.example.com

```

EC2 Instance Registration
-------------------------
Requirements:

you need to either install the catweazle package using "userdata", 
including you custom registration scripts, or you need to create an 
AMI that already contains the required data.

I would suggest to bake an AMI that contains the required data.

An example registration script could look like this:
/etc/catweazle/register.d/00_register.sh

```
#!/usr/bin/bash

FQDN=$1
OTP=$2

# setting the hostname
echo "${FQDN}" > /etc/hostname
hostname "${FQDN}"

# install and configure ipa-client
yum install -y ipa-client
ipa-client-install -w "${FQDN}" --mkhomedir --force-join --unattended

```

You then need to create a ec2 instance with the tag name you choose, in our example 
"DNS_indicator", and the example value "www-NUM".

you also need to add the required userdata, that will call the 
catweazle_register script, example:


```
#!/usr/bin/bash

catweazle_register --endpoint https://catweazle.example.com

```

That's it.

If you have questions or suggestions feel free to open an issue.

Author
------

Stephan Schultchen <stephan.schultchen@gmail.com>

License
-------

Unless stated otherwise on-file CatWeazle uses the MIT license,
check LICENSE file.

Contributing
------------

If you'd like to contribute, fork the project, make a patch and send a pull
request.