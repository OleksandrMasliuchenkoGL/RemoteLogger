import socketserver
from datetime import datetime

class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"{datetime.now()}: Accepted connection from {self.client_address[0]}")

        while True:
            self.data = self.request.recv(1024)
            if not self.data: break
            print(f"{datetime.now()} {self.client_address[0]}: {self.data.decode('utf-8').strip()}")

    def finish(self):
        print(f"{datetime.now()}: Connection from {self.client_address[0]} dropped")

if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("0.0.0.0", 9999), MyTCPHandler, True) as server:
        server.serve_forever()
