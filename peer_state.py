from dataclasses import dataclass, field
from typing import Dict, List
import threading

from config_loader import CommonConfig, PeerInfo
from piece_manager import PieceManager
from connection import ConnectionHandler


@dataclass
class PeerState:
    current_peer: PeerInfo
    common_config: CommonConfig
    all_peers: List[PeerInfo]

    piece_manager: PieceManager = field(init=False)
    neighbors: List[PeerInfo] = field(init=False)
    connections: Dict[int, ConnectionHandler] = field(init=False)
    connections_lock: threading.Lock = field(init=False)

    def __post_init__(self):
        self.piece_manager = PieceManager(
            file_size=self.common_config.file_size,
            piece_size=self.common_config.piece_size,
            starts_with_file=self.current_peer.has_file,
        )

        self.neighbors = [
            peer for peer in self.all_peers
            if peer.peer_id != self.current_peer.peer_id
        ]

        self.connections = {}
        self.connections_lock = threading.Lock()

    @property
    def peer_id(self) -> int:
        return self.current_peer.peer_id

    @property
    def host(self) -> str:
        return self.current_peer.host

    @property
    def port(self) -> int:
        return self.current_peer.port

    @property
    def has_file(self) -> bool:
        return self.current_peer.has_file

    def get_earlier_peers(self) -> List[PeerInfo]:
        earlier = []
        for peer in self.all_peers:
            if peer.peer_id == self.peer_id:
                break
            earlier.append(peer)
        return earlier

    def get_later_peers(self) -> List[PeerInfo]:
        later = []
        found_self = False
        for peer in self.all_peers:
            if found_self:
                later.append(peer)
            if peer.peer_id == self.peer_id:
                found_self = True
        return later

    def add_connection(self, remote_peer_id: int, connection: ConnectionHandler) -> None:
        with self.connections_lock:
            self.connections[remote_peer_id] = connection

    def replace_connection_key(self, old_remote_peer_id: int, new_remote_peer_id: int) -> None:
        with self.connections_lock:
            connection = self.connections.pop(old_remote_peer_id, None)
            if connection is not None:
                self.connections[new_remote_peer_id] = connection

    def get_connection(self, remote_peer_id: int):
        with self.connections_lock:
            return self.connections.get(remote_peer_id)

    def connection_count(self) -> int:
        with self.connections_lock:
            return len(self.connections)

    def is_interested_in_bitfield(self, remote_bitfield: List[bool]) -> bool:
        """
        Return True if the remote peer has at least one piece I do not have.
        """
        for i in range(min(len(remote_bitfield), self.piece_manager.num_pieces)):
            if remote_bitfield[i] and not self.piece_manager.has_piece(i):
                return True
        return False
    