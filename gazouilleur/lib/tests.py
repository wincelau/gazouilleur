#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import stderr
from traceback import format_exc

# Check dependencies
try:
    from gazouilleur.lib.colorize import colorize
    colorize('a', style='bold')
except (ImportError, TypeError) as e:
    stderr.write("ERROR: Could not load module colorize.\nERROR: Something obviously wrong here...\n")
    exit(1)
try:
    import pymongo, txmongo, txmongo.connection, lxml, twisted, twitter, feedparser, pypump, zope.interface, stevedore, urllib3, cffi, cryptography, OpenSSL
except ImportError as e:
    stderr.write(colorize("ERROR: Could not load module%s.\nERROR: Please check your install or run `./bin/update_requirements.sh` to update the dependencies.\n" % str(e).replace('No module named', ''), 'red', style='bold'))
    exit(1)

# Check config.py
try:
    from gazouilleur import config
except ImportError:
    stderr.write(colorize("Could not find `gazouilleur/config.py`.\nERROR: Please run `bash bin/configure.sh` to create it, then edit it to prepare your bot.\n", 'red', style='bold'))
    exit(1)
except SyntaxError as e:
    stderr.write(colorize("Could not read `gazouilleur/config.py`.\nERROR: Please edit it to fix the following syntax issue:\nERROR: %s\n%s\n" % (e, "\n".join(format_exc().splitlines()[-3:-1])), 'red', style='bold'))
    exit(1)

#Load decorator
from gazouilleur.lib.log import logerr

try:
    config.BOTNAME, config.BOTPASS, config.HOST, config.PORT, config.MONGODB, config.GLOBAL_USERS, config.BACK_HOURS, config.COMMAND_CHARACTER, config.CHANNELS, config.DEBUG, config.ADMINS
    [config.MONGODB[k] for k in ['HOST', 'PORT', 'DATABASE', 'USER', 'PSWD']]
except AttributeError as e:
    logerr("Some field is missing from `gazouilleur/config.py`.\nERROR: Please edit it to fix the following issue:\nERROR: %s" % str(e).replace("'module' object", 'config'))
    exit(1)
except KeyError as e:
    logerr("A field is missing from MONGODB config in `gazouilleur/config.py`: %s." % e)
    exit(1)
try:
    assert(len([1 for c in config.CHANNELS.values() if "MASTER" in c and c["MASTER"]]) == 1)
    [c[k] for k in ['USERS', 'DISPLAY_RT'] for c in config.CHANNELS.values()]
except AssertionError:
    logerr("One and only one channel must be set as MASTER in `gazouilleur/config.py`.\nERROR: Please edit it to fix this issue.")
    exit(1)
except KeyError as e:
    logerr("A field is missing from one channel set in `gazouilleur/config.py`: %s." % e)
    exit(1)
try:
    [c['IDENTICA']['USER'] for c in config.CHANNELS.values() if "IDENTICA" in c]
except KeyError:
    logerr("USER field is missing from IDENTICA config in `gazouilleur/config.py`.")
    exit(1)
try:
    [c['TWITTER'][k] for k in ['USER', 'DISPLAY_RT', 'KEY', 'SECRET', 'OAUTH_TOKEN', 'OAUTH_SECRET'] for c in config.CHANNELS.values() if "TWITTER" in c]
except KeyError as e:
    logerr("A field is missing from TWITTER config in `gazouilleur/config.py`: %s." % e)
    exit(1)

try:
    from gazouilleur.lib import ircclient_with_names, irccolors, feeds, filelogger, httpget, log, microblog, mongo, stats, utils, templater
except Exception as e:
    logerr("Oups, looks like something is wrong somewhere in the code, shouldn't be committed...")
    logerr("%s\n%s" % (e, "\n".join(format_exc().splitlines()[-3:-1])))
    exit(1)

# Check plotting dependencies if webstats activated
if hasattr(config, 'URL_STATS'):
    try:
        import pystache, pylab, matplotlib
        import gazouilleur.lib.plots
    except (NameError, ImportError) as e:
        logerr("Could not load module%s.\nERROR: This module is required to activate the Twitter web stats set in URL_STATS in `gazouilleur/config.py`: %s\nERROR: Please check your installl or run `./bin/update_requirements.sh` to update the dependencies.\n" % (str(e).replace('No module named', ''), config.URL_STATS))
        exit(1)

# Check Color Configs
try:
    irccolors.ColorConf(config.FORMAT)
except TypeError as e:
    logerr("Global FORMAT conf is broken in `gazouilleur/config.py`:\n%s" % e)
    exit(1)
