import socket

class PeerServer:
    def __init__(self, host: str, port: int, peer_id: int):
        self.host = host
        self.port = port
        self.peer_id = peer_id
        self.server_socket = None
        self.is_listening = False

    def create_socket(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def bind_and_listen(self, backlog: int = 5) -> None:
        if self.server_socket is None:
            self.create_socket()

        self.server_socket.bind(("", self.port))
        self.server_socket.listen(backlog)
        self.is_listening = True

    def close(self) -> None:
        if self.server_socket is not None:
            self.server_socket.close()
            self.server_socket = None
            self.is_listening = False

    def __repr__(self) -> str:
        return (
            f"PeerServer(peer_id={self.peer_id}, host='{self.host}', "
            f"port={self.port}, is_listening={self.is_listening})"
        )


