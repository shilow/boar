""" The Front class is a facade for the Repository, SessionWriter and
SessionReader classes. It provides some convenience methods, but its
primary purpose is to provide an interface that is easy to use over
RPC. All arguments and return values are primitive values that can be
serialized easily.
"""


from blobrepo import repository
import sys

if sys.version_info >= (2, 6):
    import json
else:
    import simplejson as json
import base64

class Front:
    def __init__(self, repo):
        self.repo = repo
        self.new_session = None
        self.blobs_to_verify = []

    def get_repo_path(self):
        return self.repo.get_repo_path()

    def get_session_ids(self, filter = {}):
        return self.repo.get_all_sessions()

    def get_session_info(self, id):
        return self.get_session_property(id, 'client_data')

    def get_session_property(self, id, property_name):
        session_reader = self.repo.get_session(id)        
        properties = session_reader.get_properties()
        assert property_name in properties
        return properties[property_name]

    def get_session_bloblist(self, id):
        session_reader = self.repo.get_session(id)
        bloblist = list(session_reader.get_all_blob_infos())
        seen = set()
        for b in bloblist:
            assert b['filename'] not in seen, "Duplicate file found in bloblist - internal error"
            seen.add(b['filename'])
        return bloblist

    def create_session(self, base_session = None):
        self.new_session = self.repo.create_session(base_session)

    def add_blob_data(self, blob_md5, b64data):
        """ Must be called after a create_session()  """
        self.new_session.add_blob_data(blob_md5, base64.b64decode(b64data))

    def add(self, metadata):
        """ Must be called after a create_session(). Adds a link to a existing
        blob. Will throw an exception if there is no such blob """
        assert metadata.has_key("md5sum")
        self.new_session.add(metadata)

    def remove(self, filename):
        """ Remove the given file in the workdir from the current
        session. Requires that the current session has a base
        session""" 
        self.new_session.remove(filename)

    def commit(self, sessioninfo = {}):
        id = self.new_session.commit(sessioninfo)
        self.new_session = None
        return id

## Disabled until I can figure out how to make transparent 
##calls with binary data in jasonrpc
#    def get_blob(self, sum):
#        return self.repo.get_blob(sum)

    def get_blob_size(self, sum):
        return self.repo.get_blob_size(sum)

    def get_blob_b64(self, sum, offset = 0, size = -1):
        blobpart = self.repo.get_blob(sum, offset, size)
        return base64.b64encode(blobpart)

    def has_blob(self, sum):
        if self.new_session:
            return self.repo.has_blob(sum) or self.new_session.has_blob(sum)
        return self.repo.has_blob(sum)

    def find_last_revision(self, session_name):
        all_sids = self.get_session_ids()
        all_sids.sort()
        all_sids.reverse()
        for sid in all_sids:
            session_info = self.get_session_info(sid)
            name = session_info.get("name", "<no name>")
            if name == session_name:
                return sid
        return None

    def init_verify_blobs(self):
        assert self.blobs_to_verify == []
        self.blobs_to_verify = self.repo.get_blob_names()
        return len(self.blobs_to_verify)

    def verify_some_blobs(self):
        succeeded = []
        count = min(100, len(self.blobs_to_verify))
        for i in range(0, count):
            blob_to_verify = self.blobs_to_verify.pop()
            result = self.repo.verify_blob(blob_to_verify)
            assert result, "Blob failed verification:" + blob_to_verify
            succeeded.append(blob_to_verify)
        return succeeded

class DryRunFront:

    def __init__(self, front):
        self.realfront = front

    def get_repo_path(self):
        return self.realfront.get_repo_path()

    def get_session_ids(self, filter = {}):
        return self.realfront.get_session_ids(filter)

    def get_session_info(self, id):
        return self.realfront.get_session_properties(id)['client_data']

    def get_session_bloblist(self, id):
        return self.realfront.get_session_bloblist(id)

    def create_session(self, base_session = None):
        pass

    def add_blob_data(self, blob_md5, b64data):
        pass

    def add(self, metadata):
        pass

    def remove(self, filename):
        pass

    def commit(self, sessioninfo = {}):
        return 0

    def get_blob_size(self, sum):
        return self.realfront.get_blob_size(sum)

    def get_blob_b64(self, sum, offset = 0, size = -1):
        return self.realfront.get_blob_b64(sum, offset, size)

    def has_blob(self, sum):
        return self.realfront.has_blob(sum)

    def find_last_revision(self, session_name):
        return self.realfront.find_last_revision(session_name)
