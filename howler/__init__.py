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

import logging

import datetime
import GeoIP

HOWLER_VERSION = '0.3'
DBVERSION      = 1

# Use this to track our global geoip db connection
gi = None

logger = logging.getLogger(__name__)

# Code taken from http://www.johndcook.com/python_longitude_latitude.html
# It is in the public domain
def distance_on_unit_sphere(lat1, long1, lat2, long2):
    import math

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = math.pi/180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians

    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians

    # Compute spherical distance from spherical coordinates.
    # For two locations in spherical coordinates
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) =
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length

    cos = (math.sin(phi1)*math.sin(phi2)*math.cos(theta1 - theta2) +
           math.cos(phi1)*math.cos(phi2))
    arc = math.acos( cos )

    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return arc

def connect_geoip(dbpath):
    global gi
    if gi is not None:
        return gi

    # Open the GeoIP database and perform the lookup
    if os.path.exists(dbpath):
        logger.debug('Opening geoip db in %s' % dbpath)
        gi = GeoIP.open(dbpath, GeoIP.GEOIP_STANDARD)
    else:
        logger.debug('%s does not exist, using basic geoip db' % dbpath)
        gi = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)

    return gi

def connect_last_seen(dbdir):
    import anydbm
    last_seen_path = os.path.abspath(os.path.join(dbdir, 'last_seen.db'))
    last_seen = anydbm.open(last_seen_path, 'c')
    return last_seen

def connect_locations(dbdir):
    import sqlite3
    # open sqlite db, creating it if we need to
    locations_db_path = os.path.abspath(os.path.join(dbdir, 'locations.sqlite'))

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

def get_distance_between_ips(gi, ipaddr1, ipaddr2):
    logger.debug('Calculating distance between %s and %s' % (ipaddr1, ipaddr2))
    rec1 = gi.record_by_addr(ipaddr1)
    if not rec1 or 'longitude' not in rec1.keys():
        logger.debug('No long/lat information for IP %s' % ipaddr1)
        return None

    rec2 = gi.record_by_addr(ipaddr2)
    if not rec2 or 'longitude' not in rec2.keys():
        logger.debug('No long/lat information for IP %s' % ipaddr2)
        return None

    dist = distance_on_unit_sphere(
            rec1['latitude'],
            rec1['longitude'],
            rec2['latitude'],
            rec2['longitude'])
    distkm = int(dist*6373)
    logger.info('Distance between %s and %s is %s km' % 
            (ipaddr1, ipaddr2, distkm))
    return distkm

def get_geoip_crc(gi, ipaddr):
    ginfo = gi.record_by_addr(ipaddr)

    if ginfo is not None:
        city = region_name = country_code = 'Unknown'

        if ginfo['city'] is not None:
            city = unicode(ginfo['city'], 'iso-8859-1')
        if ginfo['region_name'] is not None:
            region_name = unicode(ginfo['region_name'], 'iso-8859-1')
        if ginfo['country_code'] is not None:
            country_code = unicode(ginfo['country_code'], 'iso-8859-1')

        crc = u'%s, %s, %s' % (city, region_name, country_code)

    else:
        # try just the country code, then
        crc = unicode(gi.country_code_by_addr(ipaddr), 'iso-8859-1')
        if not crc:
            return None

    return crc

def not_after(config, userid, ipaddr, not_after):
    gi = connect_geoip(config['geoipcitydb'])
    crc = get_geoip_crc(gi, ipaddr)

    sconn = connect_locations(config['dbdir'])
    scursor = sconn.cursor()
    query = """UPDATE locations SET not_after = ?
                WHERE userid = ?
                  AND location = ?"""
    scursor.execute(query, (not_after, userid, crc))
    sconn.commit()
    logger.info('"%s" updated to expire on %s for %s' % (crc, not_after, userid))
    return

