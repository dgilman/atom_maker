#!/usr/bin/env python
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
import cStringIO
import codecs

lxml = False
try:
   from lxml import etree
   lxml = True
except:
   import xml.etree.cElementTree as etree

VERSION = 4
cache_length = datetime.timedelta(hours=6)
now = datetime.datetime.utcnow()

# generators imported here to avoid syntax errors bubbling up when importing prefs
import generators
from util import create_error_feed as err
from util import rfc3339
from util import self_url
import schema

def child_tag(root, tag, text=None, attrib=None):
   if attrib:
      new = etree.SubElement(root, tag, attrib=attrib)
   else:
      new = etree.SubElement(root, tag)
   if text: new.text = text
   return new

def create_atom(feed):
   """Validates the generator output and creates the ATOM feed"""
   root = etree.Element("feed", attrib={"xmlns": "http://www.w3.org/2005/Atom"})

   esc = cgi.escape

   ts = rfc3339(now)

   if not isinstance(feed, dict):
      err("Your generator forgot to return a dict.")
   if not "title" in feed:
      err("The feed lacks a title.")
   if not "id" in feed:
      err("The feed lacks a UUID.")
   if not "updated" in feed:
      feed["updated"] = ts
   if not "entries" in feed:
      err("The feed lacks entries.")

   if 'lang' in feed:
      root.set(etree.QName("{http://www.w3.org/XML/1998/namespace}lang"), feed["lang"])

   child_tag(root, "title", text=feed["title"])
   child_tag(root, "id", text=feed["id"])
   child_tag(root, "updated", text=feed["updated"])
   if "author" in feed:
      author = child_tag(root, "author")
      child_tag(author, "name", text=feed["author"])
      if "author_uri" in feed:
         child_tag(author, "uri", feed["author_uri"])
   if "subtitle" in feed:
      child_tag(root, "subtitle", text=feed["subtitle"])
   if "link" in feed:
      child_tag(root, "link", attrib={'href': feed["link"]})
   child_tag(root, "generator", attrib={"uri": "https://github.com/dgilman/atom_maker", "version": str(VERSION)}, text="atom_maker")
   child_tag(root, "link", attrib={"rel": "self", "href": self_url()})

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
         err("All entries need a content_type.")
      if entry["content_type"] not in ["html", "text", "xhtml"]:
         err("content_type must be one of html, text, or html.")
      if not "updated" in entry:
         entry["updated"] = ts

      e = child_tag(root, "entry")
      if "lang" in entry:
         e.set(etree.QName("{http://www.w3.org/XML/1998/namespace}lang"), feed["lang"])
      child_tag(e, "id", text=entry["id"])
      child_tag(e, "title", text=entry["title"])
      child_tag(e, "content", attrib={"type": entry["content_type"]}, text=entry["content"])
      child_tag(e, "updated", text=entry["updated"])

      if "author" in entry:
         author = child_tag(e, "author")
         child_tag(author, "name", text=entry["author"])
         if "author_uri" in entry:
            child_tag(author, "uri", text=entry["author_uri"])
      if "published" in entry:
         child_tag(e, "published", text=entry["published"])
      if "link" in entry:
         child_tag(e, "link", attrib={"href": entry["link"]})
   rval = cStringIO.StringIO()
   tree = etree.ElementTree(element=root)
   if sys.version_info < (2, 7):
      tree.write(rval, encoding="UTF-8")
   else:
      tree.write(rval, encoding="UTF-8", xml_declaration=True)
   return rval.getvalue()

def get_feed_generator(name):
   """Returns the generator function corresponding to a feed entry in the prefs file."""
   try:
      import prefs
   except SyntaxError:
      err("Your prefs file has a typo in it.")
   except ImportError:
      err("Your prefs.py file is missing.")
   except:
      import traceback
      err("prefs.py couldn't be imported.\n%s" % traceback.format_exc())
   if prefs.version != VERSION:
      err("You need to migrate your prefs file to the latest version!  See the changelog for help.")
   try:
      return prefs.prefs[name]
   except:
      err("Generator name not in prefs file.")

def get_feed(args):
   """Get the entry for name from prefs and run the appropriate generator.
   Return the generated dict."""
   generator = get_feed_generator(args["qs"]["gen"])
   return generator(args)

def parse_qs(qs):
   if "flush" in qs:
      del(qs["flush"])
   rval = {"qs": {}}
   for k,v in qs.iteritems():
      qs[k] = v[0].decode("UTF-8")
   if 'feed' in qs: # old-style
      rval["cache_key"] = qs["feed"]
      rval["qs"].update(((k,v) for k,v in qs.iteritems() if k != 'feed')) # slurp up other args
      rval["qs"]["gen"], underscore, rval["qs"]["arg"] = qs['feed'].partition("_") # overwrites a gen and arg if they were given
   elif "gen" in qs:
      rval["qs"] = qs
      additional_args = [x for x in qs.keys() if x != "gen" and x != "arg"]
      if "arg" in qs:
         rval["cache_key"] = qs["gen"] + "_" + qs["arg"]
      else:
         rval["cache_key"] = qs["gen"]
      if len(additional_args) != 0:
         rval["cache_key"] += "_"
         rval["cache_key"] += "_".join((x + "_" + qs[x] for x in additional_args))
   else:
      err("Your query string is incomplete.")
   return rval

def feed_cache(qs, flush=False):
   c = schema.init()

   args = parse_qs(qs)
   args["cursor"] = c

   cache = c.execute("select ts, feed from cache where qs = ?", (args["cache_key"],)).fetchall()
   if len(cache) == 0 or (now - cache[0][0] > cache_length) or flush:
      rval = create_atom(get_feed(args))
      c.execute("replace into cache values (?, ?, ?)", (args["cache_key"], now, buffer(codecs.getencoder("zlib")(rval)[0])))
      conn.commit()
   else:
      rval = codecs.getdecoder("zlib")(cache[0][1])[0]
   conn.close()
   return rval

def cli():
   if len(sys.argv) < 2:
      print "Give the name of a feed to generate"
      sys.exit()

   # hack to support old-style from cmd line
   if "&" not in sys.argv[1]:
      sys.argv[1] = "feed=%s" % sys.argv[1]

   os.environ['SERVER_NAME'] = "cli/"
   os.environ['REQUEST_URI'] = sys.argv[1]
   os.environ['QUERY_STRING'] = sys.argv[1]

   args = cgi.parse()

   feed = feed_cache(args, flush=True)

   if not lxml:
      print feed
   else:
      feed = etree.tostring(etree.fromstring(feed), pretty_print = True, encoding="UTF-8", xml_declaration=True)
      print feed

   try:
      import feedvalidator
      from feedvalidator.formatter.text_plain import Formatter
      from feedvalidator import compatibility
      from feedvalidator.logging import ValidValue
      events = (x for x in feedvalidator.validateString(feed, firstOccurrenceOnly=True, base=self_url())['loggedEvents'] if not isinstance(x, ValidValue))
      print "\n".join(Formatter(events)).encode("UTF-8")
   except ImportError:
      pass

def page():
   args = cgi.parse()
   flush = False

   print "Content-Type: application/atom+xml;charset=UTF-8"
   print ""
   if "flush" in args:
      flush = True
   print feed_cache(args, flush)

if __name__ == "__main__":
   if 'REQUEST_METHOD' in os.environ and os.environ['REQUEST_METHOD'] == 'GET':
      try:
         page()
      except Exception: # this catches everything but sys.exit()
         import traceback
         err("An uncaught exception has occured.  The generator may no longer be compatible with your webpage.\n%s" % traceback.format_exc())
   else: # fuck it, we're cli
      cli()
