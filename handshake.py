HEADER = b"P2PFILESHARINGPROJ"
ZERO_BITS = b"\x00" * 10
HANDSHAKE_LENGTH = 32


def build_handshake(peer_id: int) -> bytes:
    # Build a 32-byte handshake message: 18-byte header + 10 zero bytes + 4-byte peer ID
    if not isinstance(peer_id, int):
        raise TypeError("peer_id must be an integer")

    peer_id_bytes = peer_id.to_bytes(4, byteorder="big")
    handshake = HEADER + ZERO_BITS + peer_id_bytes

    if len(handshake) != HANDSHAKE_LENGTH:
        raise ValueError("Handshake must be exactly 32 bytes")

    return handshake


def parse_handshake(handshake_bytes: bytes) -> dict:
    # Parse a 32-byte handshake and return its parts.
    if len(handshake_bytes) != HANDSHAKE_LENGTH:
        raise ValueError("Handshake must be exactly 32 bytes")

    header = handshake_bytes[:18]
    zero_bits = handshake_bytes[18:28]
    peer_id_bytes = handshake_bytes[28:32]
    peer_id = int.from_bytes(peer_id_bytes, byteorder="big")

    return {
        "header": header,
        "zero_bits": zero_bits,
        "peer_id": peer_id,
    }


def is_valid_handshake(handshake_bytes: bytes) -> bool:
    # Check whether a handshake has the correct header and zero bits.
    
    if len(handshake_bytes) != HANDSHAKE_LENGTH:
        return False

    parsed = parse_handshake(handshake_bytes)

    return parsed["header"] == HEADER and parsed["zero_bits"] == ZERO_BITS