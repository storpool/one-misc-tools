Summary: StorPool contextualization package repository for OpenNebula VMs
Name: one-context-sp-release
Version: 1.0
Release: 0%{?dist}
License: Apache 2.0
URL: https://github.com/storpool/one-context-sp
Source0: CentOS-one-context-sp.repo
Source1: LICENSE

BuildArch: noarch

Requires: centos-release

%description
yum configuration for StorPool contextualization package
for OpenNebula managed VMs.

%prep
cp %{SOURCE1} .

%install
install -D -m 644 %{SOURCE0} %{buildroot}%{_sysconfdir}/yum.repos.d/CentOS-one-context-sp.repo

%files
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/yum.repos.d/CentOS-one-context-sp.repo
%license LICENSE

%changelog
* Thu Aug 22 2019 Anton Todorov <a.todorov@storpool.com> - 1.0-0
- Initial release
