# P2P Chat — Network Programming Project

This is a simple **peer-to-peer messenger** compatible with the basic XMPP
`<message>` stanza format required by the course.

## Features
- Listens on port **5299**
- Contacts are defined as `nick@ip`
- Automatically reconnects to peers every 5 seconds
- Shows online/offline status
- Exchanges XML messages:
  ```xml
  <message from="alice" to="bob@192.168.1.20">
      Hello Bob!
  </message>
