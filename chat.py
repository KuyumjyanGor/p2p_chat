#!/usr/bin/env python3
import socket
import threading
import time
import sys
import xml.etree.ElementTree as ET

PORT = 5299
RECONNECT_INTERVAL = 5


class Contact:
    def __init__(self, nickname, host):
        self.nickname = nickname
        self.host = host
        self.socket = None
        self.online = False

    def __repr__(self):
        return f"{self.nickname}@{self.host} ({'online' if self.online else 'offline'})"


class PeerChat:
    def __init__(self, my_nick, contacts):
        self.my_nick = my_nick
        self.contacts = contacts

    # ----------------------------------------------------
    # XML message builder
    # ----------------------------------------------------
    def build_message(self, to, text):
        return (
            f'<message from="{self.my_nick}" to="{to}">\n'
            f'    {text}\n'
            '</message>\n'
        )

    # ----------------------------------------------------
    # FIXED: Incoming connection handler
    # ----------------------------------------------------
    def handle_incoming(self, conn, addr):
        peer_ip = addr[0]
        conn.settimeout(1)

        # Identify peer by IP
        peer_contact = None
        for c in self.contacts:
            if c.host == peer_ip:
                peer_contact = c
                break

        # Reject duplicate incoming connection if outgoing exists
        if peer_contact and peer_contact.socket is not None:
            conn.close()
            return

        # Accept connection as primary
        if peer_contact:
            peer_contact.socket = conn
            peer_contact.online = True
            print(f"{peer_contact.nickname} is now ONLINE (incoming)")
        else:
            print(f"Incoming unknown peer from {peer_ip}")

        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            except Exception:
                break

            if not data:
                break

            xml = data.decode().strip()
            try:
                root = ET.fromstring(xml)
                sender = root.attrib.get("from", "?")
                body = (root.text or "").strip()
                print(f"\n[{sender}] {body}")
            except Exception:
                print("Malformed XML received.")

        # Cleanup
        if peer_contact:
            print(f"{peer_contact.nickname} went OFFLINE")
            peer_contact.online = False
            peer_contact.socket = None

        conn.close()

    # ----------------------------------------------------
    # Server thread
    # ----------------------------------------------------
    def server_thread(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("", PORT))
        srv.listen()

        print(f"Listening on port {PORT}")

        while True:
            conn, addr = srv.accept()
            threading.Thread(target=self.handle_incoming, args=(conn, addr), daemon=True).start()

    # ----------------------------------------------------
    # Outgoing connector thread
    # ----------------------------------------------------
    def connector_thread(self):
        while True:
            for c in self.contacts:
                if c.socket is None:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(3)
                        sock.connect((c.host, PORT))
                        sock.settimeout(1)

                        c.socket = sock
                        c.online = True
                        print(f"{c.nickname} is now ONLINE (outgoing)")

                        threading.Thread(target=self.listen_peer, args=(c,), daemon=True).start()
                    except Exception:
                        pass

            time.sleep(RECONNECT_INTERVAL)

    # ----------------------------------------------------
    # Listen to connected peer (outgoing connection)
    # ----------------------------------------------------
    def listen_peer(self, contact):
        sock = contact.socket
        sock.settimeout(1)

        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                continue
            except Exception:
                break

            if not data:
                break

            xml = data.decode().strip()
            try:
                root = ET.fromstring(xml)
                sender = root.attrib.get("from", "?")
                body = (root.text or "").strip()
                print(f"\n[{sender}] {body}")
            except Exception:
                print("Malformed XML received.")

        print(f"{contact.nickname} went OFFLINE")
        contact.online = False
        contact.socket = None

        try:
            sock.close()
        except:
            pass

    # ----------------------------------------------------
    # Send message
    # ----------------------------------------------------
    def send_message(self, nick, text):
        for c in self.contacts:
            if c.nickname == nick:
                if c.socket:
                    stanza = self.build_message(f"{nick}@{c.host}", text)
                    c.socket.sendall(stanza.encode())
                else:
                    print(f"{nick} is offline.")
                return
        print("Unknown contact.")

    # ----------------------------------------------------
    # User input loop
    # ----------------------------------------------------
    def run(self):
        threading.Thread(target=self.server_thread, daemon=True).start()
        threading.Thread(target=self.connector_thread, daemon=True).start()

        while True:
            cmd = input("> ").strip()
            if cmd.startswith("/msg"):
                parts = cmd.split(" ", 2)
                if len(parts) == 3:
                    self.send_message(parts[1], parts[2])
                else:
                    print("Usage: /msg nickname message")
            elif cmd == "/list":
                for c in self.contacts:
                    print(c)
            elif cmd == "/quit":
                print("Exiting.")
                sys.exit(0)
            else:
                print("Commands: /msg, /list, /quit")


# --------------------------------------------------------
# Entry point
# --------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: ./chat.py mynick nick1@ip nick2@ip ...")
        sys.exit(1)

    mynick = sys.argv[1]
    contacts = []
    for entry in sys.argv[2:]:
        nick, ip = entry.split("@")
        contacts.append(Contact(nick, ip))

    PeerChat(mynick, contacts).run()
