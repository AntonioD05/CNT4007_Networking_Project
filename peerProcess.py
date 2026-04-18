import sys
import time
import threading

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

CONFIG_DIR = "project_config_file_local"


def accept_incoming_connections(peer_server: PeerServer, peer_state: PeerState, logger: PeerLogger, expected_count: int):
    accepted = 0

    while accepted < expected_count:
        try:
            client_socket, client_address = peer_server.accept_connection()

            connection = ConnectionHandler(
                local_peer_id=peer_state.peer_id,
                remote_peer_id=None,
                sock=client_socket,
                address=client_address,
            )

            temp_remote_id = -1 * (accepted + 1)
            peer_state.add_connection(temp_remote_id, connection)

            print(f"[ACCEPT] Peer {peer_state.peer_id} accepted connection from {client_address}")

            remote_peer_id = connection.receive_handshake()
            print(f"[HANDSHAKE RECEIVE] Peer {peer_state.peer_id} received handshake from peer {remote_peer_id}")

            connection.send_handshake()
            print(f"[HANDSHAKE SEND] Peer {peer_state.peer_id} sent handshake to peer {remote_peer_id}")

            peer_state.replace_connection_key(temp_remote_id, remote_peer_id)
            logger.log_tcp_connection_from(remote_peer_id)

            connection.send_bitfield(peer_state.piece_manager.bitfield)
            print(f"[BITFIELD SEND] Peer {peer_state.peer_id} sent bitfield to peer {remote_peer_id}")

            remote_bitfield = connection.receive_bitfield(peer_state.piece_manager.num_pieces)
            print(f"[BITFIELD RECEIVE] Peer {peer_state.peer_id} received bitfield from peer {remote_peer_id}")

            if peer_state.is_interested_in_bitfield(remote_bitfield):
                connection.send_interested()
                print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent INTERESTED to peer {remote_peer_id}")
            else:
                connection.send_not_interested()
                print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {remote_peer_id}")

            interest_result = connection.receive_interest_message()
            print(f"[INTEREST RECEIVE] Peer {peer_state.peer_id} received {interest_result.upper()} from peer {remote_peer_id}")

            if interest_result == "interested":
                connection.send_unchoke()
                print(f"[UNCHOKE SEND] Peer {peer_state.peer_id} sent UNCHOKE to peer {remote_peer_id}")

                requested_piece_index = connection.receive_request_piece_index()
                print(f"[REQUEST RECEIVE] Peer {peer_state.peer_id} received request for piece {requested_piece_index} from peer {remote_peer_id}")

                piece_data = peer_state.piece_manager.get_piece_data(requested_piece_index)
                connection.send_piece_message(requested_piece_index, piece_data)
                print(f"[PIECE SEND] Peer {peer_state.peer_id} sent piece {requested_piece_index} to peer {remote_peer_id}")

            accepted += 1

        except Exception as e:
            if peer_server.is_listening:
                print(f"[ACCEPT ERROR] {e}")
            break


