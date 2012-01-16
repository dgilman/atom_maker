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

from util import create_error_feed as err
badparse = "The page couldn't be parsed properly.  It's likely that the page's markup has changed and your atom_maker needs to be updated."
badfetch = "The page couldn't be fetched.  The website might be down."

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
#(optional) lang: xml:lang attribute value for the entire feed.
#entries: list of dicts of entries (described below)

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
#(optional) lang: xml:lang attribute value for this entry.

def twitter_context(arg, lang=None):
   """arg: twitter username
   lang: optional xml:lang human language for content
   Create a feed giving context to a user's replies."""
   import json
   import urllib
   from util import rfc3339
   import datetime

   # Unfortunately this is locale dependent.  Fuck twitter's api.
   ts = lambda x: rfc3339(datetime.datetime.strptime(x, '%a %b %d %H:%M:%S +0000 %Y'))

   def format_tweet(username, realname, tweet, tweet_url, time):
      return  """@%s / %s<br/>
%s<br/>
<a href="%s">%s</a><br/>
<br/>
""" % (username, realname, tweet, tweet_url, time)

   try:
      tweets = json.load(urllib.urlopen("http://api.twitter.com/1/statuses/user_timeline.json?screen_name=%s" % arg), encoding="UTF-8")
   except:
      err(badfetch)
   if "error" in tweets:
      err(tweets["error"])

   tweet_cache = {}
   for tweet in tweets:
      tweet_cache[tweet['id_str']] = tweet

   rval = {"id": "http://twitter.com/%s#atom_maker_context_feed" % arg,
           "link": "http://twitter.com/%s" % arg,
           "title": "Twitter / %s / context" % arg,
           "author": tweets[0]["user"]["name"],
           "entries": []}

   if lang:
      rval["lang"] = lang

   parent_skip_list = set()
   for tweet in tweets:
      if tweet['id'] in parent_skip_list:
         continue

      content = []
      tweet_url = "http://twitter.com/%s/status/%s" % (arg, tweet["id_str"])

      entry = {"id": tweet_url,
               "title": "%s: " % arg + tweet["text"],
               "content_type": "html",
               "updated": ts(tweet["created_at"]),
               "link": tweet_url}
      content.append(format_tweet(tweet["user"]["screen_name"], tweet["user"]["name"], tweet["text"], tweet_url, tweet["created_at"]))
      if tweet["in_reply_to_status_id"] is not None:
         parent_id = tweet["in_reply_to_status_id_str"]
         while True:
            if parent_id in tweet_cache:
               parent_tweet = tweet_cache[parent_id]
            else:
               try:
                  parent_tweet = json.load(urllib.urlopen("http://api.twitter.com/1/statuses/show/%s.json" % parent_id), encoding="UTF-8")
                  tweet_cache[parent_id] = parent_tweet
               except:
                  err(badfetch)
            # Hitting the API limits mid-feed just leaves you with a half-fleshed out feed
            # This actually happened to me once
            if 'error' in parent_tweet:
               break

            # don't make a new RSS entry for tweets in a conversation chain
            if parent_tweet['user']['id'] == tweet['user']['id']:
               parent_skip_list.add(parent_tweet["id"])

            content.append(format_tweet(parent_tweet["user"]["screen_name"], parent_tweet["user"]["name"], parent_tweet["text"], "http://twitter.com/%s/status/%s" % (parent_tweet["user"]["screen_name"], parent_id), parent_tweet["created_at"]))

            # either crawl up the chain to the next parent or break out of this loop, finishing this RSS entry
            if parent_tweet["in_reply_to_status_id"] is not None:
               parent_id = parent_tweet["in_reply_to_status_id_str"]
            else:
               break
      entry["content"] = "".join(reversed(content))
      rval["entries"].append(entry)
   rval["updated"] = rval["entries"][0]["updated"] # first tweet is newest
   return rval

def blogspot(arg, lang=None):
   """Some users don't have RSS feeds turned on.  why_would_you_do_that.jpg"""
   from lxml import etree

   url = 'http://%s.blogspot.com' % arg
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

   if lang:
      rval["lang"] = lang

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

def twitter_noreply(username):
   """Strips out @replies from a user's twitter feed.
   username is case-sensitive!  It needs to be the same case as the user has on twitter.com"""
   # At some point https://dev.twitter.com/discussions/2690 will be fixed, making this function unnecessary
   from lxml import etree
   import sys
   import urllib

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

def redhat_sources_bz(arg, history=True, ccs=False):
   return _bz_xmlrpc(arg, 'http://sourceware.org/bugzilla', history, ccs, lang="en")

def bmo(arg, history=True, ccs=False):
   return _bz_xmlrpc(arg, 'https://bugzilla.mozilla.org', history, ccs, lang="en")

def webkit(arg):
   return _bz_screenscrape(arg, 'https://bugs.webkit.org', 3, lang="en")

