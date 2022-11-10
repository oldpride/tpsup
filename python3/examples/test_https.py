from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl

# https://blog.anvileight.com/posts/simple-python-http-server/

from io import BytesIO

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        # to test GET from browser: https://localhost:9000/
        # to test GET from command line:
        # curl -k -i -X GET https://localhost:9000
        # HTTP/1.0 200 OK
        # Server: BaseHTTP/0.6 Python/3.8.5
        # Date: Sun, 22 May 2022 03:02:39 GMT
        #
        # Hello, world!

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Hello, world!')

    def do_POST(self):
        # to test POST from browser: install chrome app Postman
        # to test POST from command line:
        # curl -k -i -X POST -H 'Content-Type: application/json' -d '{"name": "New item", "year": "2009"}' https://localhost:9000
        # HTTP/1.0 200 OK
        # Server: BaseHTTP/0.6 Python/3.8.5
        # Date: Sun, 22 May 2022 02:59:50 GMT
        #
        # This is POST request. Received: {"name": "New item", "year": "2009"}tian@linux1:/home/tian/site
        
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        response.write(body)
        self.wfile.write(response.getvalue())

# httpd = HTTPServer(('localhost', 9000), BaseHTTPRequestHandler)
httpd = HTTPServer(('localhost', 9000), SimpleHTTPRequestHandler)

httpd.socket = ssl.wrap_socket (
        httpd.socket,
        # $ openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365
        keyfile="/home/tian/.tpsup/key.pem",
        certfile='/home/tian/.tpsup/cert.pem',
        server_side=True)

httpd.serve_forever()