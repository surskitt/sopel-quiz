#!/usr/bin/env python

import os
import sqlite3

dbfile = '{}/.sopel/default.db'.format(os.environ.get('HOME'))
conn = sqlite3.connect(dbfile)
c = conn.cursor()
c.execute('DELETE FROM nick_values WHERE key = "quiz_wins"')
conn.commit()
conn.close()
