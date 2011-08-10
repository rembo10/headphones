def ex(e):
    """
    Returns a string from the exception text if it exists.
    """
    
    # sanity check
    if not e.args or not e.args[0]:
        return ""

    e_message = e.args[0]
    
    # if fixStupidEncodings doesn't fix it then maybe it's not a string, in which case we'll try printing it anyway
    if not e_message:
        try:
            e_message = str(e.args[0])
        except:
            e_message = ""
    
    return e_message
    

class HeadphonesException(Exception):
    "Generic Headphones Exception - should never be thrown, only subclassed"

class NewzbinAPIThrottled(HeadphonesException):
    "Newzbin has throttled us, deal with it"
