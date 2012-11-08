HOWLER
======
-------------------------------------------------
Get notified when users log in from new locations
-------------------------------------------------

:Author:    mricon@kernel.org
:Date:      2012-11-07
:Copyright: The Linux Foundation and contributors
:License:   GPLv3+
:Version:   0.2

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

INSTALLING
----------
Just use the RPM. If you can't use the RPM, you can probably figure out
where things go on your own. :) Yes, this section is TODO.

Note that for howler to be more useful than just announcing the country
code, you'll need to download GeoLiteCity.dat. You can get it from
maxmind.com for free (but it's not redistributable).

OPERATION
---------
The only mechanism currently provided is via rsyslog. The default
configuration works by sending all syslog strings coming from the 'sshd'
daemon to howler-rsyslog-helper, which parses the info out of lines
containing successful login information and sends that to howler.

Using rsyslog for this is sub-optimal, as it requires making an external
exec call from the rsyslog process. If you have a lot of logins, this
will probably interfere with rsyslog's operation and slow things down.

I will be adding Epylog support for Howler in the near future (for the 2
people in the world who use Epylog). This can probably be made to work
via journal, too.

Other contributions are welcomed!

SUPPORT
-------
Please use github project page https://github.com/mricon/howler to
request support or features.

