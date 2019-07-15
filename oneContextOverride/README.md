one-context-override
===============================================================================

# installation
## install via contextualizaciont

```bash
# copy the scrpit to /var/lib/one
cp one-context-override /var/lib/one/
chown oneadmin.oneadmin one-context-override

#Add the follwing contextualization variables
# note that a patched version of 'onedb change-body ...' is mandatory
onedb change-body vm --id $VMID '/VM/TEMPLATE/CONTEXT/FILES' '/var/lib/one/one-context-override'
onedb change-body vm --id $VMID '/VM/TEMPLATE/CONTEXT/INIT_SCRIPTS' 'one-context-override'
