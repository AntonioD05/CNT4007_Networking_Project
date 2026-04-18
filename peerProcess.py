import sys
import time
import threading
from pathlib import Path

from config_loader import load_common_config, load_peer_info, get_peer_by_id
from peer_state import PeerState
from logger import PeerLogger
from server import PeerServer
from connection import ConnectionHandler
from message import parse_have_payload, MESSAGE_TYPES

CONFIG_DIR = "project_config_file_local"


def resolve_peer_data_dir(peer_id: int) -> str:
    candidates = [
        Path(CONFIG_DIR) / str(peer_id),
        Path(f"peer_{peer_id}"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    default_dir = Path(CONFIG_DIR) / str(peer_id)
    default_dir.mkdir(parents=True, exist_ok=True)
    return str(default_dir)


def ensure_remote_bitfield(connection: ConnectionHandler, num_pieces: int) -> None:
    if connection.remote_bitfield is None:
        connection.remote_bitfield = [False] * num_pieces


def uploader_loop(connection: ConnectionHandler, peer_state: PeerState, logger: PeerLogger) -> None:
    remote_peer_id = connection.remote_peer_id

    while True:
        parsed = connection.receive_message()

        if parsed["type"] == MESSAGE_TYPES["have"]:
            piece_index = parse_have_payload(parsed["payload"])
            ensure_remote_bitfield(connection, peer_state.piece_manager.num_pieces)
            connection.remote_bitfield[piece_index] = True
            print(f"[HAVE RECEIVE] Peer {peer_state.peer_id} received HAVE for piece {piece_index} from peer {remote_peer_id}")

        elif parsed["type"] == MESSAGE_TYPES["request"]:
            requested_piece_index = int.from_bytes(parsed["payload"], byteorder="big")
            print(f"[REQUEST RECEIVE] Peer {peer_state.peer_id} received request for piece {requested_piece_index} from peer {remote_peer_id}")

            piece_data = peer_state.piece_manager.get_piece_data(requested_piece_index)
            connection.send_piece_message(requested_piece_index, piece_data)
            print(f"[PIECE SEND] Peer {peer_state.peer_id} sent piece {requested_piece_index} to peer {remote_peer_id}")

        elif parsed["type"] == MESSAGE_TYPES["not_interested"]:
            connection.peer_is_interested = False
            print(f"[INTEREST RECEIVE] Peer {peer_state.peer_id} received NOT_INTERESTED from peer {remote_peer_id}")
            break

        else:
            raise ValueError(f"Uploader loop got unexpected message type {parsed['type_name']}")


def downloader_loop(connection: ConnectionHandler, peer_state: PeerState, logger: PeerLogger) -> None:
    remote_peer_id = connection.remote_peer_id

    connection.receive_unchoke()
    print(f"[UNCHOKE RECEIVE] Peer {peer_state.peer_id} received UNCHOKE from peer {remote_peer_id}")

    while True:
        piece_index = peer_state.piece_manager.choose_missing_piece_from_remote_bitfield(connection.remote_bitfield)

        if piece_index is None:
            connection.send_not_interested()
            print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {remote_peer_id}")
            break

        peer_state.piece_manager.add_requested_piece(piece_index)
        connection.send_request(piece_index)
        print(f"[REQUEST SEND] Peer {peer_state.peer_id} requested piece {piece_index} from peer {remote_peer_id}")

        received_piece = connection.receive_piece_message()
        received_piece_index = received_piece["piece_index"]
        received_piece_data = received_piece["piece_data"]

        peer_state.piece_manager.mark_piece_as_owned(received_piece_index, received_piece_data)
        logger.log_downloaded_piece(remote_peer_id, received_piece_index, peer_state.piece_manager.piece_count())

        print(f"[PIECE RECEIVE] Peer {peer_state.peer_id} received piece {received_piece_index} from peer {remote_peer_id}")
        print(f"[PIECE STORE] Peer {peer_state.peer_id} now has {peer_state.piece_manager.piece_count()} pieces")

        connection.send_have(received_piece_index)
        print(f"[HAVE SEND] Peer {peer_state.peer_id} sent HAVE for piece {received_piece_index} to peer {remote_peer_id}")

        if peer_state.piece_manager.has_complete_file():
            output_path = peer_state.piece_manager.reconstruct_file()
            logger.log_complete_file()
            print(f"[COMPLETE] Peer {peer_state.peer_id} now has the complete file.")
            print(f"[FILE WRITE] Peer {peer_state.peer_id} reconstructed file at: {output_path}")
            connection.send_not_interested()
            print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {remote_peer_id}")
            break


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
                uploader_loop(connection, peer_state, logger)

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

    data_dir = resolve_peer_data_dir(peer_id)

    peer_state = PeerState(
        current_peer=current_peer,
        common_config=common_config,
        all_peers=peers,
        data_dir=data_dir,
    )

    logger = PeerLogger(peer_id=peer_state.peer_id)

    print("=== Phase F: Real File Bytes + Reconstruction ===")
    print(f"Peer ID: {peer_state.peer_id}")
    print(f"Host: {peer_state.host}")
    print(f"Port: {peer_state.port}")
    print(f"Starts with file: {peer_state.has_file}")
    print(f"Data directory: {data_dir}")
    print(f"Initial pieces owned: {peer_state.piece_manager.piece_count()}")

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
    except Exception as e:
        print(f"[SERVER ERROR] Could not start server: {e}")
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

            print(f"[CONNECT] Peer {peer_state.peer_id} connected to peer {remote_peer.peer_id} at {remote_peer.host}:{remote_peer.port}")

            connection.send_handshake()
            print(f"[HANDSHAKE SEND] Peer {peer_state.peer_id} sent handshake to peer {remote_peer.peer_id}")

            returned_peer_id = connection.receive_handshake()
            print(f"[HANDSHAKE RECEIVE] Peer {peer_state.peer_id} received handshake from peer {returned_peer_id}")

            if returned_peer_id != remote_peer.peer_id:
                raise ValueError(f"Expected handshake from peer {remote_peer.peer_id}, got {returned_peer_id}")

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

            if connection.am_interested:
                downloader_loop(connection, peer_state, logger)

        except Exception as e:
            print(f"[CONNECT ERROR] Peer {peer_state.peer_id} could not complete setup with peer {remote_peer.peer_id}: {e}")

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

