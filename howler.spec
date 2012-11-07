%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Name:       howler
Version:    0.1
Release:    2%{?dist}
Summary:    Alert when users log in from new locations

License:    GPLv3
URL:        http://pending/
Source0:    %{name}-%{version}.tar.gz

Requires:   python-GeoIP, rsyslog
BuildArch:  noarch

%description
Works in conjunction with rsyslog to alert admins when there are user logins
from new locations.


%prep
%setup -q


%install
mkdir -p %{buildroot}%{python_sitelib}
cp -a howler %{buildroot}%{python_sitelib}
mkdir -p %{buildroot}%{_bindir}
install -m 0755 howl howler-syslog-helper %{buildroot}%{_bindir}/
mkdir -p %{buildroot}%{_sysconfdir}/howler
install -m 0644 howler.ini syslog-regexes %{buildroot}%{_sysconfdir}/howler/
mkdir -p %{buildroot}%{_sysconfdir}/rsyslog.d
install -m 0644 howler-rsyslog.conf \
    %{buildroot}%{_sysconfdir}/rsyslog.d/howler.conf
mkdir -p %{buildroot}%{_localstatedir}/lib/howler
mkdir -p %{buildroot}%{_sysconfdir}/cron.daily
install -m 0755 howler-cleanup.cron %{buildroot}%{_sysconfdir}/cron.daily/


%files
%doc COPYING
%config(noreplace) %{_sysconfdir}/howler
%config(noreplace) %{_sysconfdir}/rsyslog.d/*
%config(noreplace) %{_sysconfdir}/cron.daily/*
%{python_sitelib}
%{_bindir}/*
%{_localstatedir}/lib/howler


%changelog
* Tue Nov 06 2012 Konstantin Ryabitsev <mricon@kernel.org>
- Initial spec file.
