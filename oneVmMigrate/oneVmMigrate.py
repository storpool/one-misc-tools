#!/usr/bin/env python
#

from __future__ import print_function

import subprocess
import xml.etree.ElementTree as ET
from json import dumps,loads
from os import environ
from sys import exit,stdout,stderr
import traceback
import pprint
import time
import syslog

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
    'PROLOG_MIGRATE_UNKNOWN','PROLOG_MIGRATE_UNKNOWN_FAILURE',
    'DISK_RESIZE','DISK_RESIZE_POWEROFF','DISK_RESIZE_UNDEPLOYED',
    'HOTPLUG_NIC_POWEROFF','HOTPLUG_RESIZE','HOTPLUG_SAVEAS_UNDEPLOYED',
    'HOTPLUG_SAVEAS_STOPPED']

STATE = [
    'INIT','PENDING','HOLD','ACTIVE','STOPPED','SUSPENDED','DONE','//FAILED',
    'POWEROFF','UNDEPLOYED','CLONING','CLONING_FAILURE']

def log(args, txt, level=0):
    if txt == '':
        return
    syslog.syslog(pprint.pformat(txt, indent=0, width=1000))
    if level < 1 or args.verbose:
        print('[{}] {}'.format(time.asctime(),txt))
        stdout.flush()

def run_cmd(args, cmd, addenv={}):
    try:
        env = environ.copy()
        env.update(addenv)
        out = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        msg = "run_cmd({}) exit status {}, output:'{}'"\
                .format(' '.join(cmd), e.returncode, e.output)
        log(args, msg, 2)
        raise e
    return out

def oneVmXml(args):
    cmd = ['onevm', 'show', '--xml', str(args.vmid)]
    out = run_cmd(args, cmd)
    return ET.fromstring(out)

def oneVmWaitstate(args, state, lcm_state, tout=900):
    timeout = time.time() + tout
    while True:
        xml = oneVmXml(args)
        current_lcm_state = int(xml.find('LCM_STATE').text)
        if LCM_STATE[current_lcm_state] is not None:
            current_lcm_state = LCM_STATE[current_lcm_state]
        current_state = int(xml.find('STATE').text)
        if STATE[current_state] is not None:
            current_state = STATE[current_state] 
        msg = "oneVmWaitstate({}) current {}:{}, waiting for {}:{}"\
                .format(args.vmid, current_state, current_lcm_state,
                        state, lcm_state)
        log(args, msg)
        if current_lcm_state == lcm_state and current_state == state:
            return
        if time.time() > timeout:
            msg = "Timeout waiting for {}:{}".format(state, lcm_state)
            log(args, msg, 2)
            raise Exception(msg)
        time.sleep(2)

def oneVmUndeploy(args):
    log(args, "oneVmUndeploy - Request VM Undeploy and wait to complete")
    cmd = ['onevm', 'undeploy']
    if args.force:
        cmd.append('--hard')
    cmd.append(str(args.vmid))
    if args.dry_run:
        out = "DRY-RUN {cmd}".format(cmd=cmd)
    else:
        out = run_cmd(args, cmd)
    msg = 'oneVmUndeploy({vmid}) hard={hard} {out}'.format(vmid=args.vmid,
            out=out, hard=args.force)
    log(args, msg, 1) 
    if args.dry_run:
        return
    oneVmWaitstate(args, STATE[9], LCM_STATE[0], 900)

def oneVmResume(args):
    log(args, "oneVmResume - Request VM Resume (waiting to run)")
    cmd = ['onevm', 'resume', str(args.vmid)]
    if args.dry_run:
        out = "DRY-RUN {cmd}".format(cmd=cmd)
    else:
        out = run_cmd(args, cmd)
    msg = 'oneVmResume({vmid}):{out}'.format(vmid=args.vmid,out=out)
    log(args, msg, 1)
    if args.dry_run:
        return
    oneVmWaitstate(args, STATE[3], LCM_STATE[3], 120)

def oneClusterData(args):
    log(args, "oneClusterData - Collect Cluster info", 1)
    cmd = ['onecluster', 'list', '--xml']
    out = run_cmd(args, cmd)
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
    if args.verbose:
        pp(cData)
    return cData

