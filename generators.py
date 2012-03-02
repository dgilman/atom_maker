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

from util import create_error_feed as err
from util import badparse
from util import badfetch
from util import noarg

# Generator function spec:

# arg:
# All generators are called with a single dict.  It will always have the following keys:
# "cursor": cursor object to the sqlite3 cache database.  Please try and avoid writing to the "cache" table and please upstream your schema to avoid conflicts.
# "qs": a dict of the query string args.
#     "gen": the key in prefs.py that called your generator.
#     (optional) "arg": This is called the primary argument.  It is specified with "arg" in the query string.
#         Use this for the primary value of configuration (for example the username of a twitter timeline).


# rval:
# All generators must return a dict with the following keys:

# You must have an author field in the overall feed or an author field for all entries.
# THIS IS ENFORCED.

# id: Permalink.  Atom spec says it must be a URL.
# title: the title
# (optional) author: The author's name.  See note above about the author field
# (optional) author_uri: optional link to a page for the author
# (optional) updated: A string of the date (rfc3339) of last update.  If this is not given the current time will be used.
# (optional) subtitle: A description of the feed.
# (optional) link: A link to the corresponding page for the feed.
# (optional) lang: An xml:lang attribute value for the entire feed.
# entries: list of dicts of entries (described below)

# entries:
#
# id: A permalink to the entry.  If you don't make this consistent across runs feed readers will be confused.  The atom spec demands that this be a URL.
# title: the title
# content: Body of story
# content_type: one of text, html, xhtml
# (optional) author: The name of the author of the post.  See the above note
# (optional) author_uri: optional link to a page for the author
# (optional) published: string (rfc3339) of publishing date
# (optional) updated: string of the date (rfc3339) of last update.  if not given uses now
# (optional) link: Link to the entry.
# (optional) lang: xml:lang attribute value for this entry.

def twitter_context(arg):
   import json
   import urllib
   from util import rfc3339
   import datetime

   import twitter
   from twitter import format_tweet


   if "oauth" not in arg:
      arg["oauth"] = False

   if "arg" not in arg["qs"] and arg["oauth"] == False:
      err(noarg)

   if "token_name" not in arg:
      arg["token_name"] = None

   if "infinite_retries" not in arg:
      arg["infinite_retries"] = True

   if "filter_foursquare" not in arg:
      arg["filter_foursquare"] = False

   p = twitter.Twitter(db=arg["cursor"], oauth=arg["oauth"], token_name=arg["token_name"], infinite_retries=arg["infinite_retries"])

   if "mentions" in arg and arg["mentions"] == True:
      tweets = p.mentions()
      uname = p.me().screen_name
   else:
      uname = arg["qs"]["arg"]
      tweets = p.user_timeline(uname)

   tweet_cache = {}
   for tweet in tweets:
      tweet_cache[tweet.id] = tweet

   rval = {"id": "http://twitter.com/%s#atom_maker_context_feed" % uname,
           "link": "http://twitter.com/%s" % uname,
           "title": "Twitter / %s / context" % uname,
           "author": tweets[0].user.name,
           "entries": []}

   if 'lang' in arg["qs"]:
      rval["lang"] = arg["qs"]['lang']

   parent_skip_list = set()
   for tweet in tweets:
      if tweet.id in parent_skip_list:
         continue
      if arg["filter_foursquare"] and tweet.source == "foursquare":
         continue

      content = []
      tweet_url = "http://twitter.com/%s/status/%s" % (tweet.user.screen_name, tweet.id_str)

      entry = {"id": tweet_url,
               "title": "%s: " % tweet.user.screen_name + tweet.text,
               "content_type": "html",
               "updated": rfc3339(tweet.created_at),
               "link": tweet_url}
      content.append(format_tweet(tweet.user.screen_name, tweet.user.name, tweet.text, tweet_url, tweet.created_at))
      parent_id = tweet.in_reply_to_status_id
      while parent_id:
         if parent_id in tweet_cache:
            parent_tweet = tweet_cache[parent_id]
         else:
            try:
               parent_tweet = p.get_tweet(parent_id)
            except:
               break
            tweet_cache[parent_id] = parent_tweet

         # don't make a new RSS entry for tweets in a conversation chain
         if parent_tweet.user.id == tweet.user.id:
            parent_skip_list.add(parent_tweet.id)

         content.append(format_tweet(parent_tweet.user.screen_name, parent_tweet.user.name, parent_tweet.text, "http://twitter.com/%s/status/%s" % (parent_tweet.user.screen_name, parent_id), parent_tweet.created_at))

         # continue to next parent or terminate
         parent_id = parent_tweet.in_reply_to_status_id
      entry["content"] = "".join(reversed(content))
      rval["entries"].append(entry)
   rval["updated"] = rval["entries"][0]["updated"] # first tweet is newest
   return rval

