#!/usr/bin/env python3

"""
Copyright 2024 StorPool Storage

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import glob
import logging
import subprocess
import sys
import time

"""
Attach source and destination volumes from an iSCSI array and StorPool
and copies the source volume content to the destination volume byte by byte.
"""

logging.basicConfig(level=logging.DEBUG)

def attach_iscsi(portal, iqn, lun=0):
    logging.debug("Attach iscsi %s %s %d", portal, iqn, lun)
    subprocess.run([
        'sudo',
        '/usr/sbin/iscsiadm',
        '--mode', 'discoverydb',
        '--type', 'sendtargets',
        '--portal', portal,
        '--discover',
        ], check=True)
    logging.debug("iSCSI discover portal %s successful", portal)
    subprocess.run([
        'sudo',
        '/usr/sbin/iscsiadm',
        '--mode', 'node',
        '--portal', portal,
        '--targetname', iqn,
        '--login',
        ], check=True)
    logging.debug("iSCSI login %s %s successful", portal, iqn)

    # Give some time to create the symlinks
    # FIXME: This is prone to race condition errors and needs improvement
    time.sleep(1)

    src_path_list=glob.glob(f"/dev/disk/by-path/*{iqn}-lun-{lun}")
    logging.debug("Found block devices: %s", src_path_list)
    if len(src_path_list) != 1:
        raise RuntimeError("Can't find the block device for " + iqn)
    return src_path_list[0]


def attach_storpool(volume_name):
    logging.debug("Attach StorPool volume %s", volume_name)
    subprocess.run([
        "storpool",
        "attach",
        "volume",
        volume_name,
        "here",
        ], check=True)
    logging.debug("StorPool attach successful")
    return  f"/dev/storpool/{volume_name}"


def copy(src, dest):
    logging.debug("Copy volume %s to %s", src, dest)
    start_time = time.time()
    subprocess.run([
        # "echo",
        "dd",
        "if=" + src,
        "of=" + dest,
        "bs=1M",
        "iflag=direct",
        "oflag=direct",
        ], check=True)
    finish_time = time.time()
    logging.info("Volume %s copied successful. Duration: %d seconds.", 
            src, finish_time - start_time)


def detach_iscsi(iqn):
    logging.debug("Detach iscsi %s", iqn)
    subprocess.run([
        'sudo',
        '/usr/sbin/iscsiadm',
        '--mode', 'node',
        '--targetname', iqn,
        '--logout',
        ], check=True)
    logging.debug("iSCSI logout %s successful", iqn)


def detach_storpool(volume_name):
    logging.debug("Detach StorPool volume %s", volume_name)
    subprocess.run([
        "storpool", "detach", "volume", volume_name, "here"
        ], check=True)
    logging.debug("StorPool detach successful")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('portal', help="IP address if the iSCSI portal")
    parser.add_argument('src', help="IQN of the source volume")
    parser.add_argument('dest', help="Name of the destination StorPool volume")

    args = parser.parse_args()
    logging.debug("Copy images called with arguments: %s", vars(args))

    src_path = attach_iscsi(args.portal, args.src)
    dst_path = attach_storpool(args.dest)
    copy(src_path, dst_path)
    detach_iscsi(args.src)
    detach_storpool(args.dest)


if __name__ == "__main__":
    main()
