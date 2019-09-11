#!/bin/bash

REPOURL=${REPOURL:-http://repo.storpool.com/public/one-context-sp/centos/\$releasever/noarch}

if ! which rpmbuild >/dev/null 2>&1; then
	echo "Error rpmbuild not found! Install with " >&2
	echo " yum install -y rpm-build" >&2
	exit 1
fi

mkdir -p ~/rpmbuild/{SOURCES,SPECS,SRPMS,RPMS/noarch}

cp ./CentOS-one-context-sp.repo ./LICENSE ./RPM-GPG-KEY-StorPool-Context \
        ~/rpmbuild/SOURCES/

cp one-context-sp-release.spec ~/rpmbuild/SPECS

sed -i "s|__REPOURL__|$REPOURL|g" ~/rpmbuild/SOURCES/CentOS-one-context-sp.repo 

rpmbuild -ba ~/rpmbuild/SPECS/one-context-sp-release.spec

