#!/bin/bash
#
# (c) StorPool

set -e -o pipefail

declare -A oneconf
tmp="$(grep "DB=" ~oneadmin/config | cut -d= -f2-)"
OFS=$IFS
IFS=,
arr=( $tmp )
IFS=$OFS
for e in "${arr[@]}"; do
  oneconf["${e%=*}"]="${e##*=}"
done

[ "${oneconf[BACKEND],,}" = "mysql"  ] || exit

CONF_FILE="/etc/storpool/oneBackupDB.conf"
if [ -f "$CONF_FILE" ]; then
    source "$CONF_FILE"
fi

function log()
{
#  echo "ZDBG:$*"
  logger -t "${0##*/}" -- "$*"
}

[ "${oneconf[BACKEND],,}" = "mysql"  ] || exit

umask 0077
export PATH=/bin:/usr/bin:/sbin:/usr/sbin:$PATH

BACKUP_PATH="${BACKUP_PATH:-/var/lib/one/db_backup}"
COMPRESS="${COMPRESS:-xz}"

d=($(date +"%Y %m %d %H %M %S"))

BACKUP_DIR="${BACKUP_PATH}/${d[0]}/${d[1]}"

mkdir -p "$BACKUP_DIR"

TS="${d[0]}${d[1]}${d[2]}-${d[3]}${d[4]}${d[5]}"
BACKUP_FILE="$BACKUP_DIR/${oneconf[DB_NAME]}-${TS}.sql"

MY_CNF="$(mktemp)"
trap "rm -f '$MY_CNF'" EXIT QUIT KILL HUP
chmod 600 "$MY_CNF"
cat >"$MY_CNF" <<EOF
[client]
user=${oneconf[USER]}
password=${oneconf[PASSWD]}
EOF
opts=
[ -n "$SKIP_DEFAULTS_FILE" ] || opts+=" --defaults-file=$MY_CNF"
opts+=" --host=${oneconf[SERVER]:-localhost}"
opts+=" --single-transaction"
opts+=" --create-options"
opts+=" --complete-insert"
opts+=" --dump-date"
opts+=" --extended-insert"
#opts+=" --flush-logs"
opts+=" --force"
opts+=" ${oneconf[DB_NAME]:-opennebula}"

tstart=$(date +%s)
mysqldump $opts  >"${BACKUP_FILE}"
tend=$(date +%s)
log "Dumped $BACKUP_FILE in $((tend-tstart)) seconds"

rm -f "$MY_CNF"
trap - EXIT QUIT KILL HUP

if [ -n "$COMPRESS" ]; then
  tstart=$tend
  $COMPRESS "${BACKUP_FILE}"
  tend=$(date +%s)
  log "Compressed $BACKUP_FILE in $((tend-tstart)) seconds"
fi

prevdate=($(date -d"today -1 day" +"%Y %m %d %H %M %S"))
if [ ${prevdate[1]} -ne ${d[1]} ]; then
  prevdate=($(date -d"today -2 months" +"%Y %m %d %H %M %S"))
  BACKUP_DIR="${BACKUP_PATH}/${prevdate[0]}/${prevdate[1]}"
  if [ -d "$BACKUP_DIR" ]; then
    lastfile="$(ls -t "$BACKUP_DIR" | head -n 1)"
    BACKUP_DST="${BACKUP_DIR%/*}/$lastfile"
    mv "${BACKUP_DIR}/$lastfile" "${BACKUP_DST}"
    log "Saved ${BACKUP_DST}"
    rm -rf "$BACKUP_DIR"
    log "Removed $BACKUP_DIR"
  fi
fi

