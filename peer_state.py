from dataclasses import dataclass, field
from typing import List

from config_loader import CommonConfig, PeerInfo
from piece_manager import PieceManager


@dataclass
class PeerState:
    current_peer: PeerInfo
    common_config: CommonConfig
    all_peers: List[PeerInfo]

    piece_manager: PieceManager = field(init=False)
    neighbors: List[PeerInfo] = field(init=False)

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