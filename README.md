Introduction
************


Installing
----------

pip install catweazle

the configuration is expected to be placed in /etc/catweazle/config.ini

an example configuration looks like this

```
[main]
host = 0.0.0.0
port = 9000
domain_suffix = .us-east1.aws.example.com

[file:logging]
acc_log = catweazle_rest_access.log
acc_retention = 7
app_log = catweazle_rest.log
app_retention = 7
app_loglevel = DEBUG

[aws]
enable = true
arpa_zone_id = ZNTVAHUPY596W
zone_id = Z1YUAMV5C5Q71Z

[foreman]
url = https://fmsmart1-example.com:8443
ssl_crt = /etc/puppetlabs/puppet/ssl/certs/catweazle.example.com.pem
ssl_key = /etc/puppetlabs/puppet/ssl/private_keys/catweazle.example.com.pem
dns_enable = true
realm_enable = true
realm = EXAMPLE.COM

[session:redispool]
host = 192.168.33.12
#pass = dummy

[main:mongopool]
hosts = 192.168.33.12
db = catweazle
#pass =
#user =

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


Author
------

Stephan Schultchen <stephan.schultchen@gmail.com>

License
-------

Unless stated otherwise on-file foreman-dlm-updater uses the MIT license,
check LICENSE file.

Contributing
------------

If you'd like to contribute, fork the project, make a patch and send a pull
request.