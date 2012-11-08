#!/usr/bin/python -tt
# Copyright (C) 2012 by The Linux Foundation and contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys

import datetime

HOWLER_VERSION = '0.1'
DBVERSION      = 1

def connect_last_seen(config):
    import anydbm
    last_seen_path = os.path.abspath(os.path.join(config['dbdir'],
                                     'last_seen.db'))
    last_seen = anydbm.open(last_seen_path, 'c')
    return last_seen

def connect_locations(config):
    import sqlite3
    # open sqlite db, creating it if we need to
    locations_db_path = os.path.abspath(os.path.join(config['dbdir'],
                                        'locations.sqlite'))

    if not os.path.exists(locations_db_path):
        # create the database
        sconn   = sqlite3.connect(locations_db_path)
        scursor = sconn.cursor()

        query = """CREATE TABLE locations (
                          userid    TEXT,
                          location  TEXT,
                          last_seen DATE DEFAULT CURRENT_DATE,
                          not_after DATE DEFAULT NULL)"""
        scursor.execute(query)

        query = """CREATE TABLE meta (
                          dbversion INTEGER
                          )"""
        scursor.execute(query)
        query = "INSERT INTO meta (dbversion) VALUES (%d)" % DBVERSION
        scursor.execute(query)
        sconn.commit()
    else:
        sconn   = sqlite3.connect(locations_db_path)

    return sconn

def get_geoip_crc(config, ipaddr):
    import GeoIP
    # Open the GeoIP database and perform the lookup
    if os.path.exists(config['geoipcitydb']):
        gi    = GeoIP.open(config['geoipcitydb'], GeoIP.GEOIP_STANDARD)
        ginfo = gi.record_by_addr(ipaddr)

        if not ginfo:
            return None

        city = region_name = country_code = 'Unknown'

        if ginfo['city'] is not None:
            city = unicode(ginfo['city'], 'iso-8859-1')
        if ginfo['region_name'] is not None:
            region_name = unicode(ginfo['region_name'], 'iso-8859-1')
        if ginfo['country_code'] is not None:
            country_code = unicode(ginfo['country_code'], 'iso-8859-1')

        crc = u'%s, %s, %s' % (city, region_name, country_code)

    else:
        gi  = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
        crc = unicode(gi.country_code_by_addr(ipaddr), 'iso-8859-1')
        if not crc:
            return None

    return crc

def not_after(config, userid, ipaddr, not_after):
    crc = get_geoip_crc(config, ipaddr)

    sconn = connect_locations(config)
    scursor = sconn.cursor()
    query = """UPDATE locations SET not_after = ?
                WHERE userid = ?
                  AND location = ?"""
    scursor.execute(query, (not_after, userid, crc))
    sconn.commit()
    if config['verbose']:
        print '"%s" updated to expire on %s for %s' % (crc, not_after, userid)
    return

def check(config, userid, ipaddr, hostname=None, daemon=None):
    # check if it's a user we should ignore
    if 'ignoreusers' in config.keys():
        ignoreusers = config['ignoreusers'].split(',')
        for ignoreuser in ignoreusers:
            if ignoreuser.strip() == userid:
                return

    # Check if the IP has changed since last login.
    # the last_seen database is anydbm, because it's fast
    last_seen = connect_last_seen(config)

    if userid in last_seen.keys():
        if last_seen[userid] == ipaddr:
            if config['verbose']:
                print 'Quick out: %s last seen from %s' % (userid, ipaddr)
            return

    # Record the last_seen ip
    last_seen[userid] = ipaddr
    last_seen.close()

    crc = get_geoip_crc(config, ipaddr)

    if crc is None:
        if config['verbose']:
            print 'GeoIP City database did not return anything for %s' % ipaddr
        return

    if config['verbose']:
        print 'Location: %s' % crc

    sconn = connect_locations(config)
    scursor = sconn.cursor()

    query = """SELECT location, last_seen
                 FROM locations
                WHERE userid = ?
             ORDER BY last_seen DESC"""

    locations = []
    for row in scursor.execute(query, (userid,)):
        if row[0] == crc:
            if config['verbose']:
                print 'This location already seen on %s' % row[1]
            # Update last_seen
            query = """UPDATE locations
                          SET last_seen = CURRENT_DATE
                        WHERE userid = ?
                          AND location = ?"""
            scursor.execute(query, (userid, crc))
            sconn.commit()
            return

        locations.append(row)

    # If we got here, this location either has not been seen before,
    # or this is a new user that we haven't seen before. Either way, start
    # by recording the new data.
    query = """INSERT INTO locations (userid, location)
                              VALUES (?, ?)"""
    scursor.execute(query, (userid, crc))
    sconn.commit()
    sconn.close()

    if len(locations) == 0:
        # New user. Finish up if we don't notify about new users
        if not config['alertnew']:
            if config['verbose']:
                print 'Quietly added new user %s' % userid
            return
        if config['verbose']:
            print 'Added new user %s' % userid

    # Now proceed to howling
    body = (u"This user logged in from a new location:\n\n" +
            u"\tUser    : %s\n" % userid +
            u"\tIP Addr : %s\n" % ipaddr +
            u"\tLocation: %s\n" % crc)

    if hostname is not None:
        body += u"\tHostname: %s\n" % hostname
    if daemon is not None:
        body += u"\tDaemon  : %s\n" % daemon

    if len(locations):
        body += u"\nPreviously seen locations for this user:\n"
        for row in locations:
            body += u"\t%s: %s\n" % (row[1], row[0])

    body += u"\n\n-- \nBrought to you by howler %s\n" % HOWLER_VERSION

    if config['verbose']:
        print body

    # send mail
    from email.mime.text import MIMEText
    from subprocess import Popen, PIPE

    msg = MIMEText(body, 'plain', 'utf-8')

    msg['From']    = config['mailfrom']
    msg['Subject'] = u'New login by %s from %s' % (userid, crc)
    msg['To']      = config['mailto']

    if config['verbose']:
        print 'Sending mail to %s' % config['mailto']

    try:
        p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
        p.communicate(msg.as_string())
    except Exception, ex:
        print 'Sending mail failed: %s' % ex

def cleanup(config):
    sconn   = connect_locations(config)
    scursor = sconn.cursor()

    # Delete all entries that are older than staledays
    staledays = int(config['staledays'])
    dt = datetime.datetime.now() - datetime.timedelta(days=staledays)
    query = """DELETE FROM locations
                     WHERE last_seen < ?"""
    scursor.execute(query, (dt.strftime('%Y-%m-%d'),))

    # Delete all entries where not_after is before today
    query = """DELETE FROM locations
                     WHERE not_after < CURRENT_DATE """
    scursor.execute(query)
    sconn.commit()

    # Now get all userids and entries from last_seen.db that no longer have
    # a matching userid in locations.sqlite
    query = """SELECT DISTINCT userid FROM locations"""
    cleaned_userids = []
    for row in scursor.execute(query):
        cleaned_userids.append(row[0])
    sconn.close()

    last_seen = connect_last_seen(config)
    for userid in last_seen.keys():
        if userid not in cleaned_userids:
            del(last_seen[userid])

    last_seen.close()

