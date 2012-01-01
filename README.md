Deps: lxml (python-lxml in debian)

atom_maker generates Atom feeds out of pages that do not have them.  It comes out of the box with code for Hacker News comments, Gelbooru tag searches, Bugzilla bugs, Blogspot blogs and special Twitter feed code to strip away @replies.  Implementing code for a new site is easy.

Setup
-----
Take a look at generators.py to see what sites are available and what arguments the code takes.  Configure your feeds in prefs.py and browse to am.py to see your new feed!  Most users can get away with copying prefs.py.example over.

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
