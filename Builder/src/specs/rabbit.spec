%global realversion 3.5.4
%global realname rabbitmq-server
%global rpmversion <rpm.version>
%global packager <ericsson.rstate>
%define debug_package %{nil}
%if 0%{?rhel} >= 7
%global _with_systemd 1
%else
%global _with_systemd 0
%endif
Name: EXTRlitprabbitmqserver_CXP9031043
Version: %{rpmversion}
Release: 1%{?dist}
License: MPLv1.1 and MIT and ASL 2.0 and BSD
Source0: %{realname}-%{realversion}.tar.gz
Source1: rabbitmq-server.init
Source2: rabbitmq-script-wrapper
Source3: rabbitmq-server.logrotate
Source4: rabbitmq-server.ocf
Source5: rabbitmq-server.service
Source6: rabbitmq-server.sh

URL: http://www.rabbitmq.com/
BuildArch: noarch
# This used to include python-simplejson - but that was only used to support
# building with Python older than 2.6, so we've removed it.
BuildRequires: xmlto, libxslt, gzip, sed, zip, rsync
Requires: erlang >= R16B-03, logrotate
Summary: The RabbitMQ server
BuildRoot: %{_tmppath}/%{realname}-%{realversion}-%{release}-%{_arch}-root
Provides: %{realname} = %{realversion}
Provides: config(%{realname}) = %{realversion}
Packager: %{packager}

%description
RabbitMQ 3.5.4 repackaged by Ericsson from Pivotal Software source code.

RabbitMQ is an implementation of AMQP, the emerging standard for high
performance enterprise messaging. The RabbitMQ server is a robust and
scalable implementation of an AMQP broker.


# We want to install into /usr/lib, even on 64-bit platforms
%define _rabbit_libdir %{_libdir}/rabbitmq
%define _rabbit_erllibdir %{_rabbit_libdir}/lib/rabbitmq_server-%{realversion}
%define _rabbit_wrapper %{_builddir}/`basename %{S:2}`
%define _rabbit_server_ocf %{_builddir}/`basename %{S:4}`
%define _plugins_state_dir %{_localstatedir}/lib/rabbitmq/plugins
%define _maindir %{buildroot}%{_rabbit_erllibdir}


%prep
%setup -q -n %{realname}-%{realversion}

%build
cp %{S:2} %{_rabbit_wrapper}
cp %{S:4} %{_rabbit_server_ocf}
make %{?_smp_mflags}

%install
rm -rf %{buildroot}

make install TARGET_DIR=%{_maindir} \
             SBIN_DIR=%{buildroot}%{_rabbit_libdir}/bin \
             MAN_DIR=%{buildroot}%{_mandir}

mkdir -p %{buildroot}%{_localstatedir}/lib/rabbitmq/mnesia
mkdir -p %{buildroot}%{_localstatedir}/log/rabbitmq

#Copy all necessary lib files etc.
sed -i 's|@SU_RABBITMQ_SH_C@|su rabbitmq -s /bin/sh -c|' %{_rabbit_wrapper}
sed -i 's|/usr/lib/|%{_libdir}/|' %{_rabbit_wrapper}
%if %{_with_systemd}
install -p -D -m 0644 %{S:5} %{buildroot}%{_unitdir}/rabbitmq-server.service
install -p -D -m 0755 %{S:6} %{buildroot}/usr/local/bin/rabbitmq-server.sh
%else
install -p -D -m 0755 %{S:1} %{buildroot}%{_initrddir}/rabbitmq-server
%endif
install -p -D -m 0755 %{_rabbit_wrapper} %{buildroot}%{_sbindir}/rabbitmqctl
install -p -D -m 0755 %{_rabbit_wrapper} %{buildroot}%{_sbindir}/rabbitmq-server
install -p -D -m 0755 %{_rabbit_wrapper} %{buildroot}%{_sbindir}/rabbitmq-plugins
install -p -D -m 0755 %{_rabbit_server_ocf} %{buildroot}%{_exec_prefix}/lib/ocf/resource.d/rabbitmq/rabbitmq-server

