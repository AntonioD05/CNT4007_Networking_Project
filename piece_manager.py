from typing import List, Set
import math


class PieceManager:
    def __init__(self, file_size: int, piece_size: int, starts_with_file: bool):
        self.file_size = file_size
        self.piece_size = piece_size
        self.num_pieces = math.ceil(file_size / piece_size)

        if starts_with_file:
            self.bitfield: List[bool] = [True] * self.num_pieces
        else:
            self.bitfield: List[bool] = [False] * self.num_pieces

        self.requested_pieces: Set[int] = set()

    def has_piece(self, piece_index: int) -> bool:
        self._validate_piece_index(piece_index)
        return self.bitfield[piece_index]

    def needs_piece(self, piece_index: int) -> bool:
        self._validate_piece_index(piece_index)
        return not self.bitfield[piece_index]

    def mark_piece_as_owned(self, piece_index: int) -> None:
        self._validate_piece_index(piece_index)
        self.bitfield[piece_index] = True
        self.requested_pieces.discard(piece_index)

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

    def bitfield_as_string(self) -> str:
        return "".join("1" if has_piece else "0" for has_piece in self.bitfield)

    def _validate_piece_index(self, piece_index: int) -> None:
        if piece_index < 0 or piece_index >= self.num_pieces:
            raise IndexError(f"Piece index {piece_index} out of range")