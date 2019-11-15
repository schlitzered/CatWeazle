#!/usr/bin/env python3

import argparse
import logging
import os
import requests
import subprocess
import sys
import stat


def main():
    parser = argparse.ArgumentParser(
        description="Register System based on information provided by CatWeazle. "
                    "Scripts in /etc/catweazle/register.d will be executed in order. "
                    "Scripts will be called with the fqdn as first, and the otp as second argument."
    )

    parser.add_argument("--endpoint", dest="endpoint", action="store", required=True,
                        help="CatWeazle endpoint URL")

    parsed_args = parser.parse_args()

    register = Register(
        endpoint=parsed_args.endpoint,
    )
    register.run()


class Register:
    def __init__(self, endpoint):
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
    def endpoint(self):
        return self._endpoint

    def _run_cmd(self, args):
        self.log.info("running command: {0}".format(args))
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in p.stdout:
            self.log.info(line.rstrip())
        p.stdout.close()
        self.log.info("finished running command: {0}".format(args))
        return p.wait()

    def get_cw_data(self):
        self.log.info("Getting Catweazle Data")
        data = requests.get("{0}/api/v1/instances/{1}".format(self.endpoint, self.instance_id)).json()
        self._fqdn = data['data']['fqdn']
        self._otp = data['data']['ipa_otp']
        self.log.info("Getting Catweazle Data, done")

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
        self.log.info("instance-id is {0}".format(self.instance_id))
        self.get_cw_data()
        self.log.info("designated FQDN is {0}".format(self.fqdn))
        self.run_scripts()
        self.log.info("Starting registration process, done")
