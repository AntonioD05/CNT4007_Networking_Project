from datetime import datetime
from pathlib import Path
from typing import List


class PeerLogger:
    def __init__(self, peer_id: int, log_dir: str = "."):
        self.peer_id = peer_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"log_peer_{peer_id}.log"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write_log(self, message: str) -> None:
        line = f"[{self._timestamp()}] {message}\n"
        with open(self.log_file, "a") as f:
            f.write(line)

    def log_tcp_connection_to(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} makes a connection to Peer {peer_id}."
        )

    def log_tcp_connection_from(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} is connected from Peer {peer_id}."
        )

    def log_preferred_neighbors(self, neighbor_ids: List[int]) -> None:
        neighbors_str = ", ".join(str(peer_id) for peer_id in neighbor_ids)
        self._write_log(
            f"Peer {self.peer_id} has the preferred neighbors {neighbors_str}."
        )

    def log_optimistic_unchoke(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} has the optimistically unchoked neighbor {peer_id}."
        )

    def log_unchoked_by(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} is unchoked by {peer_id}."
        )

    def log_choked_by(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} is choked by {peer_id}."
        )

    def log_receive_have(self, peer_id: int, piece_index: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} received the 'have' message from {peer_id} for the piece {piece_index}."
        )

    def log_receive_interested(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} received the 'interested' message from {peer_id}."
        )

    def log_receive_not_interested(self, peer_id: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} received the 'not interested' message from {peer_id}."
        )

    def log_downloaded_piece(self, peer_id: int, piece_index: int, total_pieces_owned: int) -> None:
        self._write_log(
            f"Peer {self.peer_id} has downloaded the piece {piece_index} from {peer_id}. "
            f"Now the number of pieces it has is {total_pieces_owned}."
        )

    def log_complete_file(self) -> None:
        self._write_log(
            f"Peer {self.peer_id} has downloaded the complete file."
        )

    def log_custom(self, message: str) -> None:
        self._write_log(message)
