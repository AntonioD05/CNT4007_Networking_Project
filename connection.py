import socket
from typing import Optional, Tuple, List

from handshake import build_handshake, parse_handshake, is_valid_handshake
from utils import recv_exact, bitfield_bytes_to_list, bitfield_list_to_bytes
from message import (
    build_bitfield,
    build_interested,
    build_not_interested,
    build_unchoke,
    build_choke,
    build_request,
    build_piece,
    build_have,
    parse_message,
    MESSAGE_TYPES,
)


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

        self.am_choked = True          # remote peer is choking me
        self.peer_is_choked = True     # I am choking remote peer
        self.peer_is_interested = False
        self.am_interested = False

        self.remote_bitfield: Optional[List[bool]] = None

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

    def send_handshake(self) -> None:
        self.send_bytes(build_handshake(self.local_peer_id))

    def receive_handshake(self) -> int:
        handshake_bytes = recv_exact(self.sock, 32)

        if not is_valid_handshake(handshake_bytes):
            raise ValueError("Received invalid handshake")

        parsed = parse_handshake(handshake_bytes)
        remote_peer_id = parsed["peer_id"]
        self.remote_peer_id = remote_peer_id
        self.handshake_completed = True
        return remote_peer_id

    def send_bitfield(self, local_bitfield: List[bool]) -> None:
        payload = bitfield_list_to_bytes(local_bitfield)
        self.send_bytes(build_bitfield(payload))

    def receive_message(self) -> dict:
        length_bytes = recv_exact(self.sock, 4)
        message_length = int.from_bytes(length_bytes, byteorder="big")
        rest = recv_exact(self.sock, message_length)
        full_message = length_bytes + rest
        return parse_message(full_message)

    def receive_bitfield(self, num_pieces: int) -> List[bool]:
        parsed = self.receive_message()

        if parsed["type"] != MESSAGE_TYPES["bitfield"]:
            raise ValueError(f"Expected bitfield message, got type {parsed['type_name']}")

        remote_bitfield = bitfield_bytes_to_list(parsed["payload"], num_pieces)
        self.remote_bitfield = remote_bitfield
        return remote_bitfield

    def send_interested(self) -> None:
        self.send_bytes(build_interested())
        self.am_interested = True

    def send_not_interested(self) -> None:
        self.send_bytes(build_not_interested())
        self.am_interested = False

    def send_unchoke(self) -> None:
        self.send_bytes(build_unchoke())
        self.peer_is_choked = False

    def send_choke(self) -> None:
        self.send_bytes(build_choke())
        self.peer_is_choked = True

    def send_request(self, piece_index: int) -> None:
        self.send_bytes(build_request(piece_index))

    def send_piece_message(self, piece_index: int, piece_data: bytes) -> None:
        self.send_bytes(build_piece(piece_index, piece_data))

    def send_have(self, piece_index: int) -> None:
        self.send_bytes(build_have(piece_index))

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
            "remote_bitfield_known": self.remote_bitfield is not None,
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