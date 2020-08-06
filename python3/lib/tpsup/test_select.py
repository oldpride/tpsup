import selectors
import socket


if hasattr(selectors, 'PollSelector'):
    _ServerSelector = selectors.PollSelector
else:
    _ServerSelector = selectors.SelectSelector

class test_select:
    def __init__(self, port=9999):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('0.0.0.0', int(port)))
        self.socket.listen(5)
        self.selector = selectors.SelectSelector()
        self.selector.register(self.socket, selectors.EVENT_READ)
        self.clientsocket = None

        timeout = 10
        for i in range(0, timeout):
            print(f"polling #{i}")
            ready = self.selector.select(1)

            if ready:
                (clientsocket, address) = self.socket.accept()
                print(f"accepted client socket {clientsocket}, address={address}")
                self.clientsocket = clientsocket
        print(f'no client seen')


def main():
    tester = test_select(9999)

if __name__ == '__main__':
    main()