def blogspot(arg):
   """Some users don't have RSS feeds turned on.  why_would_you_do_that.jpg"""
   from lxml import etree

   if "arg" not in arg["qs"]:
      err(noarg)

   url = 'http://%s.blogspot.com/' % arg["qs"]["arg"].replace("/#&", "")
   try:
      t = etree.parse(url, etree.HTMLParser(encoding="UTF-8"))
   except:
      err(badfetch)

   posts = t.xpath('//div[@class="post-outer"]')
   if len(posts) == 0: err(badparse)

   rval = {"id": url,
           "link": url,
           "title": t.xpath('//title')[0].text,
           "entries": []}

   if "lang" in arg["qs"]:
      rval["lang"] = arg["qs"]["lang"]

   for post in posts:
      ts = post.xpath('descendant::abbr[@class="published"]')[0].attrib["title"]
      link = post.xpath('descendant::a[@title="permanent link"]')[0].attrib["href"]
      entry = {"id": link,
               "title": post.xpath('descendant::div[@class="title"]/h2/a')[0].text,
               "content": etree.tostring(post.xpath('descendant::div[@class="postcover"]')[0]),
               "content_type": "html",
               "author": post.xpath('descendant::span[@class="fn"]')[0].text,
               "published": ts,
               "updated": ts,
               "link": link}
      rval["entries"].append(entry)
   rval["updated"] = rval["entries"][0]["updated"] #assume the first entry is the newest
   return rval

def twitter_noreply(arg):
   # At some point https://dev.twitter.com/discussions/2690 will be fixed, making this function unnecessary
   from lxml import etree
   import sys
   import urllib

   if "arg" in arg["qs"]:
      username = arg["qs"]["arg"]
   else:
      err(noarg)

   try:
      uid = urllib.urlopen("http://www.idfromuser.com/getID.php?username=%s" % username).readlines()[0]
   except:
      err("Couldn't figure out the twitter user ID.  You might need to update atom_maker.")

   try:
      t = etree.parse('http://twitter.com/statuses/user_timeline/%s.rss' % uid)
   except:
      err(badfetch)
   titles = t.xpath('//item/title')
   if len(titles) == 0: err(badparse)
   reply = [e.getparent() for e in titles if e.text.startswith('%s: @' % username)]
   for e in reply:
      e.getparent().remove(e)

   print etree.tostring(t).encode('UTF-8')
   sys.exit()

# BUGZILLA GENERATORS

# If the bugzilla in question has bugzilla 3.4 or greater you can use _bz_xmlrpc
# Protip: the bugzilla version is listed on the release notes page linked on the Bugzilla's front page

# _bz_screenscrape supports all of bugzilla 3 and 4 but lacks the history features

def redhat_sources_bz(arg):
   arg["url"] = 'http://sourceware.org/bugzilla'
   arg["qs"]["lang"] = "en"
   return _bz_xmlrpc(arg)

def bmo(arg):
   arg["url"] = 'https://bugzilla.mozilla.org'
   arg["qs"]["lang"] = "en"
   return _bz_xmlrpc(arg)

def webkit(arg):
   arg["url"] = 'https://bugs.webkit.org'
   arg["version"] = 3
   arg["qs"]["lang"] = "en"
   return _bz_screenscrape(arg)

