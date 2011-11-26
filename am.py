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

import sys, os

VERSION = 1

from util import create_error_feed as err
from util import rfc3339

def create_atom(feed):
   """Validates the generator output and creates the ATOM feed"""
   xml = []

   import datetime
   now = rfc3339(datetime.datetime.now())

   if not feed:
      err("Your generator forgot to return a dict.")
   if not "title" in feed:
      err("The feed lacks a title.")
   if not "id" in feed:
      err("The feed lacks a UUID.")
   if not "updated" in feed:
      feed["updated"] = now
   if not "entries" in feed:
      err("The feed lacks entries.")

   xml.append(u'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>%s</title><id>%s</id><updated>%s</updated>' % (feed["title"], feed["id"], feed["updated"]))
   if "author" in feed:
      xml.append(u'<author><name>%s</name>' % feed["author"])
      if "author_uri" in feed:
         xml.append(u'<uri>%s</uri>' % feed["author_uri"])
      xml.append(u'</author>')
   if "subtitle" in feed:
      xml.append(u'<subtitle>%s</subtitle>' % feed["subtitle"])
   if "link" in feed:
      xml.append(u'<link href="%s" />' % feed["link"])
   xml.append(u'<generator uri="https://github.com/dgilman/atom_maker" version="%s">atom_maker</generator>' % str(VERSION))

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
         entry["updated"] = now

      xml.append(u'<entry><id>%s</id><title>%s</title><content type="%s">%s</content><updated>%s</updated>' % (entry["id"], entry["title"], entry["content_type"], entry["content"], entry["updated"]))

      if "author" in entry:
         xml.append(u'<author><name>%s</name>' % entry["author"])
         if "author_uri" in entry:
            xml.append(u'<uri>%s</uri>' % entry["author_uri"])
         xml.append(u'</author>')
      if "published" in entry:
         xml.append(u'<published>%s</published>' % entry["published"])
      if "link" in entry:
         xml.append(u'<link href="%s" />' % entry["link"])

      xml.append(u'</entry>')
   xml.append(u'</feed>')
   return "".join(xml)

def get_feed_generator(gen_name):
   import generators
   return generators.generators[gen_name]

def get_feed_prefs(name):
   """Returns the dict corresponding to a feed entry in the prefs file."""
   try:
      import prefs
   except:
      err("Your prefs file is broken.")
   if prefs.prefs["version"] != VERSION:
      err("You need to migrate your prefs file to the latest version!  See the changelog for help.")
   try:
      return prefs.prefs[name]
   except:
      err("Feed name not in prefs file.")

def get_feed(name):
   """Get the entry for name from prefs and run the appropriate generator.
   Return the generated dict."""
   feed_prefs = get_feed_prefs(name)
   generator = get_feed_generator(feed_prefs['generator'])
   return generator(feed_prefs['args'])

def cli():
   if len(sys.argv) < 2:
      print "Give the name of a feed to generate"
      sys.exit()

   print create_atom(get_feed(sys.argv[1].decode('UTF-8'))).encode('UTF-8')

def page():
   import cgi

   args = cgi.parse()

   print "Content-Type: application/atom+xml;charset=UTF-8"
   print ""
   if not "feed" in args:
      err("Feed requested must be in the query string (rg.py?feed=foo).")
   print create_atom(get_feed(args["feed"][0])).encode('UTF-8')

if 'REQUEST_METHOD' in os.environ and os.environ['REQUEST_METHOD'] == 'GET':
   try:
      page()
   except Exception:
      import traceback
      err("An exception has occured.  The generator may no longer be compatible with your webpage.\n%s" % traceback.format_exc())
else: # fuck it, we're cli
   cli()
