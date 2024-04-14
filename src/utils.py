"""Utils functions."""
import json
import jsonpickle

def printf(*args):
    """Print without delay."""
    print(*args, flush=True)

def dump(obj: object):
    serialized = jsonpickle.encode(obj)
    printf(json.dumps(json.loads(serialized), indent=2))