def oneDatastoreData(args):
    log(args, "oneDatastoreData - Collect Datastore info", 1)
    cmd = ['onedatastore', 'list', '--xml']
    out = run_cmd(args, cmd)
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
    if args.verbose:
        pp(cData)
    return cData

def oneVmData(args):
    log(args, "oneVmData - Collect VM info", 1)
    vmxml = oneVmXml(args)
    vm = {'ID': args.vmid, 'Element': vmxml}
    vm['NAME'] = vmxml.find('NAME').text
    vm['LCM_STATE'] = int(vmxml.find('LCM_STATE').text)
    vm['STATE'] = int(vmxml.find('STATE').text)
    vm['DISKS'] = []
    for disk in vmxml.findall('TEMPLATE/DISK'):
        d = {'Element': disk}
        for e in ['DISK_ID','DATASTORE_ID','IMAGE_ID','CLUSTER_ID']:
            try:
                d[e] = int(disk.find(e).text)
            except:
                pass
        for e in ['SOURCE','CLONE','DATASTORE','IMAGE','TYPE', 'DISK_TYPE']:
            try:
                d[e] = disk.find(e).text
            except:
                pass
        vm['DISKS'].append(d)
    state = vm['STATE']
    if STATE[state] is not None:
        state = STATE[state]
    lcm_state = vm['LCM_STATE']
    if LCM_STATE[lcm_state] is not None:
        lcm_state = LCM_STATE[lcm_state]
    vm['VM_STATE'] = "{s}:{l}".format(s=state, l=lcm_state)
    msg = "VM {vm} '{n}' STATE:LCM_STATE is {st}".format(vm=args.vmid,
            n=vm['NAME'], st=vm['VM_STATE'])
    log(args, msg)
    if args.verbose:
        pp(vm)
    return vm

def diskVolumes(args, vm):
    log(args, "diskVolumes - VM disks to StorPool volumes map", 1)
    volumes = {}
    for disk in vm['DISKS']:
        if 'CLONE' not in disk:
            name = "{}-sys-{}-{}-raw".format(
                    args.one_px, vm['ID'], disk['DISK_ID'])
            source = "{}-ds-{}".format(args.one_px, disk['DATASTORE_ID'])
        elif disk['CLONE'] == 'YES' or disk['TYPE'] == 'CDROM':
            name = "{}-img-{}-{}-{}".format(
                    args.one_px, disk['IMAGE_ID'], vm['ID'], disk['DISK_ID'])
            source = disk['SOURCE']
        else:
            name = "{}-img-{}".format(args.one_px, disk['IMAGE_ID'])
            source = disk['SOURCE']
        dsid = disk['DATASTORE_ID']
        volumes[name] = {
            "VMID":vm['ID'],
            "SOURCE":source,
            "DISK_TYPE":disk['DISK_TYPE'],
            "TYPE":disk['TYPE'],
            "DISK_ID":disk['DISK_ID'],
            "LOCAL_DATASTORE":dsData[dsid]
            }
        if 'CLUSTER_ID' in disk:
            volumes[name]['CLUSTER_ID'] = disk['CLUSTER_ID']
        dstype = dsData[dsid]['TYPE']
        spremote= dsData[dsid]['SP_REMOTE']
        for key, val in dsData.iteritems():
            try:
                if val['TYPE'] == dstype and val['SP_LOCATION'] == spremote:
                    volumes[name]['REMOTE_DATASTORE'] = val
                    break
            except:
                pass
    log(args, volumes, 1)
    return volumes

