import os
from client import Client
from torrent import TorrentError

# TODO: Handle problem if tracker is unavailable.

# TODO: Store Partial File Download? Perhaps just completed pieces - But
#       allow for reinitiailzation on Torrent load

# TODO: Control file download process more closely.
# TODO: Open ourselves up for proactive seed connections.

# TODO: Good documentation in files.

# Files Examined:
# 1. Client
# 2. Torrent
# 3. Piece
# 4. Message
# 5. Peer

client = Client()

print(" __              __")
print("|  \\  __    __  |  \\  __  __   __")
print("|__/ |   | |__| |__/ |   |__| |__|")
print("           |                  |")
print("")
print("")

def get_and_assign_file():
    file_name = input(".torrent file: ")

    if os.path.splitext(file_name)[-1] != '.torrent':
        print("Must be .torrent file")
        get_and_assign_file()
    try:
        client.add_torrent(file_name)
    except TorrentError as e:
        print(e)
        get_and_assign_file()

get_and_assign_file()
client.start_torrent()





