def success(data=None, status=200):
    return ({"ok": True, "data": data or {}}, status)

def fail(message, status=400, code=None):
    body = {"ok": False, "error": {"message": str(message)}}
    if code: body["error"]["code"] = code
    return (body, status)