def migrateVolumes(args, volumes, stage):
    location = None
    tout = args.snapshot_timeout
    msg = "{} - Transfer snapshots".format(stage)
    if tout > 0:
        msg += "(waiting to complete)"
    log(args, msg)

    req = {"location":location,
             "tags":{"nvm":args.vmid, "cpts":time.time()},
             "volumes":[]}
    env = {}
    env_remote = {}
    for vname, vdata in volumes.iteritems():
        env.update(vdata['LOCAL_DATASTORE']['ENV'])
        env_remote.update(vdata['REMOTE_DATASTORE']['ENV'])
        req["volumes"].append(vname)
        location = vdata['LOCAL_DATASTORE']['SP_REMOTE']
        req["location"] = location
    cmd = ['storpool_req', '--json', dumps(req), '-P', 'VolumesGroupBackup']
    if args.dry_run:
        pp(env)
        log(args, 'DRY-RUN:{}'.format(' '.join(cmd)), 2)
        out = '{"backups":{}}'
    else:
        out = run_cmd(args, cmd, env)
    res = loads(out)
    # wait for the volumes...
    timeout = time.time() + tout
    if tout < 1:
        timeout = timeout + 12
    transferred = {}
    while True:
        all_found = True
        cmd = ['storpool_req', 'SnapshotsList']
        out = run_cmd(args, cmd, env_remote)
        snaps = loads(out)
        recovering = {}
        for snap in snaps:
            recovering[snap['backupOfGlobalId']] = snap['recoveringFromRemote']
        for name in res['backups']:
            remoteid = res['backups'][name]['remoteId']
            if remoteid in recovering:
                if recovering[remoteid]:
                    if tout > 0:
                        all_found = False
                    msg = "SnapshotId '{}' for Volume {} remote {} still recovering"\
                            .format(remoteid, name, location)
                    log(args, msg)
                else:
                    if remoteid not in transferred:
                        msg = "SnapshotId '{}' of Volume {} remote {} is transferred"\
                                .format(remoteid, name, location)
                        log(args, msg)
                        transferred[remoteid] = name
            else:
                all_found = False
                msg = "SnapshotId {} for Volume {} not found in remote {}"\
                                .format(remoteid, name, location)
                log(args, msg)
        if all_found:
            return res
        if time.time() > timeout:
            msg = "Timed out waiting for snapshots"
            log(args, msg, 2)
            raise RuntimeError(msg)
        time.sleep(2)
    return res

def createRemoteVolumes(args, vdata, mdata):
    log(args, "createRemoteVolumes - Create VM disk volumes on remote")
    byid = {}
    ts = time.time()
    for name, vol in vdata.iteritems():
        if len(byid) == 0:
            for key, val in mdata.iteritems():
                byid[val['remoteId']] = None
            for i in range(5):
                cnt = 0
                cmd = ['storpool_req', 'SnapshotsList']
                out = run_cmd(args, cmd, vol['REMOTE_DATASTORE']['ENV'])
                snaps = loads(out)
                for s in snaps:
                    gid = s['backupOfGlobalId']
                    if gid in byid:
                        msg = "{} -> {}" .format(
                            "globalId:{} name:{}".format(gid, byid[gid]),
                            "snapshot {} for volume {}".format(s['name'], name))
                        log(args, msg, 1)
                        byid[gid] = s['name']
                        cnt = cnt + 1
                if cnt == len(byid):
                    break
                log(args, 'snapshot names not found! {}'.format(byid), 1)
                time.sleep(2)
            for key, val in byid.iteritems():
                if val is None:
                    raise Exception(
                        "Can't find snapshot name for globalId '{}'".format(key))

            if args.verbose and not args.dry_run:
                log(args, byid)

        new_name = 'RENAMED-{}-{}'.format(name, ts)
        tags = { "nvm": str(args.vmid), "mvts": str(ts) }
        msg = "Rename '{old}' to '{new}' in datastore '{ds}'".format(
                old=name, new=new_name, ds=vol['REMOTE_DATASTORE']['NAME'])
        log(args, msg, 1)
        renameVolume(args, name, new_name,
                            vol['REMOTE_DATASTORE']['ENV'], tags)
        if args.dry_run:
            out = dumps({"DRY-RUN":"VolumeCreate:{name}".format(name=name)})
        else:
            remote_ds = vol['REMOTE_DATASTORE']
            template = "{}-ds-{}".format(args.one_px, remote_ds['ID'])
            parent = byid[mdata[name]['remoteId']]
            req = {"name": name, "parent": parent, "template": template,
                            "tags": {"nvm": args.vmid}}
            cmd = ['storpool_req', '--json', dumps(req), '-P', 'VolumeCreate']
            msg = "Creating Volume '{v}' from '{p}' in datastore '{ds}'".format(
                    v=name, p=parent, ds=remote_ds['NAME'])
            log(args, msg)
            out = run_cmd(args, cmd, remote_ds['ENV'])
        log(args, loads(out), 2)

