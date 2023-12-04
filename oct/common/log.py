import os
import requests
import threading


__all__ = (
    "log_err",
)


WEBHOOK_URL = os.getenv("WEBHOOK")


def header_embed():
    return dict({
        "title": "Headers",
        "fields": list(),
        "color": 0x0000ff
    })


def log_err(req, e):
    embeds = []
    embeds.append({
        "title": f"{req.method} {req.path}",
        "description": str(e),
        "color": 0xff0000,
    })
    embeds.append(header_embed())
    for name, value in req.headers.items():
        if len(embeds[-1]["fields"]) == 25:
            embeds.append(header_embed())
        embeds[-1]["fields"].append({"name": name, "value": value})
    threading.Thread(target=requests.post, args=(WEBHOOK_URL,), kwargs={"json": {"embeds": embeds}}).start()
