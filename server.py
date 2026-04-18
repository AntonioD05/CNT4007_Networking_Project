import socket
from typing import Optional, Tuple


class PeerServer:
    def __init__(self, host: str, port: int, peer_id: int):
        self.host = host
        self.port = port
        self.peer_id = peer_id
        self.server_socket: Optional[socket.socket] = None
        self.is_listening = False

    def create_socket(self) -> None:
        """
        Create the TCP server socket.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def bind_and_listen(self, backlog: int = 5) -> None:
        """
        Bind the socket and begin listening for incoming connections.
        """
        if self.server_socket is None:
            self.create_socket()

        self.server_socket.bind(("", self.port))
        self.server_socket.listen(backlog)
        self.is_listening = True

    def accept_connection(self) -> Tuple[socket.socket, Tuple[str, int]]:
        """
        Accept one incoming connection.
        Returns:
            (client_socket, client_address)
        """
        if self.server_socket is None or not self.is_listening:
            raise RuntimeError("Server is not listening")

        client_socket, client_address = self.server_socket.accept()
        return client_socket, client_address

    def close(self) -> None:
        """
        Close the server socket cleanly.
        """
        if self.server_socket is not None:
            try:
                self.server_socket.close()
            finally:
                self.server_socket = None
                self.is_listening = False

    def __repr__(self) -> str:
        return (
            f"PeerServer(peer_id={self.peer_id}, host='{self.host}', "
            f"port={self.port}, is_listening={self.is_listening})"
        )