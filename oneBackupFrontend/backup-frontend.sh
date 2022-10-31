#!/bin/bash
#
# Anton Todorov (a.todorov@storpool.com)
#
# vim: ts=4 sw=4 sts=0 noet

if [ -f /etc/storpool/backup-frontend.conf ]; then
	source /etc/storpool/backup-frontend.conf
fi

export PATH=/bin:/sbin:/usr/bin:/usr/sbin:$PATH

DELETE_KEEP_COUNT="${DELETE_KEEP_COUNT:-2}"
DELETE_DELAY_SECONDS="${DELETE_DELAY_SECONDS:-.2}"

FRONTEND_VOLUME="${FRONTEND_VOLUME:-frontend}"
SNAPSHOT_TAG="${SNAPSHOT_TAG:-$FRONTEND_VOLUME}"

me="${0##*/}"
LOCKFILE="/var/lib/one/$me.lock"

DELETE_KEEP_DAYS="${DELETE_KEEP_DAYS:-72}"
DELETE_KEEP_HOURS="${DELETE_KEEP_HOURS:-$((DELETE_KEEP_DAYS*24))}"
DELETE_KEEP_MINUTES="${DELETE_KEEP_MINUTES:-$((DELETE_KEEP_HOURS*60))}"
DELETE_KEEP_SECONDS="${DELETE_KEEP_SECONDS:-$((DELETE_KEEP_MINUTES*60))}"

function boolTrue()
{
	case "${1^^}" in
		1|Y|YES|TRUE|ON)
			return 0
			;;
		*)
			return 1
	esac
}

function splog()
{
#	echo "$*" #&& return
	logger -t "$me[$$]" -- "$*"
}

function backupEnd()
{
	local _ret=$?
	if [ $_ret -ne 0 ]; then
		splog "Error with exit code ${_ret}, args:$*"
	fi
	if [ -d "$TMPDIR" ]; then
		rm -fr "$TMPDIR"
	fi
	exit $_ret
}

function storpoolApi()
{
	if [ -z "$SP_API_HTTP_HOST" ]; then
		if [ -x /usr/sbin/storpool_confget ]; then
			eval `/usr/sbin/storpool_confget -S`
		fi
		if [ -z "$SP_API_HTTP_HOST" ]; then
			splog "storpoolApi: ERROR! SP_API_HTTP_HOST is not set!"
			return 1
		fi
	fi
	if boolTrue "$NO_PROXY_API";then
		export NO_PROXY="${NO_PROXY:+${NO_PROXY},}$SP_API_HTTP_HOST"
	fi
	if boolTrue "$DEBUG_SP_RUN_CMD_VERBOSE"; then
		splog "SP_API_HTTP_HOST=$SP_API_HTTP_HOST SP_API_HTTP_PORT=$SP_API_HTTP_PORT SP_AUTH_TOKEN=${SP_AUTH_TOKEN:+available} ${NO_PROXY:+NO_PROXY=${NO_PROXY}}"
	fi
	curl -s -S -q -N -H "Authorization: Storpool v1:$SP_AUTH_TOKEN" \
	--connect-timeout "${SP_API_CONNECT_TIMEOUT:-1}" \
	--max-time "${3:-300}" ${2:+-d "$2"} \
	"$SP_API_HTTP_HOST:${SP_API_HTTP_PORT:-81}/ctrl/1.0/$1" 2>/dev/null
	splog "storpoolApi $1 $2 ret:$?"
}

function storpoolWrapper()
{
#	if [ -n "$2" ]; then
		res="$(storpoolApi "VolumeSnapshot/$1" "{\"name\":\"$2\",\"tags\":{\"$SNAPSHOT_TAG\":\"$SNAPSHOT_TAG\"}}")"
		ret=$?
		if [ $ret -ne 0 ]; then
			splog "API communication error:$res ($ret)"
			return $ret
		else
			ok="$(echo "$res"|jq -r ".data|.ok" 2>&1)"
			if [ "$ok" = "true" ]; then
				if boolTrue "$DEBUG_SP_RUN_CMD_VERBOSE"; then
					splog "API response:$res"
				fi
			else
				splog "API Error:$res info:$ok"
				return 1
			fi
		fi
#	else
#		splog "storpoolWrapper: Error: Empty volume list!"
#		return 1
#	fi
}

function doCleanup()
{
	[ -n "$SNAPSHOT_TAG" ] || return

	SNAPSHOTS="$TMPDIR/snapshot_list.json"
	storpool -B -j snapshot list >"$SNAPSHOTS"
	ret=$?
	if [ $ret -ne 0 ]; then
		splog "Can't get snapshots JSON ($ret)"
	fi
	
	declare -A sCounts sNames sTimes
	now=$(date +%s)
	
	while IFS=',' read sTime sName sDeleted; do
		#splog "$sTime $sName $sDeleted"
		sName="${sName//\"/}"
		volume=${sName%-BACKUP*}
		[ "$sDeleted" = "false" ] || continue
		[ ${sCounts[$volume]+_} ] && sCount=${sCounts[$volume]} || sCount=0
		sCounts[$volume]=$((sCount+1))
		sNames[$volume]+=" $sName"
		sTimes[$volume]+=" $sTime"
	done < <(jq -r --arg tag "$SNAPSHOT_TAG" '.data|map(select(.onVolume==$tag))|sort_by(.creationTimestamp)[]|[.creationTimestamp,.name,.deleted]|@csv' "$SNAPSHOTS")
	
	for volume in ${!sNames[@]}; do
		count=${sCounts[$volume]}
		times=(${sTimes[$volume]})
		names=(${sNames[$volume]})
		for idx in ${!names[@]}; do
			ts=${times[$idx]}
			snap=${names[$idx]}
			tsx="$(date -d "@$ts")"
			#printf "%-15s %3d %3d : $ts : $snap : %s " "$volume" $count $idx "$(date -d "@$ts")"
			if [ $((ts+DELETE_KEEP_SECONDS)) -lt $now ]; then
				if [ $((count-idx)) -gt $DELETE_KEEP_COUNT ]; then
					storpool snapshot "$snap" delete "$snap" >/dev/null
					splog "$tsx $snap delete ret:$?"
					if [ -n "$DELETE_DELAY_SECONDS" ]; then
						sleep "$DELETE_DELAY_SECONDS"
					fi
				else
					splog "$tsx $snap keep (count $count)"
				fi
			else
				splog "$tsx $snap keep (ts)"
			fi
		done
	done
}

(

flock -x 200
TMPDIR="$(mktemp -d -t spone-ZZXXXXXXXX)"
ERRLOG="$TMPDIR/log"

trap backupEnd EXIT TERM INT HUP QUIT

sleep 3

storpoolWrapper "$FRONTEND_VOLUME" "${FRONTEND_VOLUME}-BACKUP-$(date +%s)"

doCleanup

) 200>"$LOCKFILE"

