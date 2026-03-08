import sys

from config_loader import load_common_config, load_peer_info, get_peer_by_id
from peer_state import PeerState
from logger import PeerLogger
from handshake import build_handshake, parse_handshake, is_valid_handshake
from message import (
    build_choke,
    build_unchoke,
    build_interested,
    build_not_interested,
    build_have,
    build_bitfield,
    build_request,
    build_piece,
    parse_message,
    parse_have_payload,
    parse_request_payload,
    parse_piece_payload,
)
from utils import (
    int_to_bytes,
    bytes_to_int,
    bitfield_list_to_bytes,
    bitfield_bytes_to_list,
)
from server import PeerServer
from connection import ConnectionHandler


def main():
    if len(sys.argv) != 2:
        print("Usage: python peerProcess.py <peer_id>")
        sys.exit(1)

    try:
        peer_id = int(sys.argv[1])
    except ValueError:
        print("Peer ID must be an integer.")
        sys.exit(1)

    common_config = load_common_config()
    peers = load_peer_info()
    current_peer = get_peer_by_id(peer_id, peers)

    peer_state = PeerState(
        current_peer=current_peer,
        common_config=common_config,
        all_peers=peers,
    )

    logger = PeerLogger(peer_id=peer_state.peer_id)

    print("=== Current Peer ===")
    print(peer_state.current_peer)

    print("\n=== Common Config ===")
    print(peer_state.common_config)

    print("\n=== Peer State Summary ===")
    print(f"Peer ID: {peer_state.peer_id}")
    print(f"Host: {peer_state.host}")
    print(f"Port: {peer_state.port}")
    print(f"Starts with file: {peer_state.has_file}")
    print(f"Total number of pieces: {peer_state.piece_manager.num_pieces}")
    print(f"Pieces currently owned: {peer_state.piece_manager.piece_count()}")
    print(f"Has complete file: {peer_state.piece_manager.has_complete_file()}")

    print("\n=== Bitfield Preview ===")
    preview_length = min(64, peer_state.piece_manager.num_pieces)
    print(peer_state.piece_manager.bitfield_as_string()[:preview_length])

    print("\n=== Piece Manager Checks ===")
    print(f"Owns piece 0: {peer_state.piece_manager.has_piece(0)}")
    print(f"Needs piece 0: {peer_state.piece_manager.needs_piece(0)}")
    print(f"Requested pieces: {peer_state.piece_manager.requested_pieces}")

    print("\n=== Neighbors ===")
    for neighbor in peer_state.neighbors:
        print(neighbor)

    logger.log_custom(f"Peer {peer_state.peer_id} started successfully.")
    logger.log_custom(
        f"Peer {peer_state.peer_id} initialized with {peer_state.piece_manager.piece_count()} pieces."
    )

    if peer_state.neighbors:
        first_neighbor = peer_state.neighbors[0]
        logger.log_tcp_connection_to(first_neighbor.peer_id)
        logger.log_receive_interested(first_neighbor.peer_id)

    if peer_state.piece_manager.has_complete_file():
        logger.log_complete_file()

    print(f"\nLog file created: log_peer_{peer_state.peer_id}.log")

    handshake = build_handshake(peer_state.peer_id)
    parsed_handshake = parse_handshake(handshake)

    print("\n=== Handshake Test ===")
    print(f"Handshake length: {len(handshake)}")
    print(f"Handshake valid: {is_valid_handshake(handshake)}")
    print(f"Parsed peer ID: {parsed_handshake['peer_id']}")
    print(f"Parsed header: {parsed_handshake['header']}")
    print(f"Parsed zero bits: {parsed_handshake['zero_bits']}")

    choke_msg = build_choke()
    unchoke_msg = build_unchoke()
    interested_msg = build_interested()
    not_interested_msg = build_not_interested()
    have_msg = build_have(7)
    bitfield_msg = build_bitfield(b"\xaa\x0f")
    request_msg = build_request(12)
    piece_msg = build_piece(5, b"hello")

    parsed_choke = parse_message(choke_msg)
    parsed_unchoke = parse_message(unchoke_msg)
    parsed_interested = parse_message(interested_msg)
    parsed_not_interested = parse_message(not_interested_msg)
    parsed_have = parse_message(have_msg)
    parsed_bitfield = parse_message(bitfield_msg)
    parsed_request = parse_message(request_msg)
    parsed_piece = parse_message(piece_msg)

    print("\n=== Message Test ===")
    print(f"Choke parsed: {parsed_choke}")
    print(f"Unchoke parsed: {parsed_unchoke}")
    print(f"Interested parsed: {parsed_interested}")
    print(f"Not interested parsed: {parsed_not_interested}")

    print(f"\nHave parsed: {parsed_have}")
    print(f"Have piece index: {parse_have_payload(parsed_have['payload'])}")

    print(f"\nBitfield parsed: {parsed_bitfield}")

    print(f"\nRequest parsed: {parsed_request}")
    print(f"Request piece index: {parse_request_payload(parsed_request['payload'])}")

    piece_payload_info = parse_piece_payload(parsed_piece["payload"])
    print(f"\nPiece parsed: {parsed_piece}")
    print(f"Piece payload index: {piece_payload_info['piece_index']}")
    print(f"Piece payload data: {piece_payload_info['piece_data']}")

    print("\n=== Utils Test ===")
    four_bytes = int_to_bytes(1001, 4)
    print(f"1001 as 4 bytes: {four_bytes}")
    print(f"Back to int: {bytes_to_int(four_bytes)}")

    sample_bitfield = [True, False, True, False, False, False, False, True, True, True]
    packed_bitfield = bitfield_list_to_bytes(sample_bitfield)
    unpacked_bitfield = bitfield_bytes_to_list(packed_bitfield, len(sample_bitfield))

    print(f"Sample bitfield list: {sample_bitfield}")
    print(f"Packed bitfield bytes: {packed_bitfield}")
    print(f"Unpacked bitfield list: {unpacked_bitfield}")

    peer_server = PeerServer(
        host=peer_state.host,
        port=peer_state.port,
        peer_id=peer_state.peer_id,
    )

    example_connection = None
    if peer_state.neighbors:
        example_connection = ConnectionHandler(
            local_peer_id=peer_state.peer_id,
            remote_peer_id=peer_state.neighbors[0].peer_id,
        )

    print("\n=== Networking Skeleton Test ===")
    print(peer_server)
    if example_connection is not None:
        print(example_connection)
        print(example_connection.summary())


if __name__ == "__main__":
    main()