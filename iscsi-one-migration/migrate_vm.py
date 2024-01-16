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
import ipaddress
import json
import logging
import shlex
import subprocess
import tempfile
import time


COPY_IMG_COMMAND = "/tmp/copy_image.py"

def create_images(args):
    logging.debug("Creating images for VM %s", args.name)

    images = []

    for i in range(len(args.disk_size)):
        disk_size = args.disk_size[i]
        image_name = f"{args.name}-disk-{i}"

        cmd = [
                'oneimage',
                'create',
                '--persistent',
                '--name', image_name,
                '--datastore', str(args.datastore),
                '--type', 'OS' if i == 0 else 'DATABLOCK',
                '--size', str(disk_size * 1024),   # size is MiB, input is in GiB
        ]
        logging.debug("Create image [%d]: %s", i, cmd)
        res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        logging.debug("oneimage create result: %s", res)
        if res.returncode != 0:
            logging.error("Error creating image: %s", res.stderr)
            raise RuntimeError
        out = res.stdout
        if not out.startswith("ID:"):
            logging.error("Error creating image. Unknown output: %s", out)
            raise RuntimeError
        img_id = int(out.split(":")[1])
        logging.info("Image created ID: %d", img_id)

        images.append(img_id)

    return images


def chown_img(images, args):

    logging.debug("Changing owner of images %s", images)
    img_list =  ",".join([str(x) for x in images])
    logging.debug("Changing owner of images %s to %d", img_list, args.user_id)
    cmd = [
            'oneimage',
            'chown',
            img_list,
            str(args.user_id),
            str(args.group_id),
    ]

    res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    logging.debug("oneimage chown result: %s", res)
    if res.returncode != 0:
        logging.error("Error changing owner of images: %s", res.stderr)
        raise RuntimeError

    logging.info("Images %s owner changed to %d", img_list, args.user_id)


def create_vm(images, args):

    logging.debug("Creating VM %s", args.name)

    logging.debug("Reading tempalte file %s", args.template.name)
    vm_template = args.template.read()
    vm_params = vars(args)

    vm_params["ip_def"] = ""
    if args.ip is not None:
        vm_params["ip_def"] += f'IP = "{args.ip}",\n'

    disk_config = ""
    for img_id in images:
        disk_config += f'DISK = [ IMAGE_ID = "{img_id}" ]\n'
    vm_params["disk_config"] = disk_config

    logging.debug("vm_params=%s", vm_params)
    vm_config = vm_template.format(**vm_params)

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
            suffix=".tmpl", delete=False) as template:
        logging.debug("VM Template (%s): %s", template.name, vm_config)
        template.write(vm_config)
        template.close()

        cmd = [
                'onevm',
                'create',
                template.name,
        ]

        res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        logging.debug("onevm create result: %s", res)
        if res.returncode != 0:
            logging.error("Error creating VM: %s", res.stderr)
            raise RuntimeError
        out = res.stdout
        if not out.startswith("ID:"):
            logging.error("Error creating VM. Unknown output: %s", out)
        vmid = int(out.split(":")[1])

    logging.info("VM ID %d created", vmid)
    return vmid


def chown_vm(vmid, args):

    logging.debug("Changing VM %d owner to %d", vmid, args.user_id)
    cmd = [
            'onevm',
            'chown',
            str(vmid),
            str(args.user_id),
            str(args.group_id),
    ]

    res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
    logging.debug("onevm chown result: %s", res)
    if res.returncode != 0:
        logging.error("Error changing owner of VM: %s", res.stderr)
        raise RuntimeError

    logging.info("VM ID %d owner changed to %d", vmid, args.user_id)



def wait_vm_ready(vmid, timeout=60, repeat=3):
    logging.debug("Waiting VM %d to get ready, timeout=%d sec", vmid, timeout)
    cmd = [ 'onevm', 'show', '--json', str(vmid) ]
    started = time.time()
    while time.time() < started + timeout:
        time.sleep(repeat)
        res = subprocess.run(cmd, capture_output=True, encoding='utf-8', check=True)
        try:
            out = json.loads(res.stdout)
            vm_state = int(out["VM"]["STATE"])
            vm_lcm_state = int(out["VM"]["LCM_STATE"])
            logging.debug("VM %d state is %d, %d", vmid, vm_state, vm_lcm_state)
            if (
                    (vm_state == 8) # POWEROFF
                    or (vm_state == 3 and vm_lcm_state == 3)  # ACTIVE, RUNNING
                    ) :
                logging.debug("VM %d ready", vmid)
                return
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logging.debug("Unknown error: %s", e.msg)
            continue
    
    logging.error("Timeout waiting VM %d", vmid)
    raise TimeoutError
                

