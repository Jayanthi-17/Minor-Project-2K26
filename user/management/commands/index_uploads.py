import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from manager.models import uploadmodel
from user.models import weightmodel
from user.ranking import compute_weight, index_document


class Command(BaseCommand):
    help = "Calculate the ML weight for uploaded files so they show up in search."

    def handle(self, *args, **options):
        total = 0

        uploads = uploadmodel.objects.all()
        self.stdout.write("Uploads found in database: %d" % uploads.count())
        for u in uploads:
            try:
                index_document(u)
                total += 1
                self.stdout.write("indexed: %s" % u.filename)
            except Exception as e:
                self.stdout.write("FAILED : %s (%s)" % (u.filename, e))

        # also index .txt files that are in the media folder but not in the database
        folder = os.path.join(settings.MEDIA_ROOT, "files", "pdfs")
        known = set(weightmodel.objects.values_list("file", flat=True))
        if os.path.isdir(folder):
            for name in sorted(os.listdir(folder)):
                rel = "files/pdfs/" + name
                stem = os.path.splitext(name)[0]
                if rel in known or not name.lower().endswith(".txt"):
                    continue
                if re.search(r"_[A-Za-z0-9]{7}$", stem):   # Django's duplicate copies
                    continue
                try:
                    s, rank, label = compute_weight(os.path.join(folder, name))
                    weightmodel.objects.update_or_create(
                        file=rel,
                        defaults={"filename": stem, "weight": s, "rank": rank, "label": label},
                    )
                    total += 1
                    self.stdout.write("indexed from folder: %s" % name)
                except Exception as e:
                    self.stdout.write("FAILED : %s (%s)" % (name, e))

        self.stdout.write(self.style.SUCCESS(
            "Done. %d file(s) indexed. Searchable documents now: %d"
            % (total, weightmodel.objects.count())))