def check(config, userid, ipaddr, hostname=None, daemon=None, sendmail=True):
    # check if it's a user we should ignore
    logger.info('Checking: userid=%s, ipaddr=%s' % (userid, ipaddr))
    if 'ignoreusers' in config.keys():
        ignoreusers = config['ignoreusers'].split(',')
        for ignoreuser in ignoreusers:
            if ignoreuser.strip() == userid:
                logger.info('Quick out: %s in ignore list' % userid)
                return None

    # Check if the IP has changed since last login.
    # the last_seen database is anydbm, because it's fast
    last_seen = connect_last_seen(config['dbdir'])

    prev_ipaddr = None
    if userid in last_seen.keys():
        prev_ipaddr = last_seen[userid]
        if prev_ipaddr == ipaddr:
            logger.info('Quick out: %s last seen from %s' % (userid, ipaddr))
            return None

    if 'ignorelocations' in config.keys() and len(config['ignorelocations']):
        for entry in config['ignorelocations'].split('\n'):
            if crc == entry.strip():
                logger.info('Quick out: %s in ignored locations' % crc)
                return

    gi = connect_geoip(config['geoipcitydb'])

    # Record the last_seen ip
    last_seen[userid] = ipaddr
    last_seen.close()

    if 'mindistance' in config.keys() and prev_ipaddr is not None:
        # calculate distance between previous and new ips
        dist = get_distance_between_ips(gi, prev_ipaddr, ipaddr)
        if dist is not None and dist < int(config['mindistance']):
            logger.info('Distance between IPs less than %s km, ignoring'
                    % config['mindistance'])
            return None

    crc = get_geoip_crc(gi, ipaddr)

    if crc is None:
        logger.info('GeoIP City database did not return anything for %s'
                    % ipaddr)
        return None

    logger.info('Location: %s' % crc)

    sconn = connect_locations(config['dbdir'])
    scursor = sconn.cursor()

    query = """SELECT location, last_seen
                 FROM locations
                WHERE userid = ?
             ORDER BY last_seen DESC"""

    locations = []
    for row in scursor.execute(query, (userid,)):
        if row[0] == crc:
            logger.info('This location already seen on %s' % row[1])
            # Update last_seen
            query = """UPDATE locations
                          SET last_seen = CURRENT_DATE
                        WHERE userid = ?
                          AND location = ?"""
            scursor.execute(query, (userid, crc))
            sconn.commit()
            return None

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
        if config['alertnew'] != 'True':
            logger.info('Quietly added new user %s' % userid)
            return None
        logger.info('Added new user %s' % userid)
    else:
        logger.info('Added new location for user %s' % userid)

    retval = {
            'location': crc,
            'previous': locations,
            }

    if 'mailto' not in config.keys() or not len(config['mailto']):
        return retval

    if not sendmail:
        logger.info('Not sending mail, as requested.')
        return retval

    body = (u"This user logged in from a new location:\n\n" +
            u"\tUser    : %s\n" % userid +
            u"\tIP Addr : %s\n" % ipaddr +
            u"\tLocation: %s\n" % crc)

    # Try to lookup whois info if cymruwhois is available
    try:
        import cymruwhois
        cym = cymruwhois.Client()
        res = cym.lookup(ipaddr)
        if res.owner and res.cc:
            body += u"\tIP Owner: %s/%s\n" % (res.owner, res.cc)
    except:
        pass

    if hostname is not None:
        body += u"\tHostname: %s\n" % hostname
    if daemon is not None:
        body += u"\tDaemon  : %s\n" % daemon

    if len(locations):
        body += u"\nPreviously seen locations for this user:\n"
        for row in locations:
            body += u"\t%s: %s\n" % (row[1], row[0])

    body += u"\n\n-- \nBrought to you by howler %s\n" % HOWLER_VERSION

    logger.debug('Message body follows')
    logger.debug(body)

    # send mail
    from email.mime.text import MIMEText
    from subprocess import Popen, PIPE

    msg = MIMEText(body, 'plain', 'utf-8')

    msg['From']    = config['mailfrom']
    msg['Subject'] = u'New login by %s from %s' % (userid, crc)
    msg['To']      = config['mailto']

    logger.info('Sending mail to %s' % config['mailto'])

    try:
        p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
        p.communicate(msg.as_string())
    except Exception, ex:
        print 'Sending mail failed: %s' % ex

    return retval

def cleanup(config):
    sconn   = connect_locations(config['dbdir'])
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

    last_seen = connect_last_seen(config['dbdir'])
    for userid in last_seen.keys():
        if userid not in cleaned_userids:
            del(last_seen[userid])

    last_seen.close()