def _bz_xmlrpc(arg, url, history=True, ccs=False, lang=None):
   """arg: bug id as string
   url: path to bugzilla installation
   history: put history changes in feed (optional, default true)
   ccs: include cc changes in history (optional, default false)"""
   import xmlrpclib
   import sqlite3
   import datetime
   now = datetime.datetime.utcnow()
   from util import rfc3339

   p = xmlrpclib.ServerProxy(url + "/xmlrpc.cgi", use_datetime=True)

   try:
      bugdata = p.Bug.get({"ids":[arg], "permissive": True})
   except:
      err(badfetch)
   if len(bugdata['faults']) > 0: err(bugdata['faults'][0]['faultString'])
   bugdata = bugdata["bugs"][0]

   guid = '%s/show_bug.cgi?id=%s' % (url, str(bugdata['id'])) # get the ID in case the query string used the bug alias
   rval = {"id": guid,
           "link": guid,
           "updated": rfc3339(bugdata['last_change_time']),
           "title": "Bug %s - " % arg + bugdata['summary'],
           "entries": []}

   if lang:
      rval["lang"] = lang

   try:
      bugcomments = p.Bug.comments({"ids":[arg]})["bugs"][arg]['comments']
   except:
      err(badfetch)

   commenting_users = [x['author'] for x in bugcomments]
   if history:
      try:
         bug_history = p.Bug.history({"ids":[arg]})['bugs'][0]['history']
      except:
         err(badfetch)
      commenting_users.extend([h['who'] for h in bug_history])

   conn = sqlite3.connect("cache.sqlite3")
   c = conn.cursor()
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

   for comment_no, comment in enumerate(bugcomments):
      comment_id = guid + "#c" + str(comment_no)
      real_name = rn(comment['author'])
      comment_time_str = rfc3339(comment['time'])
      entry = {"id": comment_id,
               "title": u"Comment %s - %s - %s" % (str(comment_no), real_name, comment_time_str),
               "content": '<pre style="white-space:pre-wrap">' + comment['text'] + "</pre>",
               "content_type": "html",
               "author": real_name,
               "updated": comment_time_str,
               "published": comment['time'], # keep for sorting
               "link": comment_id}
      rval["entries"].append(entry)

   # finally done with the db
   conn.commit()
   conn.close()

   rval["entries"].sort(key=lambda e: e["published"])
   for entry in rval["entries"]:
      entry["published"] = rfc3339(entry["published"])

   return rval

def _bz_screenscrape(arg, url, bz_version, lang=None):
   """arg: bug id as string
   url: path to bugzilla installation without slash
   bz_version: integer 3 or 4 corresponding to the installation version"""
   #TODO: not assume everyone's in PST
   from lxml import etree
   import urllib #bugzilla.mozilla.org forces https which libxml2 balks at
   base_url = url
   url = '%s/show_bug.cgi?id=%s' % (url, arg)
   rval = {"id": url,
           "link": url,
           "entries": []}
   if lang:
      rval["lang"] = lang
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
      if bz_version == 4:
         link = url + "#" + comment.attrib['id']
         time = comment.xpath("div/span[@class='bz_comment_time']")[0].text.strip("\n ")
         timebits = time.split()
         pseudo = timebits[0] + "T" + timebits[1] + "-07:00" #pseudo rfc3339
         fn = comment.xpath("div/span/span/span[@class='fn']")
         if len(fn) == 1:
            name = fn[0].text
         else: #user didn't give a full name to bugzilla
            name = comment.xpath("div/span/span")[0].text[:-1] #random newline
         title = "Comment %s - %s - %s" % (comment.attrib["id"][1:], name, time)
         content = etree.tostring(comment.xpath("pre[@class='bz_comment_text']")[0])

      if bz_version == 3:
         link = base_url + "/" + comment.xpath("span/i/a")[0].attrib['href']
         time = comment.xpath("span/i/span")[0].tail.strip("\n ")
         timebits = time.split()
         pseudo = timebits[0] + "T" + timebits[1] + "-07:00"
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
   return rval

def gelbooru(arg):
   """Gets the latest posts for a given tag query.  Arg is the query"""
   from lxml import etree
   url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%s' % arg
   rval = {"id": url,
           "title": "%s - Gelbooru" % arg,
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
   """Gets the comments of a hacker news user.  arg is a string (the username)"""
   rval = {"id": 'http://news.ycombinator.com/threads?id=%s' % arg,
           "title": "%s's comments - Hacker News" % arg,
           "author": arg,
           "lang": "en",
           "link": 'http://news.ycombinator.com/threads?id=%s' % arg,
           "entries": []}

   from lxml import etree

   link = lambda e: 'http://news.ycombinator.com/' + e.xpath('div/span[@class="comhead"]/a[2]')[0].attrib['href']
   post = lambda e: etree.tostring(list(e.xpath('span[1]')[0])[0], encoding='UTF-8') #get rid of <span class="comment">

   try:
      tree = etree.parse('http://news.ycombinator.com/threads?id=%s' % arg, etree.HTMLParser(encoding="UTF-8"))
   except:
      err(badfetch)
   user_comments = tree.xpath('/html/body/center/table/tr/td/table/tr/td[div/span/a = "%s"]' % arg)
   if len(user_comments) == 0: err(badparse)

   links = [link(e) for e in user_comments]
   posts = [post(e) for e in user_comments]
   if len(links) != len(user_comments) or len(posts) != len(user_comments): err(badparse)

   for comment in zip(links, posts):
      entry = {"id": comment[0],
               "link": comment[0],
               "title": "%s's comment" % arg,
               "content": comment[1].decode('UTF-8'),
               "content_type": "html"}
      rval["entries"].append(entry)

   return rval