def _bz_xmlrpc(arg):
   """arg: bug id as string
   url: path to bugzilla installation
   history: put history changes in feed (optional, default true)
   ccs: include cc changes in history (optional, default false)"""
   import xmlrpclib
   import sqlite3
   import datetime
   import re
   now = datetime.datetime.utcnow()
   from util import rfc3339
   from util import warn_old

   if "arg" not in arg["qs"]:
      err(noarg)

   try:
      int(arg['qs']['arg'])
   except:
      err("Bug IDs must be numerical.")

   if not "history" in arg["qs"]: # the default
      history = True
   else:
      if arg["qs"]["history"][0] in "Ff0":
         history = False
      else:
         history = True

   if not "ccs" in arg["qs"]:
      ccs = False
   else:
      if arg["qs"]["ccs"][0] in "Ff0":
         ccs = False
      else:
         ccs = True

   if "warn_old" not in arg:
      arg["warn_old"] = True

   url = arg["url"]
   bugid = arg["qs"]["arg"]
   p = xmlrpclib.ServerProxy(url + "/xmlrpc.cgi", use_datetime=True)

   try:
      bugdata = p.Bug.get({"ids":[bugid], "permissive": True})
   except:
      err(badfetch)
   if len(bugdata['faults']) > 0: err(bugdata['faults'][0]['faultString'])
   bugdata = bugdata["bugs"][0]

   guid = '%s/show_bug.cgi?id=%s' % (url, str(bugdata['id'])) # get the ID in case the query string used the bug alias
   rval = {"id": guid,
           "link": guid,
           "updated": rfc3339(bugdata['last_change_time']),
           "title": "Bug %s - " % bugid + bugdata['summary'],
           "entries": []}

   if "lang" in  arg["qs"]:
      rval["lang"] = arg["qs"]["lang"]

   try:
      bugcomments = p.Bug.comments({"ids":[bugid]})["bugs"][bugid]['comments']
   except:
      err(badfetch)

   commenting_users = [x['author'] for x in bugcomments]
   if history:
      try:
         bug_history = p.Bug.history({"ids":[bugid]})['bugs'][0]['history']
      except:
         err(badfetch)
      commenting_users.extend([h['who'] for h in bug_history])

   c = arg["cursor"]
   c.executescript("""pragma temp_store = MEMORY;
create temp table email_queries (email text unique);""")
   c.execute("insert or ignore into bugzillas (id, url) values (NULL, ?)", (url,))
   bz_id = c.execute("select id from bugzillas where url = ?", (url,)).fetchall()[0][0]
   c.execute("delete from bugzilla_users where ts <= ?", (now.year*100 + now.month - 1,))

   c.executemany("insert or ignore into email_queries (email) values (?)", ((e,) for e in commenting_users))
   cache_misses = c.execute("select email from email_queries where not exists (select 1 from bugzilla_users where bugzilla_users.bz = ? and bugzilla_users.email = email_queries.email)", (bz_id,)).fetchall()
   if len(cache_misses) > 0:
      try:
         real_names = p.User.get({"names": [e[0] for e in cache_misses]})["users"]
      except:
         err(badfetch)
      for user in real_names:
         if len(user['real_name']) != 0:
            rn = user['real_name']
         else:
            rn = user['name']
         c.execute("insert into bugzilla_users (email, name, ts, bz) values (?, ?, ?, ?)", (user['name'], rn, now.year*100 + now.month, bz_id))

   rn = lambda x: c.execute("select name from bugzilla_users where bz = ? and email = ?", (bz_id, x)).fetchall()[0][0]

   if history:
      for bug_history_change_no, bug_history_change in enumerate(bug_history):
          # don't even create an rss entry if cc is the only thing that's changed and we're ignoring ccs
          if len(bug_history_change['changes']) == 1 and bug_history_change['changes'][0]['field_name'] == 'cc' and ccs == False:
             continue
          history_id = guid + "#h" + str(bug_history_change_no)

          content = ['<pre style="white-space:pre-wrap">']
          for field_change in bug_history_change['changes']:
             if field_change['field_name'] == 'cc' and ccs == False:
                continue
             content.append("Field <b>%s</b>:\n" % field_change['field_name'])
             if field_change['field_name'] == 'attachments.isobsolete':
                content.append('<a href="%s/attachment.cgi?id=%d">Attachment #%d</a> is obsolete\n' % (url, field_change['attachment_id'], field_change['attachment_id']))
             if field_change['field_name'] in ['dependson', 'blocked']:
                sub = lambda f: re.sub("(\d+)", lambda m: '<a href="%s/show_bug.cgi?id=%s">%s</a>' % (url, m.group(1), "Bug " + m.group(1)), f)
                if 'added' in field_change:
                   field_change['added'] = sub(field_change['added'])
                if 'removed' in field_change:
                   field_change['removed'] = sub(field_change['removed'])
             content.append("Removed:\n")
             content.append("     %s\n" % field_change['removed'])
             content.append("Added:\n")
             content.append("     %s\n\n" % field_change['added'])
          content.append("</pre>")

          real_name = rn(bug_history_change['who'])
          when = rfc3339(bug_history_change['when'])
          entry = {"id": history_id,
                   "title": "%s changed at %s" % (real_name, when),
                   "author": real_name,
                   "updated":  when,
                   "published": bug_history_change['when'], # keep for sorting
                   "link": history_id,
                   "content": "".join(content),
                   "content_type": "html"}
          rval["entries"].append(entry)

   linkbugs = lambda x: re.sub("([Bb])ug (\d+)", lambda m: '<a href="%s/show_bug.cgi?id=%s">%s</a>' % (url, m.group(2), m.group(1) + "ug " + m.group(2)), x)
   for comment_no, comment in enumerate(bugcomments):
      comment_id = guid + "#c" + str(comment_no)
      real_name = rn(comment['author'])
      comment_time_str = rfc3339(comment['time'])
      entry = {"id": comment_id,
               "title": u"Comment %s - %s - %s" % (str(comment_no), real_name, comment_time_str),
               "content": '<pre style="white-space:pre-wrap">' + linkbugs(comment['text']) + "</pre>",
               "content_type": "html",
               "author": real_name,
               "updated": comment_time_str,
               "published": comment['time'], # keep for sorting
               "link": comment_id}
      rval["entries"].append(entry)

   rval["entries"].sort(key=lambda e: e["published"])
   for entry in rval["entries"]:
      entry["published"] = rfc3339(entry["published"])

   if arg["warn_old"] and bugdata['last_change_time'] < (now - datetime.timedelta(days=365)):
      rval["entries"].append(warn_old(guid, bugid))

   return rval

