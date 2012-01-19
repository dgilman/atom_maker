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
from util import badfetch
from util import rfc3339
import datetime
from tweepy.utils import parse_datetime

def format_tweet(username, realname, tweet, tweet_url, time):
   return  """@%s / %s<br/>
%s<br/>
<a href="%s">%s</a><br/>
<br/>
""" % (username, realname, tweet, tweet_url, time.strftime("%A, %B %d, %Y %H:%M:%S"))

class Object(object): pass

def populate_obj(d):
   o = Object()
   for k,v in d.iteritems():
      if k == "created_at": v = parse_datetime(v)
      if isinstance(v, dict):
         setattr(o, k, populate_obj(v))
      else:
         setattr(o, k, v)
   return o

def fake_object(tweet): # The car's on fire and there's no driver at the wheel
   if "error" in tweet:
      return None
   return populate_obj(tweet)

class TwitterProxy:
   def __init__(self, db=None, oauth=False, token_name=None):
      self.oauth = oauth
      if self.oauth:
         if db == None:
            err("OAuth needs the DB cursor")
         import tweepy
         try:
            self.token = db.execute("select key, secret from twitter_tokens where name = ?", (token_name,)).fetchall()[0]
         except:
            err("Your twitter tokens are nowhere to be found.  Try running get_twitter_tokens.py")
         # unbreakable encryption
         self.handler = tweepy.auth.OAuthHandler('Ab0dCwvGliqZDE167mg9Xu'[::-1], '4ATKOElWbkwxfuVIsI8LwJWXu2MuzDZqv2VK8eE1'[::-1], secure=True)
         self.handler.set_access_token(self.token[0], self.token[1])
         self.api = tweepy.API(self.handler)
         if not self.api.test():
            err("Couldn't get the twitter tokens to work.")

   def user_timeline(self, username):
      if self.oauth:
         try:
            return self.api.user_timeline(include_rts=True, screen_name=username)
         except:
            err("You can't see that user's timeline.")
      else:
         import json
         import urllib
         rval = []
         try:
            tweets = json.load(urllib.urlopen("https://api.twitter.com/1/statuses/user_timeline.json?screen_name=%s&include_rts=true" % username), encoding="UTF-8")
         except:
            err("You can't see that user's timeline.  The Twitter API might also be down.")
         # there is no need to check for "error" as urllib will throw an exception in that case and we won't get this far
         for tweet in tweets:
            rval.append(fake_object(tweet))
         return rval

   def get_tweet(self, tid):
      """CHECK THE RETURN VALUE!  Returns None if the tweet can't be read."""
      if self.oauth:
         try:
            return self.api.get_status(id=tid)
         except:
            return None
      else:
         import json
         import urllib
         try:
            result = json.load(urllib.urlopen("https://api.twitter.com/1/statuses/show/%s.json" % tid), encoding="UTF-8")
         except:
            err(badfetch)
         return fake_object(result)

   def mentions(self):
      if not self.oauth:
         err("user_mentions requires OAuth")
      return self.api.mentions(count=40, include_rts=True)
