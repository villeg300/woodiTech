import shortuuid

def uuid_slug (length):
    return shortuuid.ShortUUID().random(length=length).lower()
    