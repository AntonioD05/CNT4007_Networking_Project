from dataclasses import dataclass, field
from typing import List, Set
import math

from config_loader import CommonConfig, PeerInfo


@dataclass
class PeerState:
    current_peer: PeerInfo
    common_config: CommonConfig
    all_peers: List[PeerInfo]

    num_pieces: int = field(init=False)
    bitfield: List[bool] = field(init=False)
    neighbors: List[PeerInfo] = field(init=False)
    requested_pieces: Set[int] = field(default_factory=set)

    def __post_init__(self):
        self.num_pieces = math.ceil(
            self.common_config.file_size / self.common_config.piece_size
        )

        if self.current_peer.has_file:
            self.bitfield = [True] * self.num_pieces
        else:
            self.bitfield = [False] * self.num_pieces

        self.neighbors = [
            peer for peer in self.all_peers
            if peer.peer_id != self.current_peer.peer_id
        ]

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

    def has_complete_file(self) -> bool:
        return all(self.bitfield)

    def piece_count(self) -> int:
        return sum(self.bitfield)

    def mark_piece_as_owned(self, piece_index: int) -> None:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")
        self.bitfield[piece_index] = True
        self.requested_pieces.discard(piece_index)

    def needs_piece(self, piece_index: int) -> bool:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")
        return not self.bitfield[piece_index]

    def add_requested_piece(self, piece_index: int) -> None:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")
        self.requested_pieces.add(piece_index)

    def remove_requested_piece(self, piece_index: int) -> None:
        self.requested_pieces.discard(piece_index)

    def bitfield_as_string(self) -> str:
        return "".join("1" if has_piece else "0" for has_piece in self.bitfield)
    