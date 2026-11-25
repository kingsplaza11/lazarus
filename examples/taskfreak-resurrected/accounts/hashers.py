import hashlib

from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare


class LegacyMD5Hasher(BasePasswordHasher):
    """Verifies TaskFreak 0.6.4 passwords: a hex MD5 of the member's 8-char salt
    combined with the password (salt+password or password+salt).

    Stored as ``legacy_md5$<salt>$<hexdigest>`` so the value is self-contained
    and Django's ``check_password(..., setter)`` can upgrade it to the default
    hasher on the member's next successful sign-in.
    """

    algorithm = "legacy_md5"

    @staticmethod
    def _candidates(password, salt):
        for raw in (salt + password, password + salt):
            yield hashlib.md5(raw.encode()).hexdigest()

    def encode(self, password, salt):
        # Only produced by the loader's conversion (first candidate form).
        return "%s$%s$%s" % (self.algorithm, salt, next(self._candidates(password, salt)))

    @classmethod
    def wrap(cls, legacy_hash, salt):
        return "%s$%s$%s" % (cls.algorithm, salt, legacy_hash.lower())

    def decode(self, encoded):
        algorithm, salt, digest = encoded.split("$", 2)
        return {"algorithm": algorithm, "salt": salt, "hash": digest}

    def verify(self, password, encoded):
        d = self.decode(encoded)
        return any(constant_time_compare(d["hash"], c) for c in self._candidates(password, d["salt"]))

    def safe_summary(self, encoded):
        d = self.decode(encoded)
        return {"algorithm": d["algorithm"], "salt": d["salt"][:2] + "****"}

    def must_update(self, encoded):
        return True

    def harden_runtime(self, password, encoded):
        pass
