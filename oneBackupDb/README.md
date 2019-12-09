backupdb
===============================================================================

Script to do daily OpenNebula DB backups for a month and a monthly backups
for the older ones.

# installation

```bash
cp backupdb /etc/cron.daily/
```

The script parses the `DB=` line from `/var/lib/one/config` to get the running
OpenNebula configuration.

The backups are stored in `/var/lib/one/db_backup/YYYY` the monthly backups.
The daily backups are in subfolder of the month.

The default configuration could be tweaked via `/etc/backupdb.conf` file.
