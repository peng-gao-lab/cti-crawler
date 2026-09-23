from . import manifest

COLLECTION = "blackorbird/APT_REPORT"
SELECTION = "actor_scope"


class Adapter:
    """Report PDFs of the blackorbird/APT_REPORT GitHub collection, from a frozen local manifest.

    Prepared offline by script/python/prepare_blackorbird_manifest.py. This source only serves
    entries selected as `actor_scope`: PDFs inside the repository's actor and campaign directories,
    plus individually reviewed exceptions recorded in the preparation input. Selection is a scope
    decision, not a content verdict: nothing here has been judged article by article, so every
    report keeps `review_status: unreviewed`. The repository is a third-party aggregation; the
    maintainer is not the publisher of the reports, and publisher or original URL are only filled
    in where the preparation step had evidence.
    """

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.stop_event = stop_event

    def discover(self):
        data = manifest.load(self.source, COLLECTION)
        yield from manifest.reports(self.source, data, COLLECTION, self.stop_event,
                                    accepts=lambda item: item.get("selection") == SELECTION)
