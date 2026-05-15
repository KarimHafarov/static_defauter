import uasyncio as asyncio
import ure as re
import usocket as socket

class Request:
    def __init__(self, method, path, headers, body, query):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query = query

class Response:
    def __init__(self, body='', status=200, content_type='text/html'):
        self.body = body
        self.status = status
        self.content_type = content_type

    def to_bytes(self):
        body = self.body
        if isinstance(body, str):
            body = body.encode('utf-8')
        return ("HTTP/1.0 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(self.status, self.content_type, len(body)).encode('utf-8') + body)

class Microdot:
    def __init__(self):
        self.routes = []

    def route(self, path, methods=['GET']):
        def decorator(func):
            self.routes.append((path, methods, func))
            return func
        return decorator

    async def _handle(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                await writer.aclose()
                return
            request_line = request_line.decode('utf-8').strip()
            parts = request_line.split(' ')
            if len(parts) < 2:
                await writer.aclose()
                return
            method = parts[0]
            raw_path = parts[1]
            path = raw_path.split('?', 1)[0]
            query = ''
            if '?' in raw_path:
                query = raw_path.split('?', 1)[1]
            headers = {}
            while True:
                line = await reader.readline()
                if not line or line == b'\r\n':
                    break
                header = line.decode('utf-8').strip()
                if ':' in header:
                    key, value = header.split(':', 1)
                    headers[key.lower()] = value.strip()
            length = int(headers.get('content-length', 0))
            body = b''
            if length:
                body = await reader.read(length)
            request = Request(method, path, headers, body, query)
            response = None
            for route, methods, func in self.routes:
                if route == path and method in methods:
                    response = await func(request)
                    break
            if response is None:
                response = Response('<h1>404 Not Found</h1>', status=404)
            if isinstance(response, str):
                response = Response(response)
            await writer.awrite(response.to_bytes())
        except Exception:
            try:
                await writer.awrite(Response('<h1>500 Internal Server Error</h1>', status=500).to_bytes())
            except Exception:
                pass
        finally:
            try:
                await writer.aclose()
            except Exception:
                pass

    def run(self, host='0.0.0.0', port=80):
        loop = asyncio.get_event_loop()
        loop.create_task(asyncio.start_server(self._handle, host, port))
        loop.run_forever()
