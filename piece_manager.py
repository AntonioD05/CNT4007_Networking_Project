from pathlib import Path
from typing import Dict, List, Optional, Set
import math


class PieceManager:
    def __init__(
        self,
        file_name: str,
        file_size: int,
        piece_size: int,
        starts_with_file: bool,
        owner_peer_id: int,
        data_dir: str,
    ):
        self.file_name = file_name
        self.file_size = file_size
        self.piece_size = piece_size
        self.owner_peer_id = owner_peer_id
        self.data_dir = Path(data_dir)

        self.num_pieces = math.ceil(file_size / piece_size)

        if starts_with_file:
            self.bitfield: List[bool] = [True] * self.num_pieces
        else:
            self.bitfield: List[bool] = [False] * self.num_pieces

        self.requested_pieces: Set[int] = set()
        self.pieces_data: Dict[int, bytes] = {}

        self.data_dir.mkdir(parents=True, exist_ok=True)

        if starts_with_file:
            self._load_file_into_pieces()

    def _source_file_path(self) -> Path:
        return self.data_dir / self.file_name

    def _output_file_path(self) -> Path:
        return self.data_dir / self.file_name

    def _load_file_into_pieces(self) -> None:
        file_path = self._source_file_path()

        if not file_path.exists():
            raise FileNotFoundError(
                f"Seeder file not found for peer {self.owner_peer_id}: {file_path}"
            )

        file_bytes = file_path.read_bytes()

        if len(file_bytes) != self.file_size:
            raise ValueError(
                f"File size mismatch for peer {self.owner_peer_id}. "
                f"Expected {self.file_size}, found {len(file_bytes)}"
            )

        for piece_index in range(self.num_pieces):
            start = piece_index * self.piece_size
            end = min(start + self.piece_size, len(file_bytes))
            self.pieces_data[piece_index] = file_bytes[start:end]

    def reconstruct_file(self) -> Path:
        if not self.has_complete_file():
            raise ValueError("Cannot reconstruct file before all pieces are owned")

        output_path = self._output_file_path()

        with open(output_path, "wb") as f:
            for piece_index in range(self.num_pieces):
                if piece_index not in self.pieces_data:
                    raise ValueError(f"Missing data for piece {piece_index}")
                f.write(self.pieces_data[piece_index])

        return output_path

    def has_piece(self, piece_index: int) -> bool:
        self._validate_piece_index(piece_index)
        return self.bitfield[piece_index]

    def needs_piece(self, piece_index: int) -> bool:
        self._validate_piece_index(piece_index)
        return not self.bitfield[piece_index]

    def mark_piece_as_owned(self, piece_index: int, piece_data: Optional[bytes] = None) -> None:
        self._validate_piece_index(piece_index)
        self.bitfield[piece_index] = True
        self.requested_pieces.discard(piece_index)

        if piece_data is not None:
            self.pieces_data[piece_index] = piece_data

    def get_piece_data(self, piece_index: int) -> bytes:
        self._validate_piece_index(piece_index)
        if piece_index not in self.pieces_data:
            raise ValueError(f"No data stored for piece {piece_index}")
        return self.pieces_data[piece_index]

    def piece_count(self) -> int:
        return sum(self.bitfield)

    def has_complete_file(self) -> bool:
        return all(self.bitfield)

    def add_requested_piece(self, piece_index: int) -> None:
        self._validate_piece_index(piece_index)
        self.requested_pieces.add(piece_index)

    def remove_requested_piece(self, piece_index: int) -> None:
        self._validate_piece_index(piece_index)
        self.requested_pieces.discard(piece_index)

    def is_piece_requested(self, piece_index: int) -> bool:
        self._validate_piece_index(piece_index)
        return piece_index in self.requested_pieces

    def missing_pieces(self) -> List[int]:
        return [i for i, has_piece in enumerate(self.bitfield) if not has_piece]

    def owned_pieces(self) -> List[int]:
        return [i for i, has_piece in enumerate(self.bitfield) if has_piece]

    def choose_missing_piece_from_remote_bitfield(self, remote_bitfield: List[bool]) -> Optional[int]:
        for piece_index in range(min(len(remote_bitfield), self.num_pieces)):
            if (
                remote_bitfield[piece_index]
                and not self.has_piece(piece_index)
                and not self.is_piece_requested(piece_index)
            ):
                return piece_index
        return None

    def bitfield_as_string(self) -> str:
        return "".join("1" if has_piece else "0" for has_piece in self.bitfield)

    def _validate_piece_index(self, piece_index: int) -> None:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")
