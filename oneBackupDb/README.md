oneBackupDB
===============================================================================

Script to do daily OpenNebula DB backups for a month and a monthly backups
for the older ones.

# installation

```bash
sudo mkdir -p /etc/storpool
sudo cp oneBackupDB.conf  /etc/storpool/
sudo chmod 0640 /etc/storpool/oneBackupDB.conf
mkdir -p /usr/lib/storpool
sudo cp oneBackupDB.sh /usr/lib/storpool/
sudo chmod 0755 /usr/lib/storpool/oneBackupDB.sh
sudo cp oneBackupDB.{timer,service} /etc/systemd/system
sudo systemdtl daemon-reload
sudo systemctl enable oneBackupDB.timer
```

The script parses the `DB=` line from `/var/lib/one/config` to get the running
OpenNebula configuration.

The backups are stored in `/var/lib/one/db_backup/YYYY/MM/`.

The default configuration could be tweaked via `/etc/storpool/oneBackupDB.conf` file.

With OpenNebula 6.2+ the `PASSWD=` field is obfuscated so the DB password could be
provided in `/etc/storpool/oneBackupDB.conf`.

Use `SKIP_DEFAULTS_FILE=1` to use local password-less authorisation to mysql.
