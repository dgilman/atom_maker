
def create_error_feed(error_msg):
   """In case of an unrecoverable error print out an error feed and exit"""
   error_id = "http://gilslotd.com/"
   import datetime
   now = rfc3339(datetime.datetime.now())
   print u'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Internal feed error</title><id>%s</id><updated>%s</updated><author><name>rssgen</name></author><entry><titl    e>%s</title><id>%s</id><updated>%s</updated><content type="text">%s</content></entry></feed>' % (error_id, now, error_msg, error_id, now, error_msg)
   sys.exit()

