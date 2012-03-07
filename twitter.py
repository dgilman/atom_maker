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
from util import badfetch
from util import rfc3339
import datetime
from tweepy.error import TweepError
import re


def htmlize(m):
    return '<a href="%s">%s</a>' % (m.group(1), m.group(1))

regex = re.compile("(https?://[^\s\n]+)")
def link(s):
   return re.sub(regex, htmlize, s)

def format_tweet(username, realname, tweet, tweet_url, time):
   return  """@%(username)s / %(realname)s<br/>
%(tweet)s<br/>
<a href="%(tweet_url)s">%(time)s</a><br/>
<br/>
""" % {"username": username, "realname": realname, "tweet": link(tweet), "tweet_url": tweet_url, "time": time.strftime("%A, %B %d, %Y %H:%M:%S")}

class Twitter:
   def __init__(self, db=None, oauth=False, token_name=None, infinite_retries=True):
      import tweepy

      handler = None
      self.infinite_retries = infinite_retries

      if oauth:
         if db == None:
            err("OAuth needs the DB cursor")
         try:
            token = db.execute("select key, secret from twitter_tokens where name = ?", (token_name,)).fetchall()[0]
         except:
            err("Your twitter tokens are nowhere to be found.  Try running get_twitter_tokens.py")
         handler = tweepy.auth.OAuthHandler('uX9gm761EDZqilGvwCd0bA', '1Ee8KV2vqZDzuM2uXWJwL8IsIVufxwkbWlEOKTA4', secure=True)
         handler.set_access_token(token[0], token[1])
      self.api = tweepy.API(handler)
      if not self._retry(self.api.test, {}):
         err("Sanity check failed.  Your OAuth tokens might be bad.")

   def user_timeline(self, username):
      try:
         return self._retry(self.api.user_timeline, {"include_rts": True, "count": 40, "screen_name": username})
      except TweepError as e:
         err("Twitter: %s" % e.reason)

   def get_tweet(self, tid):
      return self._retry(self.api.get_status, {"id": tid})

   def mentions(self):
      if not self.api.auth:
         err("user_mentions requires OAuth")
      return self._retry(self.api.mentions, {"count": 40, "include_rts": True})

   def me(self):
      if not self.api.auth:
         err("You tried to get the profile of the authenticated user when unauthenticated.")
      return self._retry(self.api.me, {})

   # catch twitter's frequent 503s and spin endlessly on them
   def _retry(self, func, args):
      while True:
         try:
            rval = func(**args)
         except TweepError as e:
            if e.response.status == 503 and self.infinite_retries:
               continue
            else:
               raise e
         return rval
