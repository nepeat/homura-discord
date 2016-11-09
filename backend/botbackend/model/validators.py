from botbackend.model.types import EVENT_TYPES

def validate_push(form):
    try:
        msg_type = form["type"].decode("utf-8")
    except:
        msg_type = form["type"]

    missing = [x for x in ["server", "channel", "data", "type"] if x not in form]
    if missing:
        return {"missing": missing}

    if msg_type not in EVENT_TYPES:
        return {"type": "invalid:%s" % (form["type"])}

    return None