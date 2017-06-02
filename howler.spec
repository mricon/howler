Name:       python2-howler
Version:    0.3
Release:    1%{?dist}
Summary:    Alert when users log in from new locations

License:    GPLv3+
URL:        https://github.com/mricon/howler
Source0:    https://github.com/mricon/howler/archive/v%{version}.tar.gz

Requires:   python-GeoIP, /usr/sbin/sendmail, python-unidecode, logrotate
Requires:   python-netaddr
BuildArch:  noarch

%description
Keeps a database of usernames and IPs/locations and alerts the admins when
users log in from a location previously not seen. This package contains
core python libraries and the commandline utility.

%prep
%setup -q -n howler-%{version}

%build
%py2_build

%install
%py2_install

mkdir -p %{buildroot}%{_sysconfdir}/cron.daily
install -m 0755 bin/howler-cleanup.cron %{buildroot}%{_sysconfdir}/cron.daily/

mkdir -p %{buildroot}%{_sysconfdir}/howler
install -m 0644 conf/howler.ini %{buildroot}%{_sysconfdir}/howler/

mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
install -m 0644 conf/logrotate.conf %{buildroot}%{_sysconfdir}/logrotate.d/howler.conf

mkdir -p %{buildroot}%{_localstatedir}/lib/howler
mkdir -p %{buildroot}%{_localstatedir}/log/howler

%files
%doc COPYING README.rst conf/howler.sec
%config %dir %{_sysconfdir}/howler
%config(noreplace) %{_sysconfdir}/howler/howler.ini
%config(noreplace) %{_sysconfdir}/cron.daily/*
%config(noreplace) %{_sysconfdir}/logrotate.d/howler.conf
%{python2_sitelib}/*
%{_bindir}/howler
%{_localstatedir}/lib/howler
%{_localstatedir}/log/howler


%changelog
* Fri Jun 02 2014 Konstantin Ryabitsev <konstantin@linuxfoundation.org>
- Final 0.3 release
- Remove selinux subpackage (rsyslog plugin deprecated)

* Fri Sep 13 2013 Konstantin Ryabitsev <mricon@kernel.org>
- Preliminary 0.3 release with new features.

* Sun Jun 16 2013 Rene Cunningham <rene@linuxfoundation.org>
- Run fixfiles for howler-rsyslog.

* Thu Nov 08 2012 Konstantin Ryabitsev <mricon@kernel.org>
- Update to 0.2 and split into subpackages.
- Add selinux subpackage.

* Tue Nov 06 2012 Konstantin Ryabitsev <mricon@kernel.org>
- Initial spec file.