def _bz_screenscrape(arg):
   """arg: bug id as string
   url: path to bugzilla installation without slash
   bz_version: integer 3 or 4 corresponding to the installation version"""
   #TODO: not assume everyone's in PST
   from lxml import etree
   import urllib #bugzilla.mozilla.org forces https which libxml2 balks at
   import datetime
   from util import warn_old

   if "arg" not in arg["qs"]:
      err(noarg)

   try:
      int(arg["qs"]["arg"])
   except:
      err("Bug IDs must be numerical.")

   if 'warn_old' not in arg:
      arg["warn_old"] = True

   #>implying there are good programmers outside of PST
   def pseudo_rfc3339(s):
      bits = s.split()
      return bits[0] + "T" + bits[1] + "-07:00"

   base_url = arg["url"]
   bugid = arg["qs"]["arg"]
   url = '%s/show_bug.cgi?id=%s' % (base_url, bugid)
   rval = {"id": url,
           "link": url,
           "entries": []}
   if "lang" in arg["qs"]:
      rval["lang"] = arg["qs"]["lang"]

   try:
      tree = etree.parse(urllib.urlopen(url), etree.HTMLParser(encoding="UTF-8"))
   except:
      err(badfetch)

   comments = tree.xpath("//div[contains(@class, 'bz_comment')]")
   if len(comments) == 0: err(badparse)

   rval["title"] = tree.xpath('/html/head/title')[0].text

   for e in tree.xpath('//pre[@class="bz_comment_text"]'):
      e.attrib["style"] = "white-space:pre-wrap"

   for comment in comments:
      if arg["version"] == 4:
         link = url + "#" + comment.attrib['id']
         time = comment.xpath("div/span[@class='bz_comment_time']")[0].text.strip("\n ")
         pseudo = pseudo_rfc3339(time)
         fn = comment.xpath("div/span/span/span[@class='fn']")
         if len(fn) == 1:
            name = fn[0].text
         else: #user didn't give a full name to bugzilla
            name = comment.xpath("div/span/span")[0].text[:-1] #random newline
         title = "Comment %s - %s - %s" % (comment.attrib["id"][1:], name, time)
         content = etree.tostring(comment.xpath("pre[@class='bz_comment_text']")[0])

      if arg["version"] == 3:
         link = base_url + "/" + comment.xpath("span/i/a")[0].attrib['href']
         time = comment.xpath("span/i/span")[0].tail.strip("\n ")
         pseudo = pseudo_rfc3339(time)
         name = comment.xpath("span/i/span/a")[0].text # everyone always has a name
         title = "Comment %s - %s - %s" % (comment.xpath("span/i/a")[0].attrib["name"][1:], name, time)
         content = etree.tostring(comment.xpath("pre")[0])

      entry = {"id": link,
               "title": title,
               "content": content,
               "content_type": "html",
               "author": name,
               "updated": pseudo,
               "published": pseudo,
               "link": link}
      rval["entries"].append(entry)
      rval["updated"] = pseudo #the last updated time of the global feed is the post time of the last comment... for now
   if arg["warn_old"] and datetime.datetime.strptime(rval["updated"][:-6], "%Y-%m-%dT%H:%M:%S") < (datetime.datetime.utcnow() - datetime.timedelta(days=365)):
      rval["entries"].append(warn_old(url, bugid))
   return rval

