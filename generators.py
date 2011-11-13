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
# You should have received a copy of the GNU General Public License 19 # along with atom_maker.  If not, see <http://www.gnu.org/licenses/>.

#when adding a generator don't forget to add it to the dict at the end of the file!

#generator spec:

#you must have an author field in the overall feed or an author field for all entries.
#THIS IS ENFORCED.

#return a dict with the following fields:
#
#id: permalink url
#title: derp
#(optional) author: see note above
#(optional) author_uri: optional link to a page for the author
#(optional) updated: date (rfc3339) of last update.  if not given uses now
#(optional) subtitle: description
#(optional) link: page link
#entry: list of dicts of entries (described below)

#entries:
#
#id: entry permalink
#title: derp
#content: body of story
#content_type: one of text, html, xhtml
#(optional) author: see note above
#(optional) author_uri: optional link to a page for the author
#(optional) published: rfc3339 string of publishing date
#(optional) updated: date (rfc3339) of last update.  if not given uses now
#(optional) link: entry link

def twitter_noreply(arg):
   """Strips out @replies from a user's twitter feed.
   arg is a tuple of strings (username, uid).
   username is case-sensitive
   uid has to be looked up from the user's rss feed (afaict)"""
   from lxml import etree
   import sys
   username, uid = arg

   t = etree.parse('http://twitter.com/statuses/user_timeline/%s.rss' % uid)
   reply = [e.getparent() for e in t.xpath('//item/title') if e.text.startswith('%s: @' % username)]
   for e in reply:
      e.getparent().remove(e)

   print etree.tostring(t).encode('UTF-8')
   sys.exit()

def redhat_sources_bz(arg):
   return _bz4(arg, 'http://sources.redhat.com/bugzilla')

def bmo(arg):
   return _bz4(arg, 'https://bugzilla.mozilla.org')

def _bz4(arg, url):
   #TODO: not assume everyone's in PST
   from lxml import etree
   import urllib #bugzilla.mozilla.org forces https which libxml2 balks at
   url = '%s/show_bug.cgi?id=%s' % (url, arg)
   rval = {"id": url,
           "link": url,
           "entries": []}

   tree = etree.parse(urllib.urlopen(url), etree.HTMLParser(encoding="UTF-8"))
   comments = tree.xpath("//div[@class='bz_comment']")
   rval["title"] = tree.xpath('/html/head/title')[0].text

   for e in tree.xpath('//pre[@class="bz_comment_text"]'):
      e.attrib["style"] = "white-space:pre-wrap"

   for comment in comments:
      time = comment.xpath("div/span[@class='bz_comment_time']")[0].text.strip("\n ")
      timebits = time.split()
      pseudo = timebits[0]+ "T" + timebits[1] + "-07:00" #pseudo rfc3339
      fn = comment.xpath("div/span/span/span[@class='fn']")
      if len(fn) == 1:
         name = fn[0].text
      else: #user didn't give a full name to bugzilla
         name = comment.xpath("div/span/span")[0].text[:-1] #random newline
      entry = {"id": comment.attrib["id"],
               "title": u"Comment %s - %s - %s" % (comment.attrib["id"][1:], name, time),
               "content": etree.tostring(comment.xpath("pre[@class='bz_comment_text']")[0]),
               "content_type": "html",
               "author": name,
               "updated": pseudo,
               "published": pseudo,
               "link": "%s/%s" % (url, comment.xpath("div/span/a")[0].attrib["href"])}
      rval["entries"].append(entry)
      rval["updated"] = pseudo #the last updated time of the global feed is the post time of the last comment... for now
   return rval

def gelbooru(arg):
   """Gets the latest posts for a given tag query.  Arg is the query, no need to urlencode spaces"""
   from lxml import etree
   url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%s' % arg
   rval = {"id": url,
           "title": "%s - Gelbooru" % arg,
           "author": "Gelbooru",
           "link": url,
           "entries": []}

   tree = etree.parse(url, etree.HTMLParser(encoding="UTF-8"))
   posts = tree.xpath('//div[@class="content"]/div[2]/span')

   for post in posts:
      entry = {"id": post.attrib["id"],
               "title": post.xpath('a/img')[0].attrib["alt"],
               "content": etree.tostring(post.xpath('a')[0]),
               "content_type": "html",
               "link": "http://gelbooru.com/%s" % post.xpath('a')[0].attrib["href"]}
      rval["entries"].append(entry)
   return rval

def hackernews_comments(arg):
   """Gets the comments of a hacker news user.  arg is a string (the username)"""
   rval = {"id": 'http://news.ycombinator.com/threads?id=%s' % arg,
           "title": "%s's comments - Hacker News" % arg,
           "author": arg,
           "link": 'http://news.ycombinator.com/threads?id=%s' % arg,
           "entries": []}

   from lxml import etree

   link = lambda e: 'http://news.ycombinator.com/' + e.xpath('div/span[@class="comhead"]/a[2]')[0].attrib['href']
   post = lambda e: etree.tostring(list(e.xpath('span[1]')[0])[0], encoding='UTF-8') #get rid of <span class="comment">

   tree = etree.parse('http://news.ycombinator.com/threads?id=%s' % arg, etree.HTMLParser(encoding="UTF-8"))
   user_comments = tree.xpath('/html/body/center/table/tr/td/table/tr/td[div/span/a = "%s"]' % arg)

   links = [link(e) for e in user_comments]
   posts = [post(e) for e in user_comments]

   for comment in zip(links, posts):
      entry = {"id": comment[0],
               "link": comment[0],
               "title": "%s's comment" % arg,
               "content": comment[1].decode('UTF-8'),
               "content_type": "html"}
      rval["entries"].append(entry)

   return rval

generators = {
   "hackernews_comments": hackernews_comments,
   "gelbooru": gelbooru,
   "bmo": bmo,
   "redhat_sources_bz": redhat_sources_bz,
   "twitter_noreply": twitter_noreply
}
