import socket
import ssl

hostname = "localhost"
port = 55555
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.load_verify_locations("./test.crt")

with socket.create_connection((hostname, port)) as sock:
    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
        while True:
            ssock.send(input().encode("utf-8"))
            print(ssock.recv(1024).decode())
