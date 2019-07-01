#!/usr/bin/env python
#

from __future__ import print_function

import subprocess
import xml.etree.ElementTree as ET
from os import environ
from sys import exit,stdout,stderr
import traceback

LCM_STATE = [
    'LCM_INIT','PROLOG','BOOT','RUNNING','MIGRATE','SAVE_STOP','SAVE_SUSPEND',
    'SAVE_MIGRATE','PROLOG_MIGRATE','PROLOG_RESUME','EPILOG_STOP','EPILOG',
    'SHUTDOWN','//CANCEL','//FAILURE','CLEANUP_RESUBMIT','UNKNOWN','HOTPLUG',
    'SHUTDOWN_POWEROFF','BOOT_UNKNOWN','BOOT_POWEROFF','BOOT_SUSPENDED',
    'BOOT_STOPPED','CLEANUP_DELETE','HOTPLUG_SNAPSHOT','HOTPLUG_NIC',
    'HOTPLUG_SAVEAS','HOTPLUG_SAVEAS_POWEROFF','HOTPLUG_SAVEAS_SUSPENDED',
    'SHUTDOWN_UNDEPLOY','EPILOG_UNDEPLOY','PROLOG_UNDEPLOY','BOOT_UNDEPLOY',
    'HOTPLUG_PROLOG_POWEROFF','HOTPLUG_EPILOG_POWEROFF','BOOT_MIGRATE',
    'BOOT_FAILURE','BOOT_MIGRATE_FAILURE','PROLOG_MIGRATE_FAILURE',
    'PROLOG_FAILURE','EPILOG_FAILURE','EPILOG_STOP_FAILURE',
    'EPILOG_UNDEPLOY_FAILURE','PROLOG_MIGRATE_POWEROFF',
    'PROLOG_MIGRATE_POWEROFF_FAILURE','PROLOG_MIGRATE_SUSPEND',
    'PROLOG_MIGRATE_SUSPEND_FAILURE','BOOT_UNDEPLOY_FAILURE',
    'BOOT_STOPPED_FAILURE','PROLOG_RESUME_FAILURE','PROLOG_UNDEPLOY_FAILURE',
    'DISK_SNAPSHOT_POWEROFF','DISK_SNAPSHOT_REVERT_POWEROFF',
    'DISK_SNAPSHOT_DELETE_POWEROFF','DISK_SNAPSHOT_SUSPENDED',
    'DISK_SNAPSHOT_REVERT_SUSPENDED','DISK_SNAPSHOT_DELETE_SUSPENDED',
    'DISK_SNAPSHOT','//DISK_SNAPSHOT_REVERT','DISK_SNAPSHOT_DELETE',
    'PROLOG_MIGRATE_UNKNOWN','PROLOG_MIGRATE_UNKNOWN_FAILURE','DISK_RESIZE',
    'DISK_RESIZE_POWEROFF','DISK_RESIZE_UNDEPLOYED']

STATE = [
    'INIT','PENDING','HOLD','ACTIVE','STOPPED','SUSPENDED','DONE','//FAILED',
    'POWEROFF','UNDEPLOYED','CLONING','CLONING_FAILURE']

def run_cmd(cmd, addenv={}):
    try:
        env = environ.copy()
        env.update(addenv)
        out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        msg = "run_cmd({}) exit status {}, output:'{}'"\
                .format(' '.join(cmd), e.returncode, e.output)
        print(msg)
        raise e
    return out

def oneClusterData():
    cmd = ['onecluster', 'list', '--xml']
    out = run_cmd(cmd)
    xml = ET.fromstring(out)
    cData = {}
    for cEntry in xml.findall('CLUSTER'):
        cid = int(cEntry.find('ID').text)
        cData[cid] = {'ID':cid}
        cData[cid]['NAME'] = cEntry.find('NAME').text
        for cElement in ['HOSTS','DATASTORES']:
            cData[cid][cElement] = []
            for element in cEntry.findall(cElement):
                for el in element.findall('ID'):
                    did = int(el.text)
                    cData[cid][cElement].append(did)
        for txt in ['SP_REMOTE', 'SP_LOCATION']:
            try:
                text = cEntry.find("TEMPLATE/{}".format(txt)).text
                cData[cid][txt] = text
            except Exception as e:
                pass
        cData[cid]['ENV'] = {}
        for txt in ['SP_API_HTTP_HOST', 'SP_API_HTTP_PORT',
                    'SP_AUTH_TOKEN']:
            try:
                text = cEntry.find("TEMPLATE/{}".format(txt)).text
                cData[cid]['ENV'][txt] = text
            except Exception as e:
                pass
    return cData

def oneDatastoreData():
    cmd = ['onedatastore', 'list', '--xml']
    out = run_cmd(cmd)
    xml = ET.fromstring(out)
    cData = {}
    for cEntry in xml.findall('DATASTORE'):
        did = int(cEntry.find('ID').text)
        cData[did] = {'ID':did}
        cData[did]['NAME'] = cEntry.find('NAME').text
        cData[did]['TYPE'] = int(cEntry.find('TYPE').text)
        cData[did]['CLUSTERS'] = []
        for entry in cEntry.findall('CLUSTERS/ID'):
            cid = int(entry.text)
            cData[did]['CLUSTERS'].append(cid)
        for txt in ['SP_REMOTE','SP_LOCATION']:
            try:
                text = cEntry.find("TEMPLATE/{}".format(txt)).text
                cData[did][txt] = text
            except Exception as e:
                pass
        cData[did]['ENV'] = {}
        for txt in ['SP_API_HTTP_HOST', 'SP_API_HTTP_PORT',
                    'SP_AUTH_TOKEN']:
            try:
                text = cEntry.find("TEMPLATE/{}".format(txt)).text
                cData[did]['ENV'][txt] = text
            except Exception as e:
                pass
    return cData

if __name__ == '__main__':
    try:
        dsData = oneDatastoreData()
        clData = oneClusterData()

        cmd = ['onevm', 'list', '--xml', '--extended']
        out = run_cmd(cmd)
        vmpool = ET.fromstring(out)
        for vm in vmpool.findall('VM'):
            vm_name = vm.find('NAME').text
            vm_id = int(vm.find('ID').text)
            vm_disk_ds = -1
            for disk in vm.findall('TEMPLATE/DISK'):
                vm_disk_ds = int(disk.find('DATASTORE_ID').text)
                break
            cl_id = dsData[vm_disk_ds]['CLUSTERS'][0]
            cl_name = clData[cl_id]['NAME']
            print("{},{},{},{}".format(
                vm_id, vm_name, cl_id, cl_name))

    except Exception as e:
        stdout.flush()
        print(traceback.print_exc())
        exit(1)

