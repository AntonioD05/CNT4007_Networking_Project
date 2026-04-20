````md
## Demo Setup and How We Ran the Final Video Demo

### Group Members
- Antonio Diaz
- Johnson Nguyen

### Demo Environment
For the final demo, we ran the project on **multiple machines**, as required. We used:
- **Windows laptop**: ran peer `1001` and peer `1002`
- **Mac laptop**: ran peer `1003`

Both machines were connected to the **same Wi-Fi network**.

### Demo File
For the final demo, we used a file larger than **20 MB** and set the piece size to **16384 bytes**, which matches the demo requirements. 

### Configuration Files Used

#### Common.cfg
Our final demo `Common.cfg` used:
- `NumberOfPreferredNeighbors = 1`
- `UnchokingInterval = 5`
- `OptimisticUnchokingInterval = 10`
- `FileName = thefile`
- `FileSize = 21103795`
- `PieceSize = 16384`

The demo requirements specify a file of at least **20 MB** and a piece size of **16384 bytes**. 

#### PeerInfo.cfg
For the multi-machine demo, we used the following layout:

- Peer `1001` on the Windows machine
- Peer `1002` on the Windows machine
- Peer `1003` on the Mac machine

Example format:

```txt
1001 [WINDOWS_IP] 6001 1
1002 [WINDOWS_IP] 6002 0
1003 [MAC_IP] 6003 0
```

Only peer `1001` started with the complete file. Peers `1002` and `1003` started without the file.

### Peer Directories

We used the required peer subdirectories:

* `peer_1001/`
* `peer_1002/`
* `peer_1003/`

Before starting the demo:

* `peer_1001/` contained the complete source file
* `peer_1002/` and `peer_1003/` did not contain the complete file

This matches the project requirement that peer-specific files be stored in `peer_[peerID]` subdirectories. 

### How We Started the Peers

We started the peers in the order listed in `PeerInfo.cfg`, as required by the project description. 

#### On Windows

We opened two terminals and ran:

```bash
python peerProcess.py 1001
python peerProcess.py 1002
```

#### On Mac

We opened one terminal and ran:

```bash
python3 peerProcess.py 1003
```

### Runtime Behavior Demonstrated

During the demo, our program showed the following required behavior:

* TCP connections were established between peers
* handshake messages were exchanged first
* bitfield messages were exchanged after handshaking
* peers sent `interested` and `not interested` messages based on available pieces
* preferred neighbors were selected periodically
* optimistic unchoking was performed periodically
* peers exchanged `request`, `piece`, and `have` messages
* peers downloaded and reconstructed the complete file
* peers generated log files named `log_peer_[peerID].log`
* all peers terminated after the swarm completed

These behaviors follow the protocol and implementation specifics described in the project specification. 

### Verification

At the end of the demo:

* the transferred file appeared in `peer_1002/` and `peer_1003/`
* we verified file integrity by comparing the downloaded files with the original file
* the peers detected that all peers had the complete file and shut down cleanly

### Demo Recording

We recorded the final demo as a video showing:

* the configuration files
* the initial peer folders
* peers running on multiple machines
* file transfer progress
* final downloaded files
* clean termination

This was done to satisfy the recorded video demo requirement. 

Here is the link: https://youtu.be/VB_tCduUNE8
Github Repo: https://github.com/AntonioD05/CNT4007_Networking_Project
````