#!/usr/bin/env python
#
# SqlitedirFS : A FUSE filesystem to allow reading a SQLite3 Database
# as a set of folders and files
#
# Author  : Abdun Nihaal
# License : GPLv2
import os
import stat
import json
import errno
import sqlite3
import fuse
from fuse import Fuse, Stat
fuse.fuse_python_api = (0, 2)

class FileStat(Stat):
    def __init__(self, size):
        self.st_mode = stat.S_IFREG | 0o444
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 1
        self.st_uid = 1000
        self.st_gid = 1000
        self.st_size = size
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

class FolderStat(Stat):
    def __init__(self):
        self.st_mode = stat.S_IFDIR | 0o755
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 1000
        self.st_gid = 1000
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

# Sqlite functions
dbname = None

def get_tables():
    global dbname
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    tables = []
    for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        tables.append(row[0])
    return tables
    
# FIXME Prevent SQL injection in the SQL queries
def get_table_fields(table):
    global dbname
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    fields = []
    for row in cursor.execute("SELECT name FROM pragma_table_info('"+ table + "')"):
        fields.append(row[0])
    return fields
    
def get_table_field_values(table, field):
    global dbname
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    values = []
    for row in cursor.execute("SELECT DISTINCT " + field + " FROM "+ table):
        values.append(row[0])
    return values

# FIXME Return data as a JSON dict with the correct field names as keys
def get_table_field_value_data(table, field, value):
    global dbname
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    rows = list(cursor.execute("SELECT * FROM " + table + " WHERE " + field + "='" + value + "'" ))
    return json.dumps(rows, indent=4)

def explode_path(path):
    if path == "/":
        return (None, None, None)
    data = path.split("/")
    table = None
    field = None
    value = None
    if len(data) == 4:
        value = data[3]
        if value == '.':
            value = None
    if len(data) >= 3:
        field = data[2]
        if field == '.':
            field = None
    if len(data) >= 2:
        table = data[1]
        if table == '.':
            table = None
    return (table, field, value)

class SqlitedirFS(Fuse):
    def getattr(self, path):
        table, field, value = explode_path(path)
        if not table:
            return FolderStat()
        elif table and not field:
            if table in get_tables():
                return FolderStat()
            return -errno.ENOENT
        elif table and field and not value:
            if table in get_tables():
                if field in get_table_fields(table):
                    return FolderStat()
            return -errno.ENOENT
        elif table and field and value:
            if table in get_tables():
                if field in get_table_fields(table):
                    if value in get_table_field_values(table, field):
                        size = len(get_table_field_value_data(table, field, value))
                        return FileStat(size)
            return -errno.ENOENT

    def readdir(self, path, offset):
        yield fuse.Direntry('.')
        yield fuse.Direntry('..')
        table, field, value = explode_path(path)
        if not table:
            for table in get_tables():
                yield fuse.Direntry(table)
        elif table and not field:
            for field in get_table_fields(table):
                yield fuse.Direntry(field)
        elif table and field and not value:
            for value in get_table_field_values(table, field):
                yield fuse.Direntry(value)

    def open(self, path, flags):
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES
        table, field, value = explode_path(path)
        if not table:
            return 0
        elif table and not field:
            if table in get_tables():
                return 0
            return -errno.ENOENT
        elif table and field and not value:
            if table in get_tables():
                if field in get_table_fields(table):
                    return 0
            return -errno.ENOENT
        elif table and field and value:
            if table in get_tables():
                if field in get_table_fields(table):
                    if value in get_table_field_values(table, field):
                        return 0
            return -errno.ENOENT

    def read(self, path, size, offset):
        table, field, value = explode_path(path)
        if table and field and value:
            if table in get_tables():
                if field in get_table_fields(table):
                    if value in get_table_field_values(table, field):
                        data = bytes(get_table_field_value_data(table, field, value),
                                     'utf-8')
                        datalen = len(data)
                        if offset < datalen:
                            if offset + size > datalen:
                                size = datalen - offset
                            buf = data[offset:offset+size]
                        else:
                            buf = b''
                        return buf
        return -errno.ENOENT

def main():
    usage="""Sqlitedir FUSE filesystem
        Usage: python sqlitedir.py <mount_point> -o db=<db.sqlite>
        """ + Fuse.fusage
    server = SqlitedirFS(version="%prog " + fuse.__version__,
                         usage=usage,
                         dash_s_do='setsingle')
    server.parser.add_option(mountopt="db", metavar="PATH",
                             help="Sqlite3 Database file to mount")
    server.parse(values=server, errex=1)
    try:
        print("Mounting database " + server.db, end = ' ')
    except:
        print("Specify Database file with -o db=<db.sqlite>")
        exit(0)

    if (server.db):
        # Open the Sqlite3 database
        global dbname
        dbname = server.db
        server.main()
    else:
        print (usage)

if __name__ == '__main__':
    main()
