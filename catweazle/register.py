#!/usr/bin/env python3

import argparse
import logging
import os
import subprocess
import sys
import stat
import time

import requests


def main():
    parser = argparse.ArgumentParser(
        description="Register System based on information provided by CatWeazle. "
                    "Scripts in /etc/catweazle/register.d will be executed in order. "
                    "Scripts will be called with the fqdn as first, and the otp as second argument."
    )

    parser.add_argument("--endpoint", dest="endpoint", action="store", required=True,
                        help="CatWeazle endpoint URL")

    parser.add_argument("--retry", dest="retry", action="store", required=False,
                        default=10, type=int, help="Number of retries for fetching CatWeazle data")

    parser.add_argument("--pre_sleep", dest="pre_sleep", action="store", required=False,
                        default=30, type=int,
                        help="wait specified number of seconds, before doing anything. this might be needed"
                             "because of replication delay between IdM servers.")

    parsed_args = parser.parse_args()

    register = Register(
        endpoint=parsed_args.endpoint,
        retry=parsed_args.retry,
        pre_delay=parsed_args.pre_delay,
    )
    register.run()


class Register:
    def __init__(self, endpoint, retry, pre_delay):
        self.log = logging.getLogger('application')
        self.log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        self._endpoint = endpoint
        self._fqdn = None
        self._instance_id = None
        self._otp = None
        self._pre_delay = pre_delay
        self._retry = retry

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def fqdn(self):
        return self._fqdn

    @property
    def instance_id(self):
        if not self._instance_id:
            self._instance_id = requests.get('http://169.254.169.254/latest/meta-data/instance-id').text
        return self._instance_id

    @property
    def otp(self):
        return self._otp

    @property
    def pre_delay(self):
        return self._pre_delay

    @property
    def retry(self):
        return self._retry

    def _run_cmd(self, args):
        self.log.info("running command: {0}".format(args))
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in p.stdout:
            self.log.info(line.rstrip())
        p.stdout.close()
        self.log.info("finished running command: {0}".format(args))
        return p.wait()

    def get_cw_data(self):
        self.log.info("Getting CatWeazle Data")
        for _ in range(self.retry):
            self.log.info("Trying to fetch CatWeazle data")
            data = requests.get("{0}/api/v1/instances/{1}".format(self.endpoint, self.instance_id))
            status_code = data.status_code
            data = data.json()
            if status_code is not 200:
                self.log.warning(
                    "Could not fetch instance data, http status was {0}, sleeping for 5 seconds".format(
                        status_code
                    )
                )
            elif 'ipa_otp' in data['data']:
                self.log.info("Success fetching CatWeazle data")
                self._fqdn = data['data']['fqdn']
                self._otp = data['data']['ipa_otp']
                self.log.info("Getting CatWeazle Data, done")
                return
            else:
                self.log.warning(
                    "instance data incomplete, otp token missing, sleeping for 5 seconds")
            time.sleep(5)
        self.log.fatal("instance data could not be fetched, quitting")
        sys.exit(1)

    def get_scripts(self):
        path = '/etc/catweazle/register.d/'
        files = list()
        candidates = os.listdir(path)
        candidates.sort()
        for _file in candidates:
            _file = os.path.join(path, _file)
            self.log.debug("found the file: {0}".format(_file))
            if not os.path.isfile(_file):
                self.log.warning("{0} is not a file".format(_file))
                continue
            if not os.stat(_file).st_uid == 0:
                self.log.warning("file not owned by root")
                continue
            if os.stat(_file).st_mode & stat.S_IXUSR != 64:
                self.log.warning("file not executable by root")
                continue
            if os.stat(_file).st_mode & stat.S_IWOTH == 2:
                self.log.warning("file group writeable")
                continue
            if os.stat(_file).st_mode & stat.S_IWGRP == 16:
                self.log.warning("file world writeable")
                continue
            files.append(_file)
        return files

    def run_scripts(self):
        self.log.info("running registration scripts")
        files = self.get_scripts()
        for _file in files:
            self.log.info("running: {0}".format(_file))
            if self._run_cmd([_file, self.fqdn, self.otp]) != 0:
                self.log.fatal("script failed, stopping!")
                sys.exit(1)
            self.log.info("running: {0} done".format(_file))
        self.log.info("running registration scripts, done")

    def run(self):
        self.log.info("Starting registration process")
        self.log.info("sleeping for {0} seconds".format(self.pre_delay))
        time.sleep(self.pre_delay)
        self.log.info("sleeping for {0} seconds, done".format(self.pre_delay))
        self.log.info("instance-id is {0}".format(self.instance_id))
        self.get_cw_data()
        self.log.info("designated FQDN is {0}".format(self.fqdn))
        self.run_scripts()
        self.log.info("Starting registration process, done")
