from typing import Dict, List, Optional, Set
import math


class PieceManager:
    def __init__(self, file_size: int, piece_size: int, starts_with_file: bool, owner_peer_id: int):
        self.file_size = file_size
        self.piece_size = piece_size
        self.owner_peer_id = owner_peer_id
        self.num_pieces = math.ceil(file_size / piece_size)

        if starts_with_file:
            self.bitfield: List[bool] = [True] * self.num_pieces
        else:
            self.bitfield: List[bool] = [False] * self.num_pieces

        self.requested_pieces: Set[int] = set()
        self.pieces_data: Dict[int, bytes] = {}

        if starts_with_file:
            for piece_index in range(self.num_pieces):
                self.pieces_data[piece_index] = self._generate_placeholder_piece(piece_index)

    def _generate_placeholder_piece(self, piece_index: int) -> bytes:
        return f"piece-{piece_index}-from-peer-{self.owner_peer_id}".encode()

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
        elif piece_index not in self.pieces_data:
            self.pieces_data[piece_index] = self._generate_placeholder_piece(piece_index)

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
            if remote_bitfield[piece_index] and not self.has_piece(piece_index) and not self.is_piece_requested(piece_index):
                return piece_index
        return None

    def bitfield_as_string(self) -> str:
        return "".join("1" if has_piece else "0" for has_piece in self.bitfield)

    def _validate_piece_index(self, piece_index: int) -> None:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")