def main():
    if len(sys.argv) != 2:
        print("Usage: python peerProcess.py <peer_id>")
        sys.exit(1)

    try:
        peer_id = int(sys.argv[1])
    except ValueError:
        print("Peer ID must be an integer.")
        sys.exit(1)

    try:
        common_config = load_common_config(CONFIG_DIR)
        peers = load_peer_info(CONFIG_DIR)
        current_peer = get_peer_by_id(peer_id, peers)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

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

    print("\n=== Phase D: First Piece Transfer ===")
    earlier_peers = peer_state.get_earlier_peers()
    later_peers = peer_state.get_later_peers()

    print(f"Earlier peers: {[peer.peer_id for peer in earlier_peers]}")
    print(f"Later peers: {[peer.peer_id for peer in later_peers]}")

    peer_server = PeerServer(
        host=peer_state.host,
        port=peer_state.port,
        peer_id=peer_state.peer_id,
    )

    try:
        peer_server.bind_and_listen()
        print(f"[SERVER] Peer {peer_state.peer_id} listening on port {peer_state.port}")
        logger.log_custom(
            f"Peer {peer_state.peer_id} started server listening on port {peer_state.port}."
        )
    except Exception as e:
        print(f"[SERVER ERROR] Could not start server: {e}")
        logger.log_custom(
            f"Peer {peer_state.peer_id} failed to start server: {e}"
        )
        sys.exit(1)

    accept_thread = threading.Thread(
        target=accept_incoming_connections,
        args=(peer_server, peer_state, logger, len(later_peers)),
        daemon=True,
    )
    accept_thread.start()

    time.sleep(1)

    for remote_peer in earlier_peers:
        try:
            connection = ConnectionHandler(
                local_peer_id=peer_state.peer_id,
                remote_peer_id=remote_peer.peer_id,
            )
            connection.connect(remote_peer.host, remote_peer.port)

            print(
                f"[CONNECT] Peer {peer_state.peer_id} connected to peer {remote_peer.peer_id} "
                f"at {remote_peer.host}:{remote_peer.port}"
            )

            connection.send_handshake()
            print(f"[HANDSHAKE SEND] Peer {peer_state.peer_id} sent handshake to peer {remote_peer.peer_id}")

            returned_peer_id = connection.receive_handshake()
            print(f"[HANDSHAKE RECEIVE] Peer {peer_state.peer_id} received handshake from peer {returned_peer_id}")

            if returned_peer_id != remote_peer.peer_id:
                raise ValueError(
                    f"Expected handshake from peer {remote_peer.peer_id}, got {returned_peer_id}"
                )

            peer_state.add_connection(remote_peer.peer_id, connection)
            logger.log_tcp_connection_to(remote_peer.peer_id)

            connection.send_bitfield(peer_state.piece_manager.bitfield)
            print(f"[BITFIELD SEND] Peer {peer_state.peer_id} sent bitfield to peer {remote_peer.peer_id}")

            remote_bitfield = connection.receive_bitfield(peer_state.piece_manager.num_pieces)
            print(f"[BITFIELD RECEIVE] Peer {peer_state.peer_id} received bitfield from peer {remote_peer.peer_id}")

            if peer_state.is_interested_in_bitfield(remote_bitfield):
                connection.send_interested()
                print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent INTERESTED to peer {remote_peer.peer_id}")
            else:
                connection.send_not_interested()
                print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {remote_peer.peer_id}")

            interest_result = connection.receive_interest_message()
            print(f"[INTEREST RECEIVE] Peer {peer_state.peer_id} received {interest_result.upper()} from peer {remote_peer.peer_id}")

            if interest_result == "interested":
                print(f"[WAIT] Peer {peer_state.peer_id} is waiting for future request from peer {remote_peer.peer_id}")
            else:
                connection.receive_unchoke()
                print(f"[UNCHOKE RECEIVE] Peer {peer_state.peer_id} received UNCHOKE from peer {remote_peer.peer_id}")

                piece_index = peer_state.piece_manager.choose_missing_piece_from_remote_bitfield(remote_bitfield)
                if piece_index is None:
                    raise ValueError("No missing piece available to request")

                peer_state.piece_manager.add_requested_piece(piece_index)
                connection.send_request(piece_index)
                print(f"[REQUEST SEND] Peer {peer_state.peer_id} requested piece {piece_index} from peer {remote_peer.peer_id}")

                received_piece = connection.receive_piece_message()
                received_piece_index = received_piece["piece_index"]
                received_piece_data = received_piece["piece_data"]

                peer_state.piece_manager.mark_piece_as_owned(received_piece_index, received_piece_data)

                print(f"[PIECE RECEIVE] Peer {peer_state.peer_id} received piece {received_piece_index} from peer {remote_peer.peer_id}")
                print(f"[PIECE STORE] Peer {peer_state.peer_id} now has {peer_state.piece_manager.piece_count()} pieces")

        except Exception as e:
            print(
                f"[CONNECT ERROR] Peer {peer_state.peer_id} could not complete setup with "
                f"peer {remote_peer.peer_id}: {e}"
            )
            logger.log_custom(
                f"Peer {peer_state.peer_id} failed setup with peer {remote_peer.peer_id}: {e}"
            )

    print("\n[RUNNING] Peer is now waiting. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(2)
            print("\n=== Active Connections Summary ===")
            with peer_state.connections_lock:
                for remote_id, connection in peer_state.connections.items():
                    print(f"{remote_id}: {connection.summary()}")

            print(f"Total active connections stored: {peer_state.connection_count()}")
            print(f"Current owned pieces: {peer_state.piece_manager.piece_count()}")

    except KeyboardInterrupt:
        print(f"\n[SHUTDOWN] Stopping peer {peer_state.peer_id}...")

        peer_server.close()

        with peer_state.connections_lock:
            for connection in peer_state.connections.values():
                connection.close()

        print(f"[SHUTDOWN] Peer {peer_state.peer_id} closed server and connections.")


if __name__ == "__main__":
    main()

