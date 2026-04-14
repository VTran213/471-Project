# 471-Project
Names and email addresses of partners:
- Add your group members here.

Programming language:
- Python

Files included:
- serv.py
- cli.py
- README.txt
- protocol_design.txt

How to execute:
1. Start the server:
   python3 serv.py <PORT>

2. Start the client:
   python3 cli.py <SERVER_MACHINE> <SERVER_PORT>

Example:
   python3 serv.py 1234
   python3 cli.py localhost 1234

Supported commands from the client prompt:
- ls
- get <file name>
- put <file name>
- quit

Protocol design summary:
- The client first opens a persistent TCP control connection to the server.
- For each data operation (ls, get, put), the client opens a listening socket on an ephemeral port.
- The client sends a control message to the server containing the command and the ephemeral data port.
- The server connects back to the client on that ephemeral port to create a temporary TCP data connection.
- Data sent on the data connection is framed as:
  [10-byte ASCII size header][payload bytes]
- The control channel is used for commands and status messages only.
- The data channel is created and torn down once per transfer.

Anything special:
- This code uses explicit send/receive loops to avoid partial-send and partial-receive issues.
- File names containing spaces are supported.
