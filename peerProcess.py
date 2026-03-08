import sys

from config_loader import load_common_config, load_peer_info, get_peer_by_id
from peer_state import PeerState


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 peerProcess.py <peer_id>")
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


if __name__ == "__main__":
    main()