class ConnectionHandler:
    def __init__(self, local_peer_id: int, remote_peer_id: int = None, sock=None):
        self.local_peer_id = local_peer_id
        self.remote_peer_id = remote_peer_id
        self.sock = sock

        self.is_connected = sock is not None
        self.am_choked = True
        self.peer_is_choked = True
        self.peer_is_interested = False
        self.am_interested = False

    def set_remote_peer_id(self, remote_peer_id: int) -> None:
        self.remote_peer_id = remote_peer_id

    def attach_socket(self, sock) -> None:
        self.sock = sock
        self.is_connected = True

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        self.is_connected = False

    def summary(self) -> dict:
        return {
            "local_peer_id": self.local_peer_id,
            "remote_peer_id": self.remote_peer_id,
            "is_connected": self.is_connected,
            "am_choked": self.am_choked,
            "peer_is_choked": self.peer_is_choked,
            "peer_is_interested": self.peer_is_interested,
            "am_interested": self.am_interested,
        }

    def __repr__(self) -> str:
        return (
            f"ConnectionHandler(local_peer_id={self.local_peer_id}, "
            f"remote_peer_id={self.remote_peer_id}, "
            f"is_connected={self.is_connected})"
        )
