oneVmMigrate
===============================================================================

Tool for (offline) migrating ONE VM's to other StorPool Cluster, managed by single OpenNebula controler (two separate Clusters in OpenNebula)

usage: oneVmMigrate.py [-h] [-N] [-s] [-v] [-f] vmid

  vmid - OpenNebula's VM ID of the VM to migrate (number)

Optional arguments:

  -N, --dry-run      - Do nothing, only print what will be done
  -s, --skip-resume  - Do not resume after migrate
  -v, --verbose      - Be verbose
  -f, --force        - Do hard VM Undeploy instead of waiting for graceful


Installing dependancies
-------------------------------------------------------------------------------

```bash
yum -y install python-simplejson python-pip

pip install -U storpool
```

OpenNebula configuration
-------------------------------------------------------------------------------

Add the following atributes to the Datastore Template(s)


  SP_REMOTE     - remote cluster location
  SP_LOCATION   - the location of the StorPool cluster that the Datastore belongs to


Naming convention
-------------------------------------------------------------------------------

pre-snapshots

An anonymous snapshots are ceated with the following tags

    _nvm_    - VM ID
    _cpts_   - Timestamp

If there are Volumes on the destination cluster they will be renamed to _RENAMED-{originalName}-{timestamp}_
And the following tags are set:

    _nvm_    - VM ID
    _mvts_   - Timestamp

After successful migration the Volume(s) on the source datastore are renamed _MIGRATED-{originalName}-{timestamp}'_
And folling tags are set:

    _nvm_    - VM ID
    _mvts_   - Timestamp


Altered VM metadata in OpenNebula
-------------------------------------------------------------------------------

The following XPATH elements are replaced:

-------------------------------------------------- --------------------------------
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE    ${DESTINATION_DATASTORE_NAME}
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE_ID ${DESTINATION_DATASTORE_ID}
-------------------------------------------------- --------------------------------

Example commands:
```bash
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE" "$DS_NAME"
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/DATASTORE_ID" "$DS_ID"
```

Optionally, on OpenNebula 5.8.3+:
-------------------------------------------------- --------------------------------
/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/CLUSTER_ID   ${DESTINATION_CLUSTER_ID}
-------------------------------------------------- --------------------------------

```bash
onedb change-body vm --id ${VM_ID} "/VM/TEMPLATE/DISK[DISK_ID=${DISK_ID}]/CLUSTER_ID" "$CLUSTER_ID"
```

The SYSTEM Datastore ID in the last History Record, identified by the biggest SEQ number is altered too:
-------------------------------------------------- --------------------------------
/HISTORY/DS_ID
-------------------------------------------------- --------------------------------

```bash
onedb change-history --id ${VM_ID} --seq ${LAST_SEQ} "HISTORY/DS_ID" "${DESTINATION_SYSTEM_DS_ID}"
```

