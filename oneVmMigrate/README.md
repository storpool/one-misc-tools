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

OpenNebula configuration
-------------------------------------------------------------------------------

Add the following atributes to the Datastore Template(s)

SP_REMOTE     - remote cluster location
SP_LOCATION   - the location of the StorPool cluster that the Datastore belongs to


