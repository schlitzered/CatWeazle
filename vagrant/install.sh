#!/usr/bin/env bash

yum install -y epel-release

cp /home/vagrant/scripts/mongodb.repo /etc/yum.repos.d/

yum install -y dkms wget vim telnet puppet mongodb-org redis

cp /home/vagrant/scripts/mongod.conf /etc/

#wget http://download.virtualbox.org/virtualbox/4.3.30/VBoxGuestAdditions_4.3.30.iso
#mount -o loop VBoxGuestAdditions_4.3.30.iso /mnt
#/mnt/VBoxLinuxAdditions.run

#yum update -y

systemctl start redis
systemctl enable redis
systemctl start mongod
systemctl enable mongod
