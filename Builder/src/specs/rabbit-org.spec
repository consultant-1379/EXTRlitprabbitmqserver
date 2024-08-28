%global realversion 3.2.3
%global realname rabbitmq-server
%global rpmversion <rpm.version>
%define debug_package %{nil}

Name: EXTRlitprabbitmqserver_CXP9031043
Version: %{rpmversion}
Release: 1%{?dist}
License: MPLv1.1 and MIT and ASL 2.0 and BSD
Source: %{realname}-%{realversion}.tar.gz
Source1: rabbitmq-server.init
Source2: rabbitmq-script-wrapper
Source3: rabbitmq-server.logrotate
Source4: rabbitmq-server.ocf
Source5: README
Source6: Makefile 
Source7: rabbitmqctl
Source8: rabbitmq-server
URL: http://www.rabbitmq.com/
BuildArch: noarch
Requires: erlang >= R13B-03, logrotate
Summary: The RabbitMQ server
BuildRoot: %{_tmppath}/%{realname}-%{realversion}-%{release}-%{_arch}-root
Provides: %{realname} = %{realversion}
Provides: config(%{realname}) = %{realversion}
Packager: Ericsson AB

%description
RabbitMQ is an implementation of AMQP, the emerging standard for high
performance enterprise messaging. The RabbitMQ server is a robust and
scalable implementation of an AMQP broker.

# We want to install into /usr/lib, even on 64-bit platforms
%define _rabbit_libdir %{_exec_prefix}/lib/rabbitmq
%define _rabbit_erllibdir %{_rabbit_libdir}/lib/rabbitmq_server-%{realversion}
%define _rabbit_wrapper %{_builddir}/`basename %{S:2}`
%define _rabbit_server_ocf %{_builddir}/`basename %{S:4}`
%define _plugins_state_dir %{_localstatedir}/lib/rabbitmq/plugins


%define _maindir %{buildroot}%{_rabbit_erllibdir}


%prep
%setup -q -n %{realname}-%{realversion} 
cp %{S:6} %{_builddir}/%{realname}-%{realversion}/Makefile

%build
cp %{S:2} %{_rabbit_wrapper}
cp %{S:4} %{_rabbit_server_ocf}
cp %{S:5} %{_builddir}/%{realname}-%{realversion}/README
make %{?_smp_mflags}

%install
rm -rf %{buildroot}

# Note that we pass /tmp to DOC_INSTALL_DIR here because we're using %doc
# to actually install rabbitmq.config.example, so this is just a fake/temp path
make install TARGET_DIR=%{_maindir} \
             SBIN_DIR=%{buildroot}%{_rabbit_libdir}/bin \
             MAN_DIR=%{buildroot}%{_mandir} \
             DOC_INSTALL_DIR=/tmp

mkdir -p %{buildroot}%{_localstatedir}/lib/rabbitmq/mnesia
mkdir -p %{buildroot}%{_localstatedir}/log/rabbitmq

#Copy all necessary lib files etc.
install -p -D -m 0755 %{S:1} %{buildroot}%{_initrddir}/rabbitmq-server
install -p -D -m 0755 %{S:7} %{buildroot}%{_sbindir}/rabbitmqctl
install -p -D -m 0755 %{S:8} %{buildroot}%{_sbindir}/rabbitmq-server
install -p -D -m 0755 %{_rabbit_wrapper} %{buildroot}%{_sbindir}/rabbitmq-plugins
install -p -D -m 0755 %{_rabbit_server_ocf} %{buildroot}%{_exec_prefix}/lib/ocf/resource.d/rabbitmq/rabbitmq-server

install -p -D -m 0644 %{S:3} %{buildroot}%{_sysconfdir}/logrotate.d/rabbitmq-server

mkdir -p %{buildroot}%{_sysconfdir}/rabbitmq

rm %{_maindir}/LICENSE %{_maindir}/LICENSE-MPL-RabbitMQ %{_maindir}/INSTALL

#Build the list of files
echo '%defattr(-,root,root, -)' >%{_builddir}/%{realname}.files
find %{buildroot} -path %{buildroot}%{_sysconfdir} -prune -o '!' -type d -printf "/%%P\n" >>%{_builddir}/%{realname}.files

%pre

if [ $1 -gt 1 ]; then
  # Upgrade - stop previous instance of rabbitmq-server init.d script
  /sbin/service rabbitmq-server stop
fi

# create rabbitmq group
if ! getent group rabbitmq >/dev/null; then
        groupadd -r rabbitmq
fi

# create rabbitmq user
if ! getent passwd rabbitmq >/dev/null; then
        useradd -r -g rabbitmq -d %{_localstatedir}/lib/rabbitmq rabbitmq \
            -c "RabbitMQ messaging server"
fi

%post
/sbin/chkconfig --add %{realname}
if [ -f %{_sysconfdir}/rabbitmq/rabbitmq.conf ] && [ ! -f %{_sysconfdir}/rabbitmq/rabbitmq-env.conf ]; then
    mv %{_sysconfdir}/rabbitmq/rabbitmq.conf %{_sysconfdir}/rabbitmq/rabbitmq-env.conf
fi

%preun
if [ $1 = 0 ]; then
  #Complete uninstall
  /sbin/service rabbitmq-server stop
  /sbin/chkconfig --del rabbitmq-server
  
  # We do not remove /var/log and /var/lib directories
  # Leave rabbitmq user and group
fi

# Clean out plugin activation state, both on uninstall and upgrade
rm -rf %{_plugins_state_dir}
for ext in rel script boot ; do
    rm -f %{_rabbit_erllibdir}/ebin/rabbit.$ext
done

%files -f ../%{realname}.files
%defattr(-,root,root,-)
%attr(0755, rabbitmq, rabbitmq) %dir %{_localstatedir}/lib/rabbitmq
%attr(0755, rabbitmq, rabbitmq) %dir %{_localstatedir}/log/rabbitmq
%dir %{_sysconfdir}/rabbitmq
%{_initrddir}/rabbitmq-server
%config(noreplace) %{_sysconfdir}/logrotate.d/rabbitmq-server
%doc LICENSE*
%doc README
%doc docs/rabbitmq.config.example

%clean
rm -rf %{buildroot}
