import sys
from config_loader import load_common_config, load_peer_info, get_peer_by_id


def main():
    if len(sys.argv) != 2:
        print("Usage: python peerProcess.py <peer_id>")
        sys.exit(1)

    peer_id = int(sys.argv[1])

    common_config = load_common_config()
    peers = load_peer_info()
    current_peer = get_peer_by_id(peer_id, peers)

    print("=== Common Config ===")
    print(common_config)

    print("\n=== All Peers ===")
    for peer in peers:
        print(peer)

    print("\n=== Current Peer ===")
    print(current_peer)


if __name__ == "__main__":
    main()