# openldap

This charm provides a way to deploy OpenLDAP.

OpenLDAP is a free, open source implementation of the Lightweight Directory
Access Protocol (LDAP) developed by the OpenLDAP Project.

OpenLDAP has three main components:

* slapd – stand-alone LDAP daemon and associated modules and tools
* libraries implementing the LDAP protocol and ASN.1 Basic Encoding Rules (BER)
* client software: ldapsearch, ldapadd, ldapdelete, and others

Slapd is the stand-alone LDAP daemon. It listens for LDAP connections on any
number of ports (389 by default), responding to the LDAP operations it receives
over these connections.

From the data storage perspective slapd provides a [hierarchical database](http://www.openldap.org/doc/admin24/intro.html#LDAP%20vs%20RDBMS)
which means that it does not rely on a relational model and is more suitable to
provide storage for tree-like data structures with custom attributes, values and
inheritance.

# Usage

Step by step instructions on using the charm:

juju deploy openldap

## Limitations

For now only a standalone slapd is deployed without an ability to configure replication.

# Contact Information

Please contact dima{at}canonical.com if you have any questions about this code.

This charm is free an open source and is not officially supported by Canonical.

# Additional information

For more information please visit http://www.openldap.org
