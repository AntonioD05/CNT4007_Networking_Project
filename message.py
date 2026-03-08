MESSAGE_TYPES = {
    "choke": 0,
    "unchoke": 1,
    "interested": 2,
    "not_interested": 3,
    "have": 4,
    "bitfield": 5,
    "request": 6,
    "piece": 7,
}

MESSAGE_TYPE_NAMES = {value: key for key, value in MESSAGE_TYPES.items()}


def build_message(message_type: int, payload: bytes = b"") -> bytes:
    """
    Build a normal protocol message:
    4-byte length + 1-byte type + optional payload
    """
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")

    message_length = 1 + len(payload)
    length_bytes = message_length.to_bytes(4, byteorder="big")
    type_bytes = message_type.to_bytes(1, byteorder="big")

    return length_bytes + type_bytes + payload


def parse_message(message_bytes: bytes) -> dict:
    """
    Parse a normal protocol message into length, type, type_name, and payload.
    """
    if len(message_bytes) < 5:
        raise ValueError("Message must be at least 5 bytes")

    length = int.from_bytes(message_bytes[:4], byteorder="big")
    message_type = message_bytes[4]
    payload = message_bytes[5:]

    if length != 1 + len(payload):
        raise ValueError("Message length field does not match actual payload size")

    return {
        "length": length,
        "type": message_type,
        "type_name": MESSAGE_TYPE_NAMES.get(message_type, "unknown"),
        "payload": payload,
    }


def build_choke() -> bytes:
    return build_message(MESSAGE_TYPES["choke"])


def build_unchoke() -> bytes:
    return build_message(MESSAGE_TYPES["unchoke"])


def build_interested() -> bytes:
    return build_message(MESSAGE_TYPES["interested"])


def build_not_interested() -> bytes:
    return build_message(MESSAGE_TYPES["not_interested"])


def build_have(piece_index: int) -> bytes:
    payload = piece_index.to_bytes(4, byteorder="big")
    return build_message(MESSAGE_TYPES["have"], payload)


def build_bitfield(bitfield_bytes: bytes) -> bytes:
    return build_message(MESSAGE_TYPES["bitfield"], bitfield_bytes)


def build_request(piece_index: int) -> bytes:
    payload = piece_index.to_bytes(4, byteorder="big")
    return build_message(MESSAGE_TYPES["request"], payload)


def build_piece(piece_index: int, piece_data: bytes) -> bytes:
    payload = piece_index.to_bytes(4, byteorder="big") + piece_data
    return build_message(MESSAGE_TYPES["piece"], payload)


def parse_have_payload(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Have payload must be exactly 4 bytes")
    return int.from_bytes(payload, byteorder="big")


def parse_request_payload(payload: bytes) -> int:
    if len(payload) != 4:
        raise ValueError("Request payload must be exactly 4 bytes")
    return int.from_bytes(payload, byteorder="big")


def parse_piece_payload(payload: bytes) -> dict:
    if len(payload) < 4:
        raise ValueError("Piece payload must be at least 4 bytes")

    piece_index = int.from_bytes(payload[:4], byteorder="big")
    piece_data = payload[4:]

    return {
        "piece_index": piece_index,
        "piece_data": piece_data,
    }

