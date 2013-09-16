%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%global selinux_policyver %(%{__sed} -e 's,.*selinux-policy-\\([^/]*\\)/.*,\\1,' /usr/share/selinux/devel/policyhelp || echo 0.0.0)

%global selinux_variants mls strict targeted

Name:       python-howler
Version:    0.3
Release:    0.pre.2%{?dist}
Summary:    Alert when users log in from new locations

License:    GPLv3+
URL:        https://github.com/mricon/howler
Source0:    howler-%{version}.tar.gz

Requires:   python-GeoIP, /usr/sbin/sendmail, python-unidecode, logrotate
BuildArch:  noarch

BuildRequires: selinux-policy, selinux-policy-doc, hardlink

%description
Keeps a database of usernames and IPs/locations and alerts the admins when
users log in from a location previously not seen. This package contains
core python libraries and the commandline utility.

%package -n howler-rsyslog
Summary:        Rsyslog hooks and helper for howler
Requires:       python-howler = %{version}-%{release}
Requires(post): howler-selinux = %{version}-%{release}

%description -n howler-rsyslog
Hooks into rsyslog and passes matching entries to howler for location
analysis.

%package -n howler-selinux
Summary:    SELinux policies for howler
Requires:   selinux-policy >= %{selinux_policyver}
Requires(post):   python-howler = %{version}-%{release}
Requires(post):   /usr/sbin/semodule, /sbin/restorecon, /sbin/fixfiles
Requires(postun): /usr/sbin/semodule, /sbin/restorecon, /sbin/fixfiles

%description -n howler-selinux
This package includes SELinux policy for howler and its helpers.

%prep
%setup -q -n howler-%{version}

%build
%{__python} setup.py build
pushd selinux
for selinuxvariant in %{selinux_variants}
do
  make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile
  mv howler.pp howler.pp.${selinuxvariant}
  make NAME=${selinuxvariant} -f /usr/share/selinux/devel/Makefile clean
done
popd

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

mkdir -p %{buildroot}%{_bindir}
install -m 0755 bin/howler bin/howler-syslog-helper %{buildroot}%{_bindir}/
mkdir -p %{buildroot}%{_sysconfdir}/cron.daily
install -m 0755 bin/howler-cleanup.cron %{buildroot}%{_sysconfdir}/cron.daily/

mkdir -p %{buildroot}%{_sysconfdir}/howler
install -m 0644 conf/howler.ini conf/syslog-regexes \
    %{buildroot}%{_sysconfdir}/howler/
mkdir -p %{buildroot}%{_sysconfdir}/rsyslog.d
install -m 0644 conf/howler-rsyslog.conf \
    %{buildroot}%{_sysconfdir}/rsyslog.d/howler.conf

mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
install -m 0644 conf/logrotate.conf \
    %{buildroot}{%_sysconfdir}/logrotate.d/howler.conf

mkdir -p %{buildroot}%{_localstatedir}/lib/howler
mkdir -p %{buildroot}%{_localstatedir}/log/howler


# Install SELinux files
for selinuxvariant in %{selinux_variants}
do
  install -d %{buildroot}%{_datadir}/selinux/${selinuxvariant}
  install -p -m 644 selinux/howler.pp.${selinuxvariant} \
    %{buildroot}%{_datadir}/selinux/${selinuxvariant}/howler.pp
done
/usr/sbin/hardlink -cv %{buildroot}%{_datadir}/selinux

%post -n howler-rsyslog
/sbin/fixfiles -R howler-rsyslog restore || :

%postun -n howler-rsyslog
/sbin/fixfiles -R howler-rsyslog restore %{fixfiles_dirs} || :

%post -n howler-selinux
for selinuxvariant in %{selinux_variants}
do
  /usr/sbin/semodule -s ${selinuxvariant} -i \
    %{_datadir}/selinux/${selinuxvariant}/howler.pp &> /dev/null || :
done
/sbin/fixfiles -R python-howler restore || :

%postun -n howler-selinux
if [ $1 -eq 0 ] ; then
  for selinuxvariant in %{selinux_variants}
  do
    /usr/sbin/semodule -s ${selinuxvariant} -r howler &> /dev/null || :
  done
  /sbin/fixfiles -R python-howler restore %{fixfiles_dirs} || :
fi


%files
%doc COPYING README.rst
%config %dir %{_sysconfdir}/howler
%config(noreplace) %{_sysconfdir}/howler/howler.ini
%config(noreplace) %{_sysconfdir}/cron.daily/*
%config(noreplace) %{_sysconfdir}/logrotate.d/howler.conf
%{python_sitelib}
%{_bindir}/howler
%{_localstatedir}/lib/howler
%{_localstatedir}/log/howler

%files -n howler-rsyslog
%config(noreplace) %{_sysconfdir}/rsyslog.d/*
%config(noreplace) %{_sysconfdir}/howler/syslog-regexes
%{_bindir}/howler-syslog-helper

%files -n howler-selinux
%defattr(-,root,root,0755)
%doc selinux/*.{fc,if,te}
%{_datadir}/selinux/*/howler.pp


%changelog
* Fri Sep 13 2013 Konstantin Ryabitsev <mricon@kernel.org>
- Preliminary 0.3 release with new features.

* Sun Jun 16 2013 Rene Cunningham <rene@linuxfoundation.org>
- Run fixfiles for howler-rsyslog.

* Thu Nov 08 2012 Konstantin Ryabitsev <mricon@kernel.org>
- Update to 0.2 and split into subpackages.
- Add selinux subpackage.

* Tue Nov 06 2012 Konstantin Ryabitsev <mricon@kernel.org>
- Initial spec file.
