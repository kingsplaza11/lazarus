import sqlite3

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from core.legacy import load_legacy


class Command(BaseCommand):
    help = "Load data from a legacy TaskFreak! 0.6.4 database (frk_* tables)."

    def add_arguments(self, parser):
        src = parser.add_mutually_exclusive_group(required=True)
        src.add_argument("--database", help="Alias of a database in settings.DATABASES holding the legacy tables.")
        src.add_argument("--sqlite", help="Path to a SQLite file holding the legacy tables.")

    def handle(self, *args, **opts):
        if opts["sqlite"]:
            conn = sqlite3.connect(opts["sqlite"])
        else:
            try:
                conn = connections[opts["database"]]
            except Exception as e:
                raise CommandError(str(e))
        try:
            counts = load_legacy(conn, stdout=self.stdout)
        except Exception as e:
            raise CommandError("Legacy load failed, nothing was imported: %s" % e)
        finally:
            if opts["sqlite"]:
                conn.close()
        self.stdout.write(self.style.SUCCESS("Loaded %d rows." % sum(counts.values())))
