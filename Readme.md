# SQLite Directory FS

A FUSE filesystem to allow reading a SQLite3 Database as a set of folders and files.

```sh
# Install fuse
sudo apt install -y fuse

# Install python dependencies
pip install --user fuse-python==1.0.9
pip install --user cachetools==5.5.2

# Mount a database at a mount_point
python sqlitedir.py <mount_point> -o db=<db.sqlite>

# Unmount the filesystem
fusermount -u <mount_point>
```

The directory structure of the mounted directory looks like below. Each table in the database is represented as a directory at the root, within which each field (column) of the table is represented as a nested directory. Inside the directory corresponding to each field, files representing the distinct values of that field are shown.

```
├── table1
├── table2
└── table3
    ├── field1-of-table3
    ├── field2-of-table3
    └── field3-of-table3
        ├── distinct-value1-of-field3-of-table3
        ├── distinct-value2-of-field3-of-table3
        └── distinct-value3-of-field3-of-table3
```

Reading the files will return the rows in that table which matches with that field value. The data is returned as a JSON value.

```sh
cat mount/students/name/nihaal
# Equivalent to SELECT * FROM students WHERE name = 'nihaal'
```

### Note

The filesystem is written only for reading data from a static (not changing) sqlite3 database. It uses caching and so if the database was modified while the script is executing, it may show an older view.
