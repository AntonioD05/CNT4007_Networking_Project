from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CommonConfig:
    number_of_preferred_neighbors: int
    unchoking_interval: int
    optimistic_unchoking_interval: int
    file_name: str
    file_size: int
    piece_size: int


@dataclass
class PeerInfo:
    peer_id: int
    host: str
    port: int
    has_file: bool


def load_common_config(config_dir: str = "project_config_file_small") -> CommonConfig:
    # Reads Common.cfg and returns a CommonConfig object.
    path = Path(config_dir) / "Common.cfg"

    values = {}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 2:
                raise ValueError(f"Invalid line in Common.cfg: {line}")

            key, value = parts
            values[key] = value

    required_keys = [
        "NumberOfPreferredNeighbors",
        "UnchokingInterval",
        "OptimisticUnchokingInterval",
        "FileName",
        "FileSize",
        "PieceSize",
    ]

    for key in required_keys:
        if key not in values:
            raise ValueError(f"Missing key in Common.cfg: {key}")

    return CommonConfig(
        number_of_preferred_neighbors=int(values["NumberOfPreferredNeighbors"]),
        unchoking_interval=int(values["UnchokingInterval"]),
        optimistic_unchoking_interval=int(values["OptimisticUnchokingInterval"]),
        file_name=values["FileName"],
        file_size=int(values["FileSize"]),
        piece_size=int(values["PieceSize"]),
    )


def load_peer_info(config_dir: str = "project_config_file_small") -> List[PeerInfo]:
    # Reads PeerInfo.cfg and returns a list of PeerInfo objects.
    path = Path(config_dir) / "PeerInfo.cfg"
    peers = []

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 4:
                raise ValueError(f"Invalid line in PeerInfo.cfg: {line}")

            peer_id, host, port, has_file = parts

            peers.append(
                PeerInfo(
                    peer_id=int(peer_id),
                    host=host,
                    port=int(port),
                    has_file=(has_file == "1"),
                )
            )

    return peers


def get_peer_by_id(peer_id: int, peers: List[PeerInfo]) -> PeerInfo:
    # Finds and returns the PeerInfo object for the given peer_id.
    for peer in peers:
        if peer.peer_id == peer_id:
            return peer

    raise ValueError(f"Peer ID {peer_id} not found in PeerInfo.cfg")