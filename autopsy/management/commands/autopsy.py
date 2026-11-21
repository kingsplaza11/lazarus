"""python manage.py autopsy <corpse_id>         run an autopsy and print the summary
python manage.py autopsy --file path/to.php   print one file's analysis
python manage.py autopsy --tree path/to.php   print one file's raw syntax tree (debugging)
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from autopsy.parsers.forms import find_forms
from autopsy.parsers.php import debug_tree, parse_php
from autopsy.services import AutopsyError, run_autopsy
from intake.models import Corpse


class Command(BaseCommand):
    help = "Run an autopsy on a corpse, or inspect a single PHP file."

    def add_arguments(self, parser):
        parser.add_argument("corpse_id", nargs="?", type=int)
        parser.add_argument("--file", help="Analyse one PHP file and print JSON")
        parser.add_argument("--tree", help="Print the tree-sitter syntax tree of one PHP file")

    def handle(self, *args, **options):
        if options["tree"]:
            self.stdout.write(debug_tree(Path(options["tree"]).read_bytes()))
            return
        if options["file"]:
            source = Path(options["file"]).read_bytes()
            result = parse_php(source)
            result["forms"] = find_forms(source.decode("utf-8", "replace"))
            self.stdout.write(json.dumps(result, indent=2))
            return
        if not options["corpse_id"]:
            raise CommandError("Give a corpse id, --file or --tree.")
        try:
            corpse = Corpse.objects.get(pk=options["corpse_id"])
        except Corpse.DoesNotExist:
            raise CommandError("No corpse with that id.")
        try:
            autopsy = run_autopsy(corpse)
        except AutopsyError as exc:
            raise CommandError(str(exc))
        report = autopsy.report
        self.stdout.write(json.dumps(report["summary"], indent=2))
        if report["cause_of_death"]["summary"]:
            self.stdout.write(self.style.WARNING("Cause of death: " + report["cause_of_death"]["summary"]))
        self.stdout.write("Pages: " + ", ".join(p["path"] for p in report["pages"]))
        self.stdout.write("Tables: " + ", ".join(t["name"] for t in report["tables"]))
