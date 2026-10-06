class StickyTable:
    def __init__(self):
        self.owner = {}

    def lookup(self, session):
        return self.owner.get(session) if session else None

    def remember(self, session, backend_id):
        if session:
            self.owner[session] = backend_id


def has_room(backend, active):
    return active <= backend.max_conns
