# How to update the database schema
# 1. Create a new function that takes a sqlite3 db connection as an argument.
# 2. Have the function update schema and increase the user version, preferrably in a transaction
# 3. Put your function in the upgrade dict in check().  Its key is the schema version it is upgrading from.
# 4. Increase SCHEMA_VERSION at the top of this file
# 5. Submit a pull request!

SCHEMA_VERSION = 4

def create_initial_format(c):
   """Schema ver 0 to 1
   create tables for main cache and bugzilla real name cache"""
   c.executescript("""BEGIN TRANSACTION;
create table if not exists cache (qs text primary key, ts timestamp, feed text);
create table if not exists bugzillas (id integer primary key, url text unique);
create table if not exists bugzilla_users (email text, name text, ts integer, bz integer, foreign key(bz) references bugzillas(id));
create index if not exists bugzilla_user_ts_index on bugzilla_users (ts asc);
pragma user_version = 1;
END TRANSACTION;""")

def create_bugzilla_email_index(c):
   """Create an index for the monster cache miss query.  Rename bugzilla_user -> bugzilla_users"""
   c.executescript("""BEGIN TRANSACTION;
drop index if exists bugzilla_user_ts_index;
create index if not exists bugzilla_users_ts_index on bugzilla_users (ts asc);
create index if not exists bugzilla_users_bz_email_index on bugzilla_users (bz, email);
pragma user_version = 2;
END TRANSACTION;""")

def create_twitter_tokens_table(c):
   """Creates a table to store marshalled twitter tokens"""
   c.executescript("""BEGIN TRANSACTION;
create table if not exists twitter_tokens (name text unique not null, key text not null, secret text not null);
pragma user_version = 3;
END TRANSACTION;""")

def cache_text_to_blob(c):
   """Change the cache table to store cached feeds as blob"""
   c.executescript("""BEGIN TRANSACTION;
drop table if exists cache;
create table if not exists cache (qs text primary key, ts timestamp, feed blob);
pragma user_version = 4;
END TRANSACTION;""")

def check(c):
   #XXX there is a race condition here
   upgrade = {0: create_initial_format,
              1: create_bugzilla_email_index,
              2: create_twitter_tokens_table,
              3: cache_text_to_blob}
   ver = lambda: c.execute("pragma user_version").fetchall()[0][0]
   while ver() < SCHEMA_VERSION:
      upgrade[ver()](c)
