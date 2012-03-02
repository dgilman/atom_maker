#!/usr/bin/env python
import tweepy
from tweepy.error import TweepError

import schema

conn, c = schema.init()

print "Browse to this URL to authenticate with twitter."
handler = tweepy.auth.OAuthHandler('uX9gm761EDZqilGvwCd0bA', '1Ee8KV2vqZDzuM2uXWJwL8IsIVufxwkbWlEOKTA4', secure=True)

print handler.get_authorization_url()

while True:
   try:
      verify = raw_input("Activation code > ")
      token = handler.get_access_token(verifier=verify)
      break
   except TweepError:
      print "Try again."

api = tweepy.API(handler)
if not api.test():
   print "Sanity test failed"
   import sys
   sys.exit()

name = raw_input("What name do you want to give this token? ")

c.execute("insert into twitter_tokens (name, key, secret) values (?, ?, ?)", (name, token.key, token.secret))
conn.commit()
conn.close()
