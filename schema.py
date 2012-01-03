# How to update the database schema
# 1. Create a new function that takes a sqlite3 db connection as an argument.
# 2. Have the function update schema and increase the user version, preferrably in a transaction
# 3. Put your function in the upgrade dict in check().  Its key is the schema version it is upgrading from.
# 4. Increase SCHEMA_VERSION at the top of this file
# 5. Submit a pull request!

SCHEMA_VERSION = 1

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

def check(c):
   upgrade = {0: create_initial_format}
   ver = c.execute("pragma user_version").fetchall()[0][0]
   while ver < SCHEMA_VERSION:
      upgrade[ver](c)
      ver += 1