def onedbChangeBody(args, xpath, data):
    cmd = ['onedb', 'change-body', 'vm', '--id', str(args.vmid),
            xpath, str(data)]
    log(args, ' '.join(cmd), 1)
    if args.dry_run:
        out = dumps({"DRY-RUN": "{x} to {v}".format(x=xpath, v=data)})
    else:
        out = run_cmd(args, cmd)
    log(args, out, 1)

def onedbChangeBodyDelete(args, xpath):
    cmd = ['onedb', 'change-body', 'vm', '--id', str(args.vmid),
            xpath, '--delete']
    log(args, ' '.join(cmd), 1)
    if args.dry_run:
        out = dumps({"DRY-RUN": "{x} Delete".format(x=xpath)})
    else:
        out = run_cmd(args, cmd)
    log(args, out, 1)

def onedbChangeHistory(args, seq, xpath, data):
    cmd = ['onedb', 'change-history', '--id', str(args.vmid),
            '--seq',str(seq), xpath, str(data)]
    log(args, ' '.join(cmd), 1)
    if args.dry_run:
        out = dumps({"DRY-RUN": "SEQ:{s} {x} to {v}".format(
                        s=seq, x=xpath, v=data)})
    else:
        out = run_cmd(args, cmd)
    log(args, out, 1)

def oneVmUpdate(args, volumes):
    log(args, "oneVmUpdate - Update VM's metadata")
    for key, val in volumes.iteritems():
        xpath = "/VM/TEMPLATE/DISK[DISK_ID={}]/DATASTORE_ID"\
                .format(val['DISK_ID'])
        onedbChangeBody(args, xpath,
                        val['REMOTE_DATASTORE']['ID'])
        xpath = "/VM/TEMPLATE/DISK[DISK_ID={}]/DATASTORE"\
                .format(val['DISK_ID'])
        onedbChangeBody(args, xpath,
                        val['REMOTE_DATASTORE']['NAME'])
        new_cid = val['REMOTE_DATASTORE']['CLUSTERS'][0]
        if 'CLUSTER_ID' in val:
            xpath = "/VM/TEMPLATE/DISK[DISK_ID={}]/CLUSTER_ID"\
                    .format(val['DISK_ID'])
            onedbChangeBody(args, xpath, new_cid)

    for key in ["SCHED_DS_REQUIREMENTS", "SCHED_REQUIREMENTS"]:
        xpath = "/VM/USER_TEMPLATE/{}".format(key)
        onedbChangeBodyDelete(args, xpath)

    history_seq = -1
    history_ds = -1
    sysdsid = -1
    vmxml = oneVmXml(args)
    for history in vmxml.findall('HISTORY_RECORDS/HISTORY'):
        seq = int(history.find('SEQ').text)
        if seq > history_seq:
            history_seq = seq
            history_ds = int(history.find('DS_ID').text)
    if history_ds > -1:
        sysds = dsData[history_ds]
        for did in clData[new_cid]['DATASTORES']:
            if dsData[did]['TYPE'] == 1:
                sysdsid = did
                break
        xpath = 'HISTORY/DS_ID'
        onedbChangeHistory(args, history_seq, xpath, sysdsid)
        log(args, "VM metadata updated.")
    else:
        log("WARNING! VM history record not updated!"+\
            "Probably the VM will not be re-scheduled...")

def renameVolume(args, old_name, name, env, tags={}, do_raise=False):
    try:
        req = { "rename": name,
                "tags": tags }
        cmd = [ 'storpool_req', '--json', dumps(req),
                '-P', 'VolumeUpdate', old_name ]
        log(args, ' '.join(cmd), 1)
        if args.dry_run:
            out = dumps({"DRY-RUN": "Rename volume '{old}' to '{new}'".format(
                            old=old_name, new=name)})
        else:
            out = run_cmd(args, cmd, env)
        log(args, loads(out), 1)
    except Exception as e:
        log(args, e, 1)
        if do_raise:
            raise Exception(e)

