"""python manage.py resurrection_check <corpse id> --url http://127.0.0.1:8001 --source ~/Desktop/taskfreak-reborn \
       --username admin --password lazarus-demo   [--db path/to/db.sqlite3]

Scores a rebuilt app against the legacy app's autopsy and saves the result in Lazarus.
"""
from django.core.management.base import BaseCommand, CommandError

from intake.models import Corpse
from parity.services import CheckError, run_resurrection_check

LABELS = {"pages": "Pages", "forms": "Forms", "tables": "Tables", "safety": "Safety", "look": "Look and feel"}


class Command(BaseCommand):
    help = "Check how faithfully a rebuilt app resurrects a corpse."

    def add_arguments(self, parser):
        parser.add_argument("corpse_id", type=int)
        parser.add_argument("--url", default="http://127.0.0.1:8001", help="Base URL of the running rebuild")
        parser.add_argument("--source", help="Folder of the rebuild's source code")
        parser.add_argument("--db", help="The rebuild's SQLite file (default: <source>/db.sqlite3)")
        parser.add_argument("--username", help="An account in the rebuild, to check pages signed in")
        parser.add_argument("--password")
        parser.add_argument("--details", action="store_true", help="Print every item, not just failures")

    def handle(self, *args, **options):
        try:
            corpse = Corpse.objects.get(pk=options["corpse_id"])
        except Corpse.DoesNotExist:
            raise CommandError("No corpse with that id.")
        try:
            check = run_resurrection_check(corpse, options["url"], options["source"], options["db"],
                                           options["username"], options["password"])
        except CheckError as exc:
            raise CommandError(str(exc))
        results = check.results
        for note in results["notes"]:
            self.stdout.write(f"  · {note}")
        for name, label in LABELS.items():
            cat = results["categories"][name]
            if not cat["total"]:
                continue
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{label}: {cat['passed']}/{cat['total']} ({round(cat['score'] * 100)}%)"))
            for item in cat["items"]:
                if options["details"] or item["score"] < 0.999:
                    mark = "✓" if item["score"] >= 0.999 else ("~" if item["score"] > 0 else "✗")
                    self.stdout.write(f"  {mark} {item['label']}: {item['detail']}")
        style = self.style.SUCCESS if check.score >= 80 else self.style.WARNING
        self.stdout.write(style(f"\nResurrection score: {check.score}%  ({results['summary']})"))
