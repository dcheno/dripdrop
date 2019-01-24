# DripDrop - A simple BitTorrent Client

DripDrop was written as a project to gain a deeper knowledge of Python. It is not recommended as a client for actual BitTorrent use. At present, the client only downloads files from other peers and does not upload them.

![DripDrop Screenshot](https://github.com/dcheno/dripdrop/blob/master/dripdrop_sc.png)

## Requirements

DripDrop requires the following Python packages:

[Twisted](https://twistedmatrix.com/trac/)
```bash
pip3 install twisted
```

[Requests](http://docs.python-requests.org/en/master/)
```bash
pip3 install requests
```

[Bencode3](https://pypi.org/project/bencode3/)
```bash
pip3 install bencode3
```

## Running DripDrop
To run DripDrop download the files and use the command line to run dripdrop.py from the root directory:

```
python3 dripdrop.py
```

This will open an interface which will request the name of a .torrent file. This .torrent file should be stored in root directory as well.

At present, DripDrop is only known to work on Linux and to interact with Deluge and Qbittorrent clients.

## License
DripDrop is copyright 2018 Dan Chenoweth and is available under the MIT License.
