from disquotes.model.types import EVENT_TYPES


def validate_push(form, msg_type):
    msg_type = msg_type.strip().lower()

    if msg_type not in EVENT_TYPES:
        return {"type": "invalid:%s" % (msg_type)}

    return None
