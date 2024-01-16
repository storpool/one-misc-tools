This is a set of scripts to support the process of migration of virtual
machines to OpenNebula.

The scripts create a VM in OpenNabula and persistent images for virtual
disk(s), copy the disk images from a source iSCSI SAN to the created images on
StorPool and start the VM.

Requirements
============

1. A running OpenNebula cloud with StorPool Storage and KVM hosts.

2. One of the KVM hosts to be assigend as a `transfer host`. It can still
   be used as an OpenNebula host.

3. The `transfer hosts` is configured as an iSCSI initiator and can connect to
   the source iSCSI SAN.

4. iscsi-initiator-utils and storpool cli installed on the `transfer host`.


Install
========

Transfer host
--------------

1. Copy `copy_image.py` to a selected directory on the transfer host.

2. Add the following line to `/etc/sudoers` or :

        oneadmin ALL=(ALL:ALL) NOPASSWD: /usr/sbin/iscsiadm

OpenNebula front end
--------------------

1. Copy `migrate_vm.py` to the OpenNebula front end.

2. Edit `migrate_vm.py` and set the path to the `copy_image.py` script on the transfer host.


Usage
======

Create a VM template file in the working directory of OpenNebula front
end. It can contain any VM configuration as parameters in the format of
"OpenNebula Virtual Machine Template" - see
https://docs.opennebula.io/6.8/management_and_operations/references/template.html#template

Don't include any disks in the template file. They will be added
automatically by the migartrion script.

You can use placeholders for parameters of the migration script e.g.
`{name}`, `{cpu}`, `{ram}`, etc. See the template.example. 

On the OpenNebula frontend run `migrate_vm.py` as `oneadmin` user:


        usage: migrate_vm.py [-h] [--debug] [--one-prefix ONE_PREFIX] --name NAME --template
                             TEMPLATE --user-id USER_ID --group-id GROUP_ID --cpu CPU --pcpu PCPU
                             --ram RAM --network NETWORK [--ip IP] [--datastore DATASTORE]
                             --disk-size DISK_SIZE --disk-source DISK_SOURCE --host HOST --portal
                             PORTAL
        
        options:
          -h, --help            show this help message and exit
          --debug, -D           Enable debug output
          --one-prefix ONE_PREFIX
                                prefix used by OpenNebula addon for StorPool
          --name NAME           Name of the created VM
          --template TEMPLATE   filename of VM configuration tempalte. Shall contain static
                                configuration similar to the output of `onevm show`
          --user-id USER_ID     OpenNebula user ID, owner of the VM
          --group-id GROUP_ID   OpenNebula group ID, group of the VM
          --cpu CPU             Number of vCPUs
          --pcpu PCPU           Number of physical CPUs
          --ram RAM             RAM in MiB
          --network NETWORK     Network ID, as reported by onevnet list
          --ip IP               Sets the IP address if provided. OpenNebula will assing the next
                                available address from the network range, if not provided
          --datastore DATASTORE
                                Datastore ID in OpenNebula to store the disk images
          --disk-size DISK_SIZE
                                Size of the disk in GiB. Shall be specified one per each disk.
                                The number and order shall match the --disk-source items.
          --disk-source DISK_SOURCE
                                Source image IQN and LUN. Shall be specified one per each disk.
                                The number and the order shall match the --disk-size items.
                                Example: 'iqn.example.com:volume1-lun-0'
          --host HOST           Transfer host. This is the host that will perform the actual
                                transfer of the image content.
          --portal PORTAL       IP addrerss of the iSCSI portal for the source volumes
        

Example:

	# su - oneadmin
	$ ./migrate_vm.py --debug --one-prefix one --name "test vm" \
	--template template1 --user-id 40 --group-id 102 --cpu 8 --pcpu 0.5 \
	--ram 16384 --network 6 --ip 10.22.33.44 --datastore 101 \
        --disk-size 10 --disk-source iqn.2024-01.com.example:volume1 \
        --disk-size 50 --disk-source iqn.2024-01.com.example:volume2 \
        --host kvm5.cloud.example.com --portal iscsi-san-1.cloud.example.com

This will create a VM in OpenNebula with a name "test vm", 8 virtual CPUs,
16GiB RAM, two virtual disks - 10GiB and 50 GiB, one network interface attached
to virtual netowork ID 6. It will assign IP address 10.22.33.44 to this
interface. VM will be owned by user ID 40, group ID 102. The virual disk images
will be copied from the provded iSCSI targets. When the copy of the images is
completed, the VM will be stareted in OpenNebula cloud.

You can specify one or more virtual disks when creating the virtual machine.
For each disk you have to specify the disk size in GiB and the source image in
the iSCSI array. The order you specify the disks is important.

Note that the user and the virtual newtork shall be created in OpenNebula in
advance.

Limitations
============

1. The scripts here don't handle any possible image convertion (e.g., qcow to raw)
or OS morphing (e.g., install virtio drivers, update boot options, rename
drives, etc.). It can be used without modification if the there is no change of
the hypervisor type.

2. VM name shall be unique for the user.

