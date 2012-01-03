#!/usr/bin/python
# vim: ts=3 et sw=3 sts=3:

# Copyright 2011 David Gilman
#
# This file is part of atom_maker.
#
# atom_maker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# atom_maker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with atom_maker.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import cgi
import datetime
import sqlite3

VERSION = 2
cache_length = datetime.timedelta(hours=6)
now = datetime.datetime.utcnow()

# generators imported here to avoid syntax errors bubbling up when importing prefs
import generators
from util import create_error_feed as err
from util import rfc3339
import schema

def create_atom(feed):
   """Validates the generator output and creates the ATOM feed"""
   xml = []

   esc = cgi.escape

   ts = rfc3339(now)

   if not feed:
      err("Your generator forgot to return a dict.")
   if not "title" in feed:
      err("The feed lacks a title.")
   if not "id" in feed:
      err("The feed lacks a UUID.")
   if not "updated" in feed:
      feed["updated"] = ts
   if not "entries" in feed:
      err("The feed lacks entries.")

   xml.append('<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>%s</title><id>%s</id><updated>%s</updated>' % (feed["title"], esc(feed["id"]), feed["updated"]))
   if "author" in feed:
      xml.append('<author><name>%s</name>' % feed["author"])
      if "author_uri" in feed:
         xml.append('<uri>%s</uri>' % esc(feed["author_uri"]))
      xml.append('</author>')
   if "subtitle" in feed:
      xml.append('<subtitle>%s</subtitle>' % feed["subtitle"])
   if "link" in feed:
      xml.append('<link href="%s" />' % esc(feed["link"]))
   xml.append('<generator uri="https://github.com/dgilman/atom_maker" version="%s">atom_maker</generator>' % str(VERSION))
   xml.append('<link rel="self" href="http://%s%s" />' % (os.environ['SERVER_NAME'], esc(os.environ['REQUEST_URI'])))

   #validate individual entries.

   check_for_authors = False
   if not "author" in feed:
      check_for_authors = True

   for entry in feed["entries"]:
      if check_for_authors and not "author" in entry:
         err("One of the feed entries lacks an author.  If there is no global author set each feed needs its own author.")
      if not "id" in entry:
         err("An entry lacks a UUID.")
      if not "title" in entry:
         err("An entry lacks a title.")
      if not "content" in entry:
         err("An entry lacks content.")
      if not "content_type" in entry:
         err("All entries need a content_type.  It must be text, html or xhtml depending on the content.")
      if not "updated" in entry:
         entry["updated"] = ts

      if entry["content_type"] == "html":
         entry["content"] = esc(entry["content"])

      xml.append('<entry><id>%s</id><title>%s</title><content type="%s">%s</content><updated>%s</updated>' % (esc(entry["id"]), entry["title"], entry["content_type"],entry["content"], entry["updated"]))

      if "author" in entry:
         xml.append('<author><name>%s</name>' % entry["author"])
         if "author_uri" in entry:
            xml.append('<uri>%s</uri>' % esc(entry["author_uri"]))
         xml.append('</author>')
      if "published" in entry:
         xml.append('<published>%s</published>' % entry["published"])
      if "link" in entry:
         xml.append('<link href="%s" />' % esc(entry["link"]))

      xml.append('</entry>')
   xml.append('</feed>')
   return "".join(xml)

def get_feed_generator(name):
   """Returns the generator function corresponding to a feed entry in the prefs file."""
   try:
      import prefs
   except SyntaxError:
      err("Your prefs file has a typo in it.")
   except ImportError:
      err("Your prefs.py file is missing.")
   except:
      err("prefs.py couldn't be imported.")
   if prefs.version != VERSION:
      err("You need to migrate your prefs file to the latest version!  See the changelog for help.")
   try:
      return prefs.prefs[name]
   except:
      err("Generator name not in prefs file.")

def get_feed(name):
   """Get the entry for name from prefs and run the appropriate generator.
   Return the generated dict."""
   generator_name, underscore, generator_args = name.partition("_")
   generator = get_feed_generator(generator_name)
   return generator(generator_args)

def feed_cache(qs, flush=False):
   conn = sqlite3.connect("cache.sqlite3", detect_types=sqlite3.PARSE_DECLTYPES)
   c = conn.cursor()
   schema.check(c)

   cache = c.execute("select ts, feed from cache where qs = ?", (qs,)).fetchall()
   if len(cache) == 0 or (now - cache[0][0] > cache_length) or flush:
      rval = create_atom(get_feed(qs))
      c.execute("replace into cache values (?, ?, ?)", (qs, now, rval))
      conn.commit()
   else:
      rval = cache[0][1]
   conn.close()
   return rval

def cli():
   if len(sys.argv) < 2:
      print "Give the name of a feed to generate"
      sys.exit()

   os.environ['SERVER_NAME'] = "cli/"
   os.environ['REQUEST_URI'] = sys.argv[1]

   has_xml = True
   try:
      import lxml.etree as etree
   except:
      has_xml = False

   feed = feed_cache(sys.argv[1].decode('UTF-8'), flush=True).encode('UTF-8')

   if not has_xml:
      print feed
   else:
      print etree.tostring(etree.fromstring(feed), pretty_print = True, encoding="UTF-8")

def page():
   args = cgi.parse()
   flush = False

   print "Content-Type: application/atom+xml;charset=UTF-8"
   print ""
   if not "feed" in args:
      err("Feed requested must be in the query string (am.py?feed=foo).")
   if "flush" in args:
      flush = True
   print feed_cache(args["feed"][0].decode('UTF-8'), flush).encode('UTF-8')

if __name__ == "__main__":
   if 'REQUEST_METHOD' in os.environ and os.environ['REQUEST_METHOD'] == 'GET':
      try:
         page()
      except Exception: # this catches everything but sys.exit()
         import traceback
         err("An uncaught exception has occured.  The generator may no longer be compatible with your webpage.\n%s" % traceback.format_exc())
   else: # fuck it, we're cli
      cli()
