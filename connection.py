import socket
from typing import Optional, Tuple

from handshake import build_handshake, parse_handshake, is_valid_handshake
from utils import recv_exact


class ConnectionHandler:
    def __init__(
        self,
        local_peer_id: int,
        remote_peer_id: Optional[int] = None,
        sock: Optional[socket.socket] = None,
        address: Optional[Tuple[str, int]] = None,
    ):
        self.local_peer_id = local_peer_id
        self.remote_peer_id = remote_peer_id
        self.sock = sock
        self.address = address

        self.is_connected = sock is not None
        self.handshake_completed = False

        self.am_choked = True
        self.peer_is_choked = True
        self.peer_is_interested = False
        self.am_interested = False

    def set_remote_peer_id(self, remote_peer_id: int) -> None:
        self.remote_peer_id = remote_peer_id

    def attach_socket(
        self,
        sock: socket.socket,
        address: Optional[Tuple[str, int]] = None,
    ) -> None:
        self.sock = sock
        self.address = address
        self.is_connected = True

    def connect(self, host: str, port: int, timeout: float = 5.0) -> None:
        if self.sock is not None:
            raise RuntimeError("Socket already attached to this connection")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.settimeout(None)

        self.sock = sock
        self.address = (host, port)
        self.is_connected = True

    def send_bytes(self, data: bytes) -> None:
        if self.sock is None or not self.is_connected:
            raise RuntimeError("Connection is not active")
        self.sock.sendall(data)

    def recv_bytes(self, num_bytes: int) -> bytes:
        if self.sock is None or not self.is_connected:
            raise RuntimeError("Connection is not active")

        data = self.sock.recv(num_bytes)
        if data == b"":
            raise ConnectionError("Socket connection closed by remote peer")
        return data

    def send_handshake(self) -> None:
        handshake = build_handshake(self.local_peer_id)
        self.send_bytes(handshake)

    def receive_handshake(self) -> int:
        handshake_bytes = recv_exact(self.sock, 32)

        if not is_valid_handshake(handshake_bytes):
            raise ValueError("Received invalid handshake")

        parsed = parse_handshake(handshake_bytes)
        remote_peer_id = parsed["peer_id"]
        self.remote_peer_id = remote_peer_id
        self.handshake_completed = True
        return remote_peer_id

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None
                self.is_connected = False

    def summary(self) -> dict:
        return {
            "local_peer_id": self.local_peer_id,
            "remote_peer_id": self.remote_peer_id,
            "address": self.address,
            "is_connected": self.is_connected,
            "handshake_completed": self.handshake_completed,
            "am_choked": self.am_choked,
            "peer_is_choked": self.peer_is_choked,
            "peer_is_interested": self.peer_is_interested,
            "am_interested": self.am_interested,
        }

    def __repr__(self) -> str:
        return (
            f"ConnectionHandler(local_peer_id={self.local_peer_id}, "
            f"remote_peer_id={self.remote_peer_id}, "
            f"address={self.address}, "
            f"is_connected={self.is_connected}, "
            f"handshake_completed={self.handshake_completed})"
        )
