from typing import List

def int_to_bytes(value: int, length: int) -> bytes:
    # Convert an integer to a big-endian byte sequence of the given length.
    if value < 0:
        raise ValueError("value must be non-negative")
    return value.to_bytes(length, byteorder="big")


def bytes_to_int(data: bytes) -> int:
    # Convert a big-endian byte sequence to an integer.
    return int.from_bytes(data, byteorder="big")


def bitfield_list_to_bytes(bitfield: List[bool]) -> bytes:
    # Convert a list of booleans into packed bitfield bytes.
    if not bitfield:
        return b""

    bits = "".join("1" if bit else "0" for bit in bitfield)

    padding = (8 - (len(bits) % 8)) % 8
    bits += "0" * padding

    byte_array = bytearray()
    for i in range(0, len(bits), 8):
        byte_chunk = bits[i:i + 8]
        byte_array.append(int(byte_chunk, 2))

    return bytes(byte_array)


def bitfield_bytes_to_list(bitfield_bytes: bytes, num_pieces: int) -> List[bool]:
    # Convert packed bitfield bytes back into a list of booleans. Only keep the first num_pieces bits.
    bits = ""
    for byte in bitfield_bytes:
        bits += format(byte, "08b")

    bits = bits[:num_pieces]
    return [bit == "1" for bit in bits]


def recv_exact(sock, num_bytes: int) -> bytes:
    # Read exactly num_bytes from a socket. Raises ConnectionError if the socket closes early.
    data = b""
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError("Socket connection closed before receiving enough data")
        data += chunk
    return data