install -p -D -m 0644 %{S:3} %{buildroot}%{_sysconfdir}/logrotate.d/rabbitmq-server

mkdir -p %{buildroot}%{_sysconfdir}/rabbitmq

rm %{_maindir}/LICENSE %{_maindir}/LICENSE-MPL-RabbitMQ %{_maindir}/INSTALL

#Build the list of files
echo '%defattr(-,root,root, -)' >%{_builddir}/%{realname}.files
find %{buildroot} -path %{buildroot}%{_sysconfdir} -prune -o '!' -type d -printf "/%%P\n" >>%{_builddir}/%{name}.files

%pre

# create rabbitmq group
if ! getent group rabbitmq >/dev/null; then
        groupadd -r rabbitmq
fi

# create rabbitmq user
if ! getent passwd rabbitmq >/dev/null; then
        useradd -r -g rabbitmq -d %{_localstatedir}/lib/rabbitmq -s /bin/nologin rabbitmq \
            -c "RabbitMQ messaging server"
fi

%post
%if %{_with_systemd}
/usr/bin/systemctl enable %{realname}
%else
/sbin/chkconfig --add %{realname}
%endif
if [ -f %{_sysconfdir}/rabbitmq/rabbitmq.conf ] && [ ! -f %{_sysconfdir}/rabbitmq/rabbitmq-env.conf ]; then
    mv %{_sysconfdir}/rabbitmq/rabbitmq.conf %{_sysconfdir}/rabbitmq/rabbitmq-env.conf
fi
chmod -R o-rwx,g-w %{_localstatedir}/lib/rabbitmq/mnesia
chown -R rabbitmq:rabbitmq %{_localstatedir}/lib/rabbitmq/mnesia

if [ $1 -ge 2 ]; then
  if [ "$(getent passwd rabbitmq | awk -F: '{print $NF}')" != "/sbin/nologin" ] ; then
    logger -t "RABBITMQ" -p user.info " postinstall: Updating rabbitmq shell to /sbin/nologin"
    usermod -s /sbin/nologin rabbitmq
  fi

  # Upgrade - conditional restart
  # Our init script doesn't have "condrestart", but it has "try-restart"
  %if %{_with_systemd}
  /usr/bin/systemctl condrestart rabbitmq-server.service ||:
  %else
  /sbin/service rabbitmq-server try-restart ||:
  %endif
fi

%preun
if [ $1 = 0 ]; then
  #Complete uninstall
  %if %{_with_systemd}
  /usr/bin/systemctl stop rabbitmq-server.service
  /usr/bin/systemctl disable rabbitmq-server.service
  %else
  /sbin/service rabbitmq-server stop
  /sbin/chkconfig --del rabbitmq-server
  %endif
  # We do not remove /var/log and /var/lib directories
  # Leave rabbitmq user and group
fi

# Clean out plugin activation state, both on uninstall and upgrade
rm -rf %{_plugins_state_dir}
for ext in rel script boot ; do
    rm -f %{_rabbit_erllibdir}/ebin/rabbit.$ext
done

%files -f ../%{name}.files
%defattr(-,root,root,0755)
%attr(0755, rabbitmq, rabbitmq) %dir %{_localstatedir}/lib/rabbitmq
%attr(0750, rabbitmq, rabbitmq) %dir %{_localstatedir}/lib/rabbitmq/mnesia

%attr(0755, rabbitmq, rabbitmq) %dir %{_localstatedir}/log/rabbitmq
%attr(0755, root, root) %dir %{_sysconfdir}/rabbitmq
%if %{_with_systemd}
%{_unitdir}/rabbitmq-server.service
%else
%{_initrddir}/rabbitmq-server
%endif
%config(noreplace) %{_sysconfdir}/logrotate.d/rabbitmq-server
%doc LICENSE*
%doc README
%doc docs/rabbitmq.config.example

%clean
rm -rf %{buildroot}
