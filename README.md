Deps: python 2.6.  Some generators have their own special dependencies, see genoptions.txt for more info.  lxml (http://lxml.de/) is needed for many.

atom_maker generates Atom feeds out of pages that do not have them.  It comes out of the box with code for Hacker News comments, Gelbooru tag searches, Bugzilla bugs, Blogspot blogs and special Twitter feed code to either provide context for @replies or strip them away.  Implementing code for a new site is easy.

Quick start
-----------
1. Copy prefs.py.example to prefs.py
2. Find what generator (backend) you want to use in prefs.py.  (example: bmo for bugzilla.mozilla.org)
3. Browse to am.py with the appropriate query string (example: am.py?gen=bmo&arg=700000&lang=en)
3a. If your generator only uses one argument (usually "arg" in the query string) you can use the "old-style" URL as a shortcut.  (example: am.py?feed=bmo_700000)

Fancy configuration
-------------------
The top of prefs.py.example explains how you can configure your generators beforehand by writing short functions.  There's documentation available for all the generators in genoptions.txt.

Creating a new generator
------------------------
The top of generator.py explains the dict generators are expected to return.  You might be interested in the Atom specification.  Choose your ID generation carefully because you probably don't want to keep any state.  If you do want to keep any state you can use the cache.sqlite3 database.  atom_maker already caches the entire feed above the generator level for 6 hours so you probably don't have much to save anyway.

For tracking down new XPath queries I play around in the Python interpreter like so:

```
>>> from lxml import etree
>>> ts = etree.tostring
>>> t = etree.parse('http://gilslotd.com', etree.HTMLParser())
>>> t.xpath('//cadadr')
[<Element cadadr at 0x42324985>, <Element cadadr at 0x414191>, ...]
#How useless!  A list of objects.
#Let's look at one to see what we got.
>>> t.xpath('//cadadr')[0]
<Element cadadr at 0x814841>
>>> ts(_)
'<cadadr>hello world</cadadr>'
#Looks good!
#Keep going until you get the list you want.
```

Why xpath?
----------
Once upon a time I had to pull out stuff from a nasty mess of HTML tables off of a page with really, really old markup.  XPath is really the best tool for the job when regex won't work.

Why did you call them generators?
---------------------------------
idk
