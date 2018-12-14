from bencode3 import bdecode

print('starting:')

# with open('test.torrent', 'rb') as torrent_file:
#     for i, line in enumerate(torrent_file):
#         print(i)
#         print(line)
#         try:
#             s = bdecode(line)
#         except UnicodeDecodeError:
#             print(s)


with open('test.torrent', 'rb') as torrent_file:
    data = torrent_file.read()
    print(data[:200])

    s = bdecode(data)
    print(type(s))
    print(s.keys())

    print(s['info'].keys())
    print(s['info']['length'])
    print(s['info']['piece length'])
    print(len(s['info']['pieces']))
    print(s['info']['piece length'] * len(s['info']['pieces']))
