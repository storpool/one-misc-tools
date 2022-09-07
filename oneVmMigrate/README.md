oneVmMigrate
===============================================================================

Tool for (offline) migrating ONE VM's to other StorPool Cluster, managed by single OpenNebula controler (two separate Clusters in OpenNebula)

```
Usage: oneVmMigrate.py [-h] [-N] [-s] [-v] [-f] [-t [<seconds>]] vmid cid

  vmid - OpenNebula's VM ID of the VM to migrate (number)
  cid  - Cluster ID to migrate the VM to (number)

Optional arguments:

 -N, --dry-run          - Do nothing, only print what will be done
 -s, --skip-resume      - Do not resume after migrate
 -t, --snapshot-timeout - Send pre-snapshot, wait to complete(default: 3600sec)
 -v, --verbose          - Be verbose
 -f, --force            - Do hard VM Undeploy instead of waiting for graceful shutdown
```

Installing dependancies
-------------------------------------------------------------------------------

```bash
yum -y install python-simplejson python-pip
pip install -U storpool
```

OpenNebula configuration
-------------------------------------------------------------------------------

Add the following atributes to the Datastore Template(s)

  * _SP_REMOTE_     - remote cluster location for the Datastore (where to migrate)
  * _SP_LOCATION_   - the location of the StorPool cluster that the Datastore belongs to


Naming convention
-------------------------------------------------------------------------------

* pre-snapshots - An anonymous snapshots are ceated with the following tags:
     
    * _nvm_    - VM ID
    * _cpts_   - Timestamp

* backup destination Volume(s) - If there are Volumes on the destination cluster they will be renamed to _RENAMED-{originalName}-{timestamp}_
And the following tags are set:

    * _nvm_    - VM ID
    * _mvts_   - Timestamp

* backup source Volume(s) - After successful migration the Volume(s) on the source datastore are renamed _MIGRATED-{originalName}-{timestamp}'_
And folling tags are set:

    * _nvm_    - VM ID
    * _mvts_   - Timestamp


Altered VM metadata in OpenNebula
-------------------------------------------------------------------------------

The following XPATH elements are replaced:

XPATH | Value
-------------------------------------------------- | --------------------------------
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE | ${DESTINATION_DATASTORE_NAME}
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE_ID | ${DESTINATION_DATASTORE_ID}

Example commands:
```bash
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE" "$DS_NAME"
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE_ID" "$DS_ID"
```

Optionally, on OpenNebula 5.8.3+:

XPATH | Value
-------------------------------------------------- | --------------------------------
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/CLUSTER_ID | ${DESTINATION_CLUSTER_ID}

```bash
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/CLUSTER_ID" "$CLUSTER_ID"
```

The SYSTEM Datastore ID in the last History Record, identified by the biggest SEQ number is altered too:

XPATH | Value
-------------------------------------------------- | --------------------------------
HISTORY/DS_ID | $DESTINATION_SYSTEM_DS_ID

```bash
onedb change-history --id ${VM_ID} --seq ${LAST_SEQ} "HISTORY/DS_ID" "${DESTINATION_SYSTEM_DS_ID}"
```

The following XPATH elements are deleted:

```
/VM/USER_TEMPLATE/SCHED_DS_REQUIREMENTS
/VM/USER_TEMPLATE/SCHED_REQUIREMENTS
```

```bash
onedb change-body vm --id ${VM_ID} "/VM/USER_TEMPLATE/SCHED_DS_REQUIREMENTS" --delete
onedb change-body vm --id ${VM_ID} "/VM/USER_TEMPLATE/SCHED_REQUIREMENTS" --delete
```

