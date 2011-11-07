# vim: ts=3 et sw=3 sts=3:

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

def bmo(arg):
   from lxml import etree
   import urllib #bugzilla.mozilla.org forces https which libxml2 balks at
   from textwrap import fill
   url = 'https://bugzilla.mozilla.org/show_bug.cgi?id=%s' % arg
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
               "link": "https://bugzilla.mozilla.org/%s" % comment.xpath("div/span/a")[0].attrib["href"]}
      rval["entries"].append(entry)
      rval["updated"] = pseudo #the last updated time of the global feed is the post time of the last comment... for now
   return rval

def gelbooru(arg):
   from lxml import etree
   url = 'http://gelbooru.com/index.php?page=post&s=list&tags=%s' % arg
   rval = {"id": url,
           "title": "%s - Gelbooru" % arg,
           "author": "Gelbooru",
           "link": url,
           "entries": []}

   tree = etree.parse(url, etree.HTMLParser())
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
   """arg is a string (the username)"""
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
   "bmo": bmo
}