def copy_images(images, args):
    logging.debug("Copy images on host: %s, images: %s", args.host, images)

    for i in range(len(args.disk_source)):
        src_image = args.disk_source[i]
        dst_volume = f"{args.one_prefix}-img-{images[i]}"
        cmd = [
            #'echo',
            'ssh', args.host,
            shlex.quote(COPY_IMG_COMMAND),
            shlex.quote(args.portal),
            shlex.quote(src_image),
            shlex.quote(dst_volume)
        ]
        start_time = time.time()
        logging.debug("Sending command for transfer: %s", cmd)
        res = subprocess.run(cmd, capture_output=True, encoding='utf-8')
        logging.debug("transfer result: %s", res)
        if res.returncode != 0:
            logging.error("Error transfering image %s|%s: %s", 
                    src_image, dst_volume, res.stderr)
            raise RuntimeError
        transfer_time = time.time() - start_time
        logging.info("Image transfer successful [%.1f sec]: %s -> %s",
                transfer_time, src_image, dst_volume)

    logging.info("All images for VM %s are transferred", args.name)


def poweroff_vm(vmid):
    logging.debug("PowerOff HARD VM %d", vmid)
    cmd = [
            'onevm',
            'poweroff', '--hard',
            str(vmid),
    ]
    res = subprocess.run(cmd, check=True)
    logging.info("VM %d powered OFF", vmid)


def start_vm(vmid):
    logging.debug("Starting VM %d", vmid)
    cmd = [
            'onevm',
            'resume',
            str(vmid),
    ]
    res = subprocess.run(cmd, check=True)
    logging.info("VM %d Started, check status", vmid)


def parse_args():

    parser = argparse.ArgumentParser(
            description=''
            )

    parser.add_argument('--debug', '-D', action="store_true", help="Enable debug output")
    parser.add_argument('--one-prefix', default='one',
            help="prefix used by OpenNebula addon for StorPool")
    parser.add_argument('--name', required=True, help="Name of the created VM")
    parser.add_argument('--template', required=True, type=argparse.FileType(),
            help="filename of VM configuration tempalte. Shall contain static "
            "configuration similar to the output of `onevm show`")
    parser.add_argument('--user-id', required=True, type=int, 
            help="OpenNebula user ID, owner of the VM");
    parser.add_argument('--group-id', required=True, type=int, 
            help="OpenNebula group ID, group of the VM");
    parser.add_argument('--cpu', required=True, type=int,
            help="Number of vCPUs");
    parser.add_argument('--pcpu', required=True, type=float,
            help="Number of physical CPUs");
    parser.add_argument('--ram', required=True, type=int,
            help="RAM in MiB");
    parser.add_argument('--network', required=True, type=int,
            help="Network ID, as reported by onevnet list");
    parser.add_argument('--ip', required=False, type=ipaddress.ip_address,
            help="Sets the IP address if provided. OpenNebula will assing the next "
            "available address from the network range, if not provided");
    parser.add_argument('--datastore', type=int, default=1,
            help="Datastore ID in OpenNebula to store the disk images")
    parser.add_argument('--disk-size', required=True, type=int, action="append",
            help="Size of the disk in GiB. Shall be specified one per each disk. "
            "The number and order shall match the --disk-source items.");
    parser.add_argument('--disk-source', required=True, action="append",
            help="Source image IQN and LUN. Shall be specified one per each disk. "
            "The number and the order shall match the --disk-size items. "
            "Example: 'iqn.example.com:volume1-lun-0'");
    parser.add_argument('--host', required=True,
            help="Transfer host. This is the host that will perform the actual "
            "transfer of the image content.")
    parser.add_argument('--portal', required=True,
            help="IP addrerss of the iSCSI portal for the source volumes")

    
    args = parser.parse_args()
    if len(args.disk_size) != len (args.disk_source):
        parser.error("--disk-size doesn't match the number of --disk-source arguments")

    for disk_size in args.disk_size:
        if disk_size < 1:
            parser.error("Bad disk size: " + str(disk_size))

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


    return args


def main():

    args = parse_args()

    images = create_images(args)
    chown_img(images, args)
    vmid = create_vm(images, args)
    chown_vm(vmid, args)
    wait_vm_ready(vmid)
    poweroff_vm(vmid)
    copy_images(images, args)
    wait_vm_ready(vmid)
    start_vm(vmid)


if __name__ == "__main__":
    main()

