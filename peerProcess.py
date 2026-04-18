import random
import sys
import time
import threading
from pathlib import Path

from config_loader import load_common_config, load_peer_info, get_peer_by_id
from peer_state import PeerState
from logger import PeerLogger
from server import PeerServer
from connection import ConnectionHandler
from message import parse_have_payload, parse_request_payload, parse_piece_payload, MESSAGE_TYPES

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


def send_have_to_all(peer_state: PeerState, piece_index: int) -> None:
    connections = peer_state.all_connections()
    for remote_peer_id, connection in connections.items():
        if connection.is_connected:
            connection.send_have(piece_index)
            print(f"[HAVE SEND] Peer {peer_state.peer_id} sent HAVE for piece {piece_index} to peer {remote_peer_id}")


def request_next_piece(connection: ConnectionHandler, peer_state: PeerState) -> None:
    if connection.am_choked:
        return

    if connection.remote_bitfield is None:
        return

    piece_index = peer_state.piece_manager.choose_missing_piece_from_remote_bitfield(connection.remote_bitfield)

    if piece_index is None:
        if connection.am_interested:
            connection.send_not_interested()
            print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {connection.remote_peer_id}")
        return

    peer_state.piece_manager.add_requested_piece(piece_index)
    connection.send_request(piece_index)
    print(f"[REQUEST SEND] Peer {peer_state.peer_id} requested piece {piece_index} from peer {connection.remote_peer_id}")


def receiver_loop(connection: ConnectionHandler, peer_state: PeerState, logger: PeerLogger) -> None:
    remote_peer_id = connection.remote_peer_id

    while True:
        try:
            parsed = connection.receive_message()
            msg_type = parsed["type"]

            if msg_type == MESSAGE_TYPES["interested"]:
                connection.peer_is_interested = True
                print(f"[INTEREST RECEIVE] Peer {peer_state.peer_id} received INTERESTED from peer {remote_peer_id}")

            elif msg_type == MESSAGE_TYPES["not_interested"]:
                connection.peer_is_interested = False
                print(f"[INTEREST RECEIVE] Peer {peer_state.peer_id} received NOT_INTERESTED from peer {remote_peer_id}")

            elif msg_type == MESSAGE_TYPES["choke"]:
                connection.am_choked = True
                print(f"[CHOKE RECEIVE] Peer {peer_state.peer_id} received CHOKE from peer {remote_peer_id}")

            elif msg_type == MESSAGE_TYPES["unchoke"]:
                connection.am_choked = False
                print(f"[UNCHOKE RECEIVE] Peer {peer_state.peer_id} received UNCHOKE from peer {remote_peer_id}")
                request_next_piece(connection, peer_state)

            elif msg_type == MESSAGE_TYPES["request"]:
                requested_piece_index = parse_request_payload(parsed["payload"])
                print(f"[REQUEST RECEIVE] Peer {peer_state.peer_id} received request for piece {requested_piece_index} from peer {remote_peer_id}")

                if not connection.peer_is_choked:
                    piece_data = peer_state.piece_manager.get_piece_data(requested_piece_index)
                    connection.send_piece_message(requested_piece_index, piece_data)
                    print(f"[PIECE SEND] Peer {peer_state.peer_id} sent piece {requested_piece_index} to peer {remote_peer_id}")

            elif msg_type == MESSAGE_TYPES["piece"]:
                piece_info = parse_piece_payload(parsed["payload"])
                piece_index = piece_info["piece_index"]
                piece_data = piece_info["piece_data"]

                peer_state.piece_manager.mark_piece_as_owned(piece_index, piece_data)
                peer_state.increment_download_count(remote_peer_id)
                logger.log_downloaded_piece(remote_peer_id, piece_index, peer_state.piece_manager.piece_count())

                print(f"[PIECE RECEIVE] Peer {peer_state.peer_id} received piece {piece_index} from peer {remote_peer_id}")
                print(f"[PIECE STORE] Peer {peer_state.peer_id} now has {peer_state.piece_manager.piece_count()} pieces")

                send_have_to_all(peer_state, piece_index)

                if peer_state.piece_manager.has_complete_file():
                    output_path = peer_state.piece_manager.reconstruct_file()
                    logger.log_complete_file()
                    print(f"[COMPLETE] Peer {peer_state.peer_id} now has the complete file.")
                    print(f"[FILE WRITE] Peer {peer_state.peer_id} reconstructed file at: {output_path}")
                    connection.send_not_interested()
                    print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent NOT INTERESTED to peer {remote_peer_id}")
                else:
                    request_next_piece(connection, peer_state)

            elif msg_type == MESSAGE_TYPES["have"]:
                piece_index = parse_have_payload(parsed["payload"])
                ensure_remote_bitfield(connection, peer_state.piece_manager.num_pieces)
                connection.remote_bitfield[piece_index] = True
                print(f"[HAVE RECEIVE] Peer {peer_state.peer_id} received HAVE for piece {piece_index} from peer {remote_peer_id}")

                if peer_state.piece_manager.needs_piece(piece_index):
                    if not connection.am_interested:
                        connection.send_interested()
                        print(f"[INTEREST SEND] Peer {peer_state.peer_id} sent INTERESTED to peer {remote_peer_id}")

                    if not connection.am_choked:
                        request_next_piece(connection, peer_state)

            else:
                print(f"[RECEIVE LOOP] Peer {peer_state.peer_id} got unexpected message type {parsed['type_name']} from peer {remote_peer_id}")

        except Exception as e:
            print(f"[RECEIVE LOOP END] Peer {peer_state.peer_id} connection with peer {remote_peer_id} ended: {e}")
            break


