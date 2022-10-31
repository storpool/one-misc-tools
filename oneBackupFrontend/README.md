
Install
===============================================================================

```bash
sudo mkdir -p /etc/storpool
sudo cp backup-frontend.conf  /etc/storpool/
mkdir -p /usr/lib/storpool
sudo cp backup-frontend.sh /usr/lib/storpool/
sudo chmod a+x /usr/lib/storpool/backup-frontend.sh
sudo cp backup-frontend.{timer,service} /etc/systemd/system
sudo systemdtl daemon-reload
sudo systemctl enable backup-frontend.timer
```

