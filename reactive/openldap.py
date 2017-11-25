from charms.reactive import when, when_not, set_state, hook

from charms import layer
from charms.layer import tls_client

from charmhelpers import fetch

from charmhelpers.core import hookenv
from charmhelpers.core import host

import subprocess
import os
import shutil
import socket

from ldap3 import Server, Connection, SASL, EXTERNAL, MODIFY_REPLACE


def debconf_set_selections(line):
    subprocess.run("debconf-set-selections",
                   input=line.encode('utf-8'),
                   shell=True, check=True)


@hook('install')
def install():
    config = hookenv.config()
    # set debconf selections so that slapd is installed with pre-set
    # configuration as usage of config files is deprecated and it
    # uses a config tree instead
    passwd = config['password']
    debconf_set_selections("slapd slapd/password1 password %s" % passwd)
    debconf_set_selections("slapd slapd/password2 password %s" % passwd)
    debconf_set_selections("slapd shared/organization string %s" %
                           config['organization'])
    debconf_set_selections("slapd slapd/domain string %s" %
                           config['domain'])


@when_not('openldap.installed')
@when('apt.installed.slapd')
@when('apt.installed.ldap-utils')
def install_openldap():
    set_state('openldap.installed')

    tls_dir = layer.options('openldap')['tls-dir']
    os.mkdir(tls_dir, mode=0o640)
    shutil.chown(tls_dir, user='openldap', group='openldap')

    hookenv.status_set('active', 'openldap is installed')


@when('certificates.available')
def send_data(tls):
    '''Send the data that is required to create a server certificate for
    this server.'''
    # Use the public ip of this unit as the Common Name for the certificate.
    common_name = hookenv.unit_public_ip()

    # Create SANs that the tls layer will add to the server cert.
    sans = [
        hookenv.unit_public_ip(),
        hookenv.unit_private_ip(),
        # TODO: add network-gets for all provides
        socket.gethostname(),
    ]

    # any extra subject alternative names (SANs)
    extra_sans = hookenv.config('extra_sans')
    if extra_sans and not extra_sans == "":
        sans.extend(extra_sans.split())

    # Create a path safe name by removing path characters from the unit name.
    certificate_name = hookenv.local_unit().replace('/', '_')
    # Request a server cert with this information.
    tls.request_server_cert(common_name, sans, certificate_name)


@when('config.changed.extra_sans', 'certificates.available')
def update_certificate(tls):
    # Using the config.changed.extra_sans flag to catch changes.
    # IP changes will take ~5 minutes or so to propagate, but
    # it will update.
    send_data(tls)


@when('openldap.installed',
      'certificates.server.cert.available',
      'certificates.ca.available',
      'tls_client.server.certificate.written')
def configure_tls(tls, tlsc):
    hookenv.log('Configuring slapd TLS')
    hookenv.status_set('maintenance', 'Configuring TLS via olc')
    # ldap group should be able to read the private key
    # certificates are public information hence are untouched
    tls_options = layer.options('tls-client')
    srv_key = tls_options.get('server_key_path')
    srv_cert = tls_options.get('server_certificate_path')
    ca_cert = tls_options.get('ca_certificate_path')
    hookenv.log('Changing owner for the server key')

    for f in [srv_key, srv_cert, ca_cert]:
        shutil.chown(f, user='openldap', group='openldap')
        os.chmod(f, 0o640)

    s = Server('ldapi:///var/run/slapd/ldapi')

    hookenv.log('Connecting to slapd over a unix socket')

    c = Connection(s, authentication=SASL, sasl_mechanism=EXTERNAL,
                   sasl_credentials='')
    if not c.bind():
        raise Exception("Unable to bind to a local slapd server")

    hookenv.log('Modifying TLS config entries in via olc')
    # configure openldap via olc (OnLine Configuration)
    res = c.modify('cn=config',
             {
                 'olcTLSCACertificateFile':
                 [(MODIFY_REPLACE, [ca_cert])],
                 'olcTLSCertificateFile':
                 [(MODIFY_REPLACE, [srv_cert])],
                 'olcTLSCertificateKeyFile':
                 [(MODIFY_REPLACE, [srv_key])],
             })

    if not res:
        raise Exception('Failed to configure TLS options via olc')

    tls_client.reset_certificate_write_flag('server')

    hookenv.status_set('active', 'slapd is configured')
