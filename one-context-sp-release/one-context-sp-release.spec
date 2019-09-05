Name: one-context-sp-release
Version: 1.0
Release: 0%{?dist}
Summary: StorPool contextualization package repository for OpenNebula VMs
Group: System Environment/Base
License: Apache 2.0
URL: https://github.com/storpool/one-context-sp
Source0: CentOS-one-context-sp.repo
Source1: LICENSE

BuildArch: noarch

%description
yum configuration for StorPool contextualization package
for OpenNebula managed VMs.

%prep
%setup -q -c -T
install -pm 644 %{SOURCE1} .

%install
rm -rf $RPM_BUILD_ROOT

install -dm 755 $RPM_BUILD_ROOT%{_sysconfdir}/yum.repos.d
install -pm 644 %{SOURCE0} $RPM_BUILD_ROOT%{_sysconfdir}/yum.repos.d

%files
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/yum.repos.d/CentOS-one-context-sp.repo
%license LICENSE

%changelog
* Thu Aug 22 2019 Anton Todorov <a.todorov@storpool.com> - 1.0-0
- Initial release
