PUBLIC = 0
PROTECTED = 1
PRIVATE = 2


def access_type(node):
    v = node.attrib.get("access")

    if not v or v == "public":
        return PUBLIC
    elif v == "protected":
        return PROTECTED
    else:
        return PRIVATE