def renameSourceVolumes(args, vdata):
    log(args, "renameSourceVolumes - Rename source VM's volumes")
    ts = time.time()
    for name, vol in vdata.iteritems():
        new_name = 'MIGRATED-{}-{}'.format(name,ts)
        tags = {"nvm": str(args.vmid), "mvts": str(ts), "vc-policy": "no"}
        msg = "Rename '{old}' to '{new}', Datastore '{ds}'".format(
                old=name, new=new_name, ds=vol['LOCAL_DATASTORE']['NAME'])
        log(args, msg, 1)
        renameVolume(args, name, new_name, vol['LOCAL_DATASTORE']['ENV'], tags)

if __name__ == '__main__':
    import argparse
    syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_USER)

    pp = pprint.PrettyPrinter(indent=2).pprint
    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--dry-run", action="store_true",
                        help="do nothing")
    parser.add_argument("-s", "--skip-resume", action="store_true",
                        help="do not resume after migrate")
    parser.add_argument("-n", "--snapshot-only", action="store_true",
                        help="Only send backup snapshots")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="be verbose")
    parser.add_argument("-f", "--force", action="store_true",
                        help="be hard")
    parser.add_argument("-t", "--snapshot-timeout", action="store",
                        const=3600, default=0, nargs='?', type=int,
                        help="snapshot(s) transfer timeout in seconds")
    parser.add_argument("-p", "--one-px", action="store",
                        default=environ.get("ONE_PX", "one"),
                        nargs='?', type=str,
                        help="Object preffix in StorPool, string")
    parser.add_argument("vmid",type=int,help="ID of the VM to migrate")
    parser.add_argument("cluster_id", type=int,
                        help="destination cluster")
    try:
        args = parser.parse_args()
        if args.verbose:
            pp(args)
        dsData = oneDatastoreData(args)
        clData = oneClusterData(args)
        vmData = oneVmData(args)
        if args.cluster_id not in clData:
            log(args, "Please provide CLUSTER_ID")
            exit(1)

        vmData['CLUSTER_ID'] = dsData[vmData['DISKS'][0]['DATASTORE_ID']]['CLUSTERS'][0]
        if args.cluster_id == vmData['CLUSTER_ID']:
            log(args, "VM {} is already in cluster {} '{}'".format(args.vmid,
                  vmData['CLUSTER_ID'], clData[vmData['CLUSTER_ID']]['NAME']))
            exit(1)
        else:
            log(args,"Moving VM {} '{}' to cluster {} '{}' ...".format(
                args.vmid, vmData['NAME'], args.cluster_id,
                clData[args.cluster_id]['NAME']))

        spVolumes = diskVolumes(args, vmData)

        if args.snapshot_only:
            snapshots = migrateVolumes(args, spVolumes, 'send-snapshots')
            pp(snapshots)
            print("END - only backup snapshots are sent")
            exit(0)

        if vmData['VM_STATE'] != 'UNDEPLOYED:LCM_INIT':
            if vmData['VM_STATE'] not in ['ACTIVE:RUNNING', 'POWEROFF:LCM_INIT']:
                msg = "Unsupported VM state for migration.".format(
                        vmData['VM_STATE'])
                msg += " UNDEPLOYED or ACTIVE expected."
                log(args, msg)
                exit(1)
            if args.snapshot_timeout > 0:
                migrated = migrateVolumes(args, spVolumes, 'pre-snapshot')
            oneVmUndeploy(args)

        migrated = migrateVolumes(args, spVolumes, 'last-snapshot')

        try:
            createRemoteVolumes(args, spVolumes, migrated['backups'])
        except Exception as e:
            log(args, e)
            if not args.skip_resume:
                oneVmResume(args)
            raise Exception(e)

        oneVmUpdate(args, spVolumes)

        if args.skip_resume or vmData['VM_STATE'] == 'UNDEPLOYED:LCM_INIT':
            log(args, "oneVmResume - skipped", 2)
        else:
            oneVmResume(args)

        renameSourceVolumes(args, spVolumes)

        log(args, "Done - Migration completed")

    except Exception as e:
        stdout.flush()
        log(args, traceback.print_exc())
        exit(1)