def choose_preferred_neighbors(peer_state: PeerState, logger: PeerLogger) -> None:
    k = peer_state.common_config.number_of_preferred_neighbors
    connections = peer_state.all_connections()

    interested_ids = [
        peer_id for peer_id, conn in connections.items()
        if conn.peer_is_interested
    ]

    if not interested_ids:
        with peer_state.state_lock:
            peer_state.preferred_neighbors = set()
        return

    if peer_state.piece_manager.has_complete_file():
        random.shuffle(interested_ids)
        selected = set(interested_ids[:k])
    else:
        shuffled = interested_ids[:]
        random.shuffle(shuffled)
        with peer_state.state_lock:
            selected = set(
                sorted(
                    shuffled,
                    key=lambda pid: peer_state.download_counts.get(pid, 0),
                    reverse=True,
                )[:k]
            )

    with peer_state.state_lock:
        peer_state.preferred_neighbors = selected

    logger.log_preferred_neighbors(sorted(selected))
    print(f"[PREFERRED] Peer {peer_state.peer_id} preferred neighbors: {sorted(selected)}")


def choose_optimistic_neighbor(peer_state: PeerState, logger: PeerLogger) -> None:
    connections = peer_state.all_connections()

    with peer_state.state_lock:
        preferred = set(peer_state.preferred_neighbors)

    candidates = [
        peer_id for peer_id, conn in connections.items()
        if conn.peer_is_interested and peer_id not in preferred and conn.peer_is_choked
    ]

    if not candidates:
        with peer_state.state_lock:
            peer_state.optimistic_neighbor = None
        return

    chosen = random.choice(candidates)

    with peer_state.state_lock:
        peer_state.optimistic_neighbor = chosen

    logger.log_optimistic_unchoke(chosen)
    print(f"[OPTIMISTIC] Peer {peer_state.peer_id} optimistic neighbor: {chosen}")


def apply_choking_rules(peer_state: PeerState) -> None:
    connections = peer_state.all_connections()

    with peer_state.state_lock:
        preferred = set(peer_state.preferred_neighbors)
        optimistic = peer_state.optimistic_neighbor

    for peer_id, connection in connections.items():
        should_unchoke = peer_id in preferred or peer_id == optimistic

        if should_unchoke and connection.peer_is_choked:
            connection.send_unchoke()
            print(f"[UNCHOKE SEND] Peer {peer_state.peer_id} sent UNCHOKE to peer {peer_id}")

        elif not should_unchoke and not connection.peer_is_choked:
            connection.send_choke()
            print(f"[CHOKE SEND] Peer {peer_state.peer_id} sent CHOKE to peer {peer_id}")


def preferred_neighbor_scheduler(peer_state: PeerState, logger: PeerLogger) -> None:
    interval = peer_state.common_config.unchoking_interval

    while True:
        time.sleep(interval)
        choose_preferred_neighbors(peer_state, logger)
        apply_choking_rules(peer_state)
        peer_state.reset_download_counts()


def optimistic_unchoke_scheduler(peer_state: PeerState, logger: PeerLogger) -> None:
    interval = peer_state.common_config.optimistic_unchoking_interval

    while True:
        time.sleep(interval)
        choose_optimistic_neighbor(peer_state, logger)
        apply_choking_rules(peer_state)


def setup_connection_after_handshake_and_bitfield(connection: ConnectionHandler, peer_state: PeerState) -> None:
    remote_peer_id = connection.remote_peer_id

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

            setup_connection_after_handshake_and_bitfield(connection, peer_state)

            threading.Thread(
                target=receiver_loop,
                args=(connection, peer_state, logger),
                daemon=True,
            ).start()

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

    print("=== Phase G: Preferred Neighbors + Optimistic Unchoking ===")
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

            setup_connection_after_handshake_and_bitfield(connection, peer_state)

            threading.Thread(
                target=receiver_loop,
                args=(connection, peer_state, logger),
                daemon=True,
            ).start()

        except Exception as e:
            print(f"[CONNECT ERROR] Peer {peer_state.peer_id} could not complete setup with peer {remote_peer.peer_id}: {e}")

    threading.Thread(
        target=preferred_neighbor_scheduler,
        args=(peer_state, logger),
        daemon=True,
    ).start()

    threading.Thread(
        target=optimistic_unchoke_scheduler,
        args=(peer_state, logger),
        daemon=True,
    ).start()

    print("\n[RUNNING] Peer is now waiting. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(2)
            print("\n=== Active Connections Summary ===")
            for remote_id, connection in peer_state.all_connections().items():
                print(f"{remote_id}: {connection.summary()}")

            print(f"Total active connections stored: {peer_state.connection_count()}")
            print(f"Current owned pieces: {peer_state.piece_manager.piece_count()}")

    except KeyboardInterrupt:
        print(f"\n[SHUTDOWN] Stopping peer {peer_state.peer_id}...")

        peer_server.close()

        for connection in peer_state.all_connections().values():
            connection.close()

        print(f"[SHUTDOWN] Peer {peer_state.peer_id} closed server and connections.")


if __name__ == "__main__":
    main()