def gelbooru(arg):
   from lxml import etree

   if "arg" not in arg["qs"]:
      err(noarg)

   tag = arg["qs"]["arg"]
   url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%s' % tag
   rval = {"id": url,
           "title": "%s - Gelbooru" % tag,
           "author": "Gelbooru",
           "link": url,
           "lang": "en",
           "entries": []}

   try:
      tree = etree.parse(url, etree.HTMLParser(encoding="UTF-8"))
   except:
      err(badfetch)
   posts = tree.xpath('//div[@class="content"]/div[2]/span')
   if len(posts) == 0: err(badparse)

   for post in posts:
      post.xpath('a')[0].attrib['href'] = 'http://gelbooru.com/' + post.xpath('a')[0].attrib['href']
      title = post.xpath('a/img')[0].attrib["alt"]
      del post.xpath('a/img')[0].attrib["alt"]
      del post.xpath('a/img')[0].attrib["title"]
      entry = {"id": post.xpath('a')[0].attrib["href"],
               "title": title,
               "content": etree.tostring(post.xpath('a')[0]),
               "content_type": "html",
               "link": post.xpath('a')[0].attrib["href"]}
      rval["entries"].append(entry)
   return rval

def hackernews_comments(arg):
   if "arg" not in arg["qs"]:
      err(noarg)
   else:
      username = arg["qs"]["arg"]
   userpage = 'http://news.ycombinator.com/threads?id=%s' % username
   rval = {"id": userpage,
           "title": "%s's comments - Hacker News" % username,
           "author": username,
           "lang": "en",
           "link": userpage,
           "entries": []}

   from lxml import etree

   link = lambda e: 'http://news.ycombinator.com/' + e.xpath('div/span[@class="comhead"]/a[2]')[0].attrib['href']
   post = lambda e: etree.tostring(list(e.xpath('span[1]')[0])[0], encoding='UTF-8') #get rid of <span class="comment">

   try:
      tree = etree.parse('http://news.ycombinator.com/threads?id=%s' % username, etree.HTMLParser(encoding="UTF-8"))
   except:
      err(badfetch)
   user_comments = tree.xpath('/html/body/center/table/tr/td/table/tr/td[div/span/a = "%s"]' % username)
   if len(user_comments) == 0: err(badparse)

   links = [link(e) for e in user_comments]
   posts = [post(e) for e in user_comments]
   if len(links) != len(user_comments) or len(posts) != len(user_comments): err(badparse)

   for comment in zip(links, posts):
      entry = {"id": comment[0],
               "link": comment[0],
               "title": "%s's comment" % username,
               "content": comment[1].decode('UTF-8'),
               "content_type": "html"}
      rval["entries"].append(entry)
   return rval
