import os
import socket
from datetime import datetime
import random
import string

# https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
HTTP_METHODS = set({
    'GET', 'HEAD', 'POST', 'PUT', 'DELTE', 'CONNECT', 'OPTIONS', 'TRACE',
    'PATCH'
})

# https://developer.mozilla.org/en-US/docs/Web/HTTP/MIME_types/Common_types
MIME_TYPE_EXT_IMAGE = {
    b'image/avif': b'avif',
    b'image/bmp': b'bmp',
    b'image/gif': b'gif',
    b'image/vnd.microsoft.icon': b'ico',
    b'image/jpg': b'jpg',
    b'image/jpeg': b'jpeg',
    b'image/png': b'png',
    b'image/svg+xml': b'tiff',
    b'image/webp': b'webp',
}


class Server:
    DIR_PATH = './request'
    IMAGE_DIR_PATH = './image'

    def __init__(self, addr, port):
        self.addr = addr
        self.port = port
        with open('response.bin', 'rb') as f:
            self.default_response = f.read()
        with open('response_large.bin', 'rb') as f:
            self.default_response_large = f.read()
        self.create_dir(self.DIR_PATH)
        self.create_dir(self.IMAGE_DIR_PATH)

    def create_dir(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError:
            print('cannot create directory')

    def save_raw_data(self, data: bytes):
        filename = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        ext = 'bin'
        with open(f'{self.DIR_PATH}/{filename}.{ext}', 'wb') as f:
            f.write(data)
    
    def save_image_data(self, data: bytes, ext: str):
        filename = ''. join(random.choices(string.ascii_letters + string.digits, k=15))
        with open(f'{self.IMAGE_DIR_PATH}/{filename}.{ext}', 'wb') as f:
            f.write(data)

    def parse_http_header(buf: bytearray):
        # parse http version
        http_header = {}
        ret = -1
        pos = buf.find(b'\r\n', 0, 1024)
        if pos == -1:
            return {}, ret

        method, _, ver = buf[:pos].split(b' ')

        if not method.decode() in HTTP_METHODS \
            or ver != b'HTTP/1.1':
            return {}, ret

        buf = buf[pos + 2:]
        ret = pos + 2

        while len(buf) > 0:
            pos = buf.find(b'\r\n', 0, 1024)
            if pos == -1:
                return {}, pos
            line = buf[:pos]
            ret += pos + 2
            if line == b'':
                break

            header, value = line.split(b': ', 1)

            http_header[header.decode()] = value.decode()
            buf = buf[pos + 2:]

        return http_header, ret
    
    def recv_data(client: socket.socket, buf: bytearray):
        while True:
            data = client.recv(1024)
            buf.extend(data)
            if len(data) < 1024:
                break 

    def run_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.addr, self.port))
        self.sock.listen(10)

        print(self.default_response)

        try:
            while True:
                client, _ = self.sock.accept()
                client.settimeout(5.0)

                buf = bytearray()
                
                Server.recv_data(client, buf)

                http_header, pos = Server.parse_http_header(buf)
                
                if 'Expect' in http_header:
                    client.sendall(self.default_response_large)
                    print(self.default_response_large)
                    Server.recv_data(client, buf)

                self.save_raw_data(buf)

                print('http_headr, pos = ', http_header, pos)
                print(len(buf))
                
                buf = buf[pos:]

                if http_header == {}:
                    client.sendall(self.default_response)
                    client.close()
                    continue

                content_type = http_header['Content-Type'] if 'Content-Type' in http_header else ''
                
                multipart = content_type.split(
                    'multipart/form-data; boundary=')
                
                if len(multipart) < 2:
                    client.sendall(self.default_response)
                    client.close()
                    continue

                boundary = multipart[1].encode()
                print(boundary)
                
                end_of_boundary = buf.find(b'--' + boundary + b'--\r\n')
                print(end_of_boundary)

                buf = buf[:end_of_boundary]

                multipart_data = buf.split(b'--' + boundary + b'\r\n')[1:]
                
                for i, data in enumerate(multipart_data):
                    header, content = data.split(b'\r\n\r\n')
                    # to convert bytes -> dict
                    header = dict(
                        list(
                            map(
                                lambda x: tuple(bytes(x).split(b': ', 1)),
                                header.split(b'\r\n')
                            )
                        )
                    )
                    
                    # text/plain
                    # application/octet-stream
                    
                    if b'Content-Type' in header and header[b'Content-Type'] in MIME_TYPE_EXT_IMAGE:
                        ext = MIME_TYPE_EXT_IMAGE[header[b'Content-Type']].decode()
                        self.save_image_data(content, ext)

                    print(f'================ {i}th data =====================')
                    print(header)
                    print('=================')

                client.sendall(self.default_response)
                client.close()

        except KeyboardInterrupt:
            print('keyboard interrupt!!')

        self.sock.close()


server = Server('127.0.0.1', 8080)
server.run_server()
