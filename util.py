def rfc3339(d): # https://bitbucket.org/henry/rfc3339/src/tip/rfc3339.py 
    return ('%04d-%02d-%02dT%02d:%02d:%02dZ' % (d.year, d.month, d.day, d.hour, d.minute, d.second))

def create_error_feed(error_msg):
   """In case of an unrecoverable error print out an error feed and exit"""
   error_id = "https://github.com/dgilman/atom_maker"
   import datetime
   now = rfc3339(datetime.datetime.now())
   print u'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Internal feed error</title><id>%s</id><updated>%s</updated><author><name>rssgen</name></author><entry><title>%s</title><id>%s</id><updated>%s</updated><content type="text">%s</content></entry></feed>' % (error_id, now, error_msg.partition('\n')[0], error_id, now, error_msg)
   import sys
   sys.exit()