except:
    pass
for chan, conf in config.CHANNELS.iteritems():
    if "FORMAT" not in conf:
        continue
    try:
        irccolors.ColorConf(conf['FORMAT'])
    except TypeError as e:
        logerr("Conf FORMAT of channel %s is broken in `gazouilleur/config.py`:\n%s" % (chan, e))
        exit(1)

# Check MongoDB
try:
    db = pymongo.MongoClient(config.MONGODB['HOST'], config.MONGODB['PORT'])[config.MONGODB['DATABASE']]
    assert(db.authenticate(config.MONGODB['USER'], config.MONGODB['PSWD']))
except (pymongo.errors.AutoReconnect, pymongo.errors.ConnectionFailure) as e:
    logerr("MongoDB is unreachable, %s \nERROR: Please check `mongo` is installed and restart it with `sudo /etc/init.d/mongodb restart`\nERROR: You may need to repair your database, run `tail -n 30 /var/log/mongodb/mongodb.log` for more details.\nERROR: Classic cleaning would be: `sudo service mongodb stop; sudo rm /var/lib/mongodb/mongod.lock; sudo -u mongodb mongod --dbpath /var/lib/mongodb --repair --repairpath /var/lib/mongodb/%s; sudo service mongodb start`\n" % (e, config.BOTNAME))
    exit(1)
except (AssertionError, pymongo.errors.OperationFailure) as e:
    logerr("Cannot connect to database %s in MongoDB.\nERROR: Please check the database and its users are created,\nERROR: or run `bash bin/configureDB.sh` to create or update them automatically (or configureDB-mongo3.sh when using MongoDB v3+).\n%s\n" % (config.MONGODB['DATABASE'], e))
    exit(1)

# Check Identi.ca config
if [1 for c in config.CHANNELS.values() if "IDENTICA" in c]:
    try:
        from gazouilleur.identica_auth_config import identica_auth
        [identica_auth[conf['IDENTICA']['USER'].lower()] for conf in config.CHANNELS.values() if "IDENTICA" in conf]
    except (ImportError, KeyError) as e:
        logerr("Could not find `gazouilleur/identica_auth_config.py` with configuration for %s.\nERROR: Please run `python bin/auth_identica.py` to generate your OAuth Identi.ca keys and create it automatically.\n" % e)
        exit(1)
from gazouilleur.lib.microblog import Microblog
for chan, conf in config.CHANNELS.iteritems():
    if "IDENTICA" not in conf:
        continue
    conn = Microblog("identica", conf)
    try:
        from urllib2 import urlopen
        urlopen("https://identi.ca", timeout=15)
        if not conn.ping():
            logerr("Cannot connect to Identi.ca with the auth configuration provided in `gazouilleur/identica_auth_config.py` for channel %s and user @%s.\nERROR: Please rerun `python bin/auth_identica.py` to generate your OAuth Identi.ca keys.\n" % (chan, conf["IDENTICA"]["USER"].lower()))
            exit(1)
    except:
        stderr.write(colorize("WARNING: Identi.ca seems down, bypassing related tests.\n", 'red', style='bold'))

# Check Twitter config
for chan, conf in config.CHANNELS.iteritems():
    if "TWITTER" not in conf:
        continue
    conn = Microblog("twitter", conf)
    if not conn.ping():
        logerr("Cannot connect to Twitter with the auth configuration provided in `gazouilleur/config.py` for channel %s and user @%s.\nERROR: Please check you properly set the 4 auth fields and gave \"Read, write, and direct messages\" rights to gazouilleur's app on https://dev.twitter.com and wait at most 15 minutes\n" % (chan, conf["TWITTER"]["USER"]))
        exit(1)

# Check IRC server
from twisted.internet import reactor, protocol, ssl
from twisted.words.protocols.irc import IRCClient

class IRCBotTest(IRCClient):
    def connectionMade(self):
        self.factory.doStop()
class IRCBotTester(protocol.ClientFactory):
    protocol = IRCBotTest
    def clientConnectionFailed(self, connector, reason):
        self.doStop()
        logerr("Cannot connect to IRC server %s on port %d: %s.\nERROR: Please check your configuration in `gazouilleur/config.py`.\n" % (config.HOST, config.PORT, reason.getErrorMessage()))
        reactor.stop()

if utils.is_ssl(config):
    d = reactor.connectSSL(config.HOST, config.PORT, IRCBotTester(), ssl.ClientContextFactory())
else:
    d = reactor.connectTCP(config.HOST, config.PORT, IRCBotTester())
