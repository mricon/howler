HOWLER
======
-------------------------------------------------
Get notified when users log in from new locations
-------------------------------------------------

:Author:    konstantin@linuxfoundation.org
:Date:      2017-06-02
:Copyright: The Linux Foundation and contributors
:License:   GPLv3+
:Version:   0.3

DECRIPTION
----------
Did you ever want to be alerted when one of your users suddenly logged
in from somewhere else other than their customary location? E.g. if Bob
suddenly logged in from Australia, even though he usually logs in from
Memphis? Because that's kinda sketchy, eh?

Having previously used this functionality via a proprietary security
device that will remain unnamed, I decided to write this fairly simple
script that relies on the GeoIP-City database to keep track of locations
from where users log in, and alert me if they suddenly start logging in
from elsewhere.

Is this mostly noise? Oh, sure. However, after the initial barrage of
emails as users' locations are recorded, the alerts will stop arriving
all the time and become more meaningful.

Example email::

    This user logged in from a new location:

            User    : mricon
            IP Addr : 198.145.x.x
            Location: Portland, Oregon, US
            Hostname: myhost.kernel.org
            Daemon  : ssh2

    Previously seen locations for this user:
            2012-11-08: Monteal, Quebec, CA

INSTALLING
----------
Just use the RPM. If you can't use the RPM, you can probably figure out
where things go on your own. :)

You'll probably want to install geoipupdate-cron to keep your city data
updated.

OPERATION
---------
The easiest way to use howler is via SEC (Simple Event Correlator) that
provides a mechanism for monitoring log files and triggering external
tools when matches are discovered.

See https://github.com/simple-evcorr/sec

An example howler.sec file is included.

There is also a way to hook things up directly via rsyslog, but it is
quirkier and requires installing an SELinux policy, so just go with SEC.

SUPPORT
-------
Please use github project page https://github.com/mricon/howler to
request support or features.
