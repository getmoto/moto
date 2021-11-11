import re

import moto.backend_index as backend_index
import moto.backends as backends
from aiohttp import web


def get_service():
    return "s3"


async def handle_all(request):
    if not str(request.url) == "http://localhost:5000/moto-api/reset":
        print(request)
        print(request.url)
        print(request.host)
        print(request.headers)
        if request.can_read_body:
            # TODO: Pass the co-routine to S3?
            request.data = await request.text()
            print(request.data)
            request.files = None
        else:
            print("no body")
            request.data = ""
            request.files = None
        print("=================")
    service = get_service()
    backend = list(backends.get_backend(service).values())[0]
    print(backend)
    print(type(backend))
    print("===========")
    for path, handler in backend.url_paths.items():
        if re.match(path, str(request.rel_url)):
            resp = handler(request, str(request.url), request.headers)
            print(resp)
            if type(resp) == tuple:
                status, headers, body = resp
                return web.Response(body=body, status=status, headers=headers)
        else:
            print(f"{path} does not match {request.rel_url}")

    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    print("-------------")
    print("returning name?")
    return web.Response(text=text)


app = web.Application()
for op in [web.get, web.post, web.put, web.delete]:
    app.add_routes([op("/{tail:.*}", handle_all)])
#app.router.add_route("*", "/", MyView)

if __name__ == '__main__':
    web.run_app(app, port=5000)
