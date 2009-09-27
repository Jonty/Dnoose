#!/usr/bin/python

from twisted.application import service, internet
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.names import client, server, dns, error
from twisted.python import failure
import ConfigParser, sys, re

class DNSResolver(client.Resolver):
    def filterAnswers(self, message):
        if message.trunc:
            return self.queryTCP(message.queries).addCallback(self.filterAnswers)
        if message.rCode != dns.OK:
            return failure.Failure(self._errormap.get(message.rCode, error.DNSUnknownError)(message))

        if len(message.queries):
            query = message.queries[0].name.name
            print "Resolve request for '%s'" % (query)

            for name in self.names:
                if re.match(name['name'], query):
                    print "Matched '%s' with '%s', returning '%s'" % (query, name['name'], name['ip'])

                    for i in range(len(message.answers)):
                        if isinstance(message.answers[i].payload, dns.Record_A):
                            message.answers[i].payload = dns.Record_A(name['ip'], 1)
                    break

        return (message.answers, message.authority, message.additional)



try:
    config = ConfigParser.ConfigParser()
    config.read(('dnoose.conf', '/etc/dnoose.conf'))
    nameserver = config.get('dnoose', 'nameserver')

    names = []
    for line in config.get('dnoose', 'rewrite').split(","):
        if len(line.strip()):
            bits = [bit.strip() for bit in line.split("=")]
            name = {'name': bits[0], 'ip': bits[1]}
            names.append(name)

except ConfigParser.NoSectionError:
    print "Missing Dnoose section in dnoose.conf"
    sys.exit(-1)


dnsResolver = DNSResolver(servers = [(nameserver, 53)])
dnsResolver.names = names

serverFactory = server.DNSServerFactory(clients = [dnsResolver])
dnsProtocol = dns.DNSDatagramProtocol(serverFactory)

reactor.listenUDP(53, dnsProtocol)
reactor.run()
