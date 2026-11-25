"""Prepare the demo corpse on a fresh deploy: summon, autopsy, spec, saved check.

    python manage.py preload_demo               # on the server (run by build.sh)
    python manage.py preload_demo --save-check  # locally, once: saves your latest TaskFreak check
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from autopsy.models import Autopsy
from autopsy.services import run_autopsy
from intake.services import summon_demo
from lazarus.choices import Status
from parity.models import ResurrectionCheck
from parity.services import latest_check
from specgen.services import generate_for_corpse, latest_spec

CHECK_FILE = Path(settings.BASE_DIR) / "samples" / "taskfreak-check.json"


class Command(BaseCommand):
    help = "Summon the demo corpse, run its autopsy and spec, and load the saved resurrection check."

    def add_arguments(self, parser):
        parser.add_argument("--save-check", action="store_true",
                            help="Write this machine's latest TaskFreak check to samples/taskfreak-check.json.")

    def handle(self, *args, **opts):
        corpse = summon_demo()
        if opts["save_check"]:
            check = latest_check(corpse)
            if check is None:
                self.stderr.write("No resurrection check for the demo corpse yet.")
                return
            CHECK_FILE.write_text(json.dumps(
                {"target_url": check.target_url, "score": check.score, "results": check.results}, indent=2))
            self.stdout.write(f"Saved {check.score}% check to {CHECK_FILE}")
            return

        if not Autopsy.objects.filter(corpse=corpse, status=Status.DONE).exists():
            run_autopsy(corpse)
            self.stdout.write("Autopsy done.")
        if latest_spec(corpse) is None:
            generate_for_corpse(corpse)
            self.stdout.write("Spec written.")
        if latest_check(corpse) is None and CHECK_FILE.exists():
            data = json.loads(CHECK_FILE.read_text())
            ResurrectionCheck.objects.create(corpse=corpse, target_url=data["target_url"], source_path="",
                                             score=data["score"], results=data["results"])
            self.stdout.write(f"Loaded saved check: {data['score']}%")
        self.stdout.write(self.style.SUCCESS(f"Demo corpse ready: /corpses/{corpse.pk}/"))
