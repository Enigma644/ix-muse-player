import textwrap

class LibloErrorExplainer(object):
    def __init__(self, err):
        self.err = err

    def explanation(self):
        if self.err.num == 9904:    # LO_NOPORT
            return textwrap.dedent('''
                We couldn't bind to the port requested. There may already be
                another application bound to that port. Check to see if you
                have any other instances of MuseLab or muse-player reading from
                it.

                If you want to read from the same stream with two programs,
                consider running muse-player with multiple outputs, e.g.:

                    muse-player -s 5001 -s 5002
                ''')
