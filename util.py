badparse = "The page couldn't be parsed properly.  It's likely that the page's markup has changed and your atom_maker needs to be updated."
badfetch = "The page couldn't be fetched.  The website might be down."
noarg = "This generator has a mandatory primary argument (arg).  You need to include one in your query."

def rfc3339(d): # https://bitbucket.org/henry/rfc3339/src/tip/rfc3339.py 
    return ('%04d-%02d-%02dT%02d:%02d:%02dZ' % (d.year, d.month, d.day, d.hour, d.minute, d.second))

def create_error_feed(error_msg, silent=False):
   """In case of an unrecoverable error print out an error feed and exit"""
   import sys
   from cgi import escape
   import datetime

   if silent:
      sys.exit()

   now = rfc3339(datetime.datetime.utcnow())
   guid = "https://github.com/dgilman/atom_maker" + "#" + now

   rval = '<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Internal feed error</title><id>%(id)s</id><updated>%(ts)s</updated><link rel="self" href="%(self)s"/><author><name>atom_maker</name></author><entry><title>%(title)s</title><id>%(id)s</id><updated>%(ts)s</updated><content type="html">%(content)s</content></entry></feed>' % ({"id": guid, "ts": now, "self": escape(self_url()), "title": error_msg.partition('\n')[0], "content": escape("<pre>"+error_msg+"</pre>")})
   print rval.encode("UTF-8")
   sys.exit()

def self_url():
   import os
   from cgi import escape
   return "http://%s%s" % (os.environ['SERVER_NAME'].decode("UTF-8"), os.environ['REQUEST_URI'].decode("UTF-8"))

def warn_old(guid, id):
   """guid: path to bug (foo.com/show_bug.cgi)
      id: bug id"""
   import datetime
   now = rfc3339(datetime.datetime.utcnow())
   guid = guid + "#oldwarning_%d" % now.year # on january 1 feed readers will present a "new" reminder
   return {"id": guid,
            "title": "Bug %s is old" % id,
            "content": "Bug %s hasn't been changed in over a year.  It might be time to give up hope." % id,
            "content_type": "text",
            "author": "The Great Gig In The Sky",
            "updated": now,
            "published": now,
            "link": guid}

