Name: one-context-sp-release
Version: 1.0
Release: 1%{?dist}
Summary: StorPool contextualization package repository for OpenNebula VMs
Group: System Environment/Base
License: Apache 2.0
URL: https://github.com/storpool/one-context-sp
Source0: CentOS-one-context-sp.repo
Source1: LICENSE
Source2: RPM-GPG-KEY-StorPool-Context

BuildArch: noarch

%description
yum configuration for StorPool contextualization package
for OpenNebula managed VMs.

%prep
%setup -q -c -T
install -pm 644 %{SOURCE1} .

%install
rm -rf $RPM_BUILD_ROOT

# yum repo
install -dm 755 $RPM_BUILD_ROOT%{_sysconfdir}/yum.repos.d
install -pm 644 %{SOURCE0} $RPM_BUILD_ROOT%{_sysconfdir}/yum.repos.d

# GPG Key
install -dm 755 $RPM_BUILD_ROOT%{_sysconfdir}/pki/rpm-gpg
install -pm 644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/pki/rpm-gpg

%post
rpmkeys --import -- '/etc/pki/rpm-gpg/RPM-GPG-KEY-StorPool-Context'

%files
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/yum.repos.d/CentOS-one-context-sp.repo
%{_sysconfdir}/pki/rpm-gpg/RPM-GPG-KEY-StorPool-Context
%license LICENSE

%changelog
* Thu Aug 22 2019 Anton Todorov <a.todorov@storpool.com> - 1.0-1
- add gpg key
- enable gpgcheck

* Thu Aug 22 2019 Anton Todorov <a.todorov@storpool.com> - 1.0-0
- Initial release
