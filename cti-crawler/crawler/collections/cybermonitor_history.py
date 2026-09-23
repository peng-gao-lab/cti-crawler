from . import manifest

COLLECTION = "CyberMonitor/APT_CyberCriminal_Campagin_Collections"
SELECTION = "new_candidate"


class Adapter:
    """Report PDFs of the CyberMonitor GitHub collection, from a frozen local manifest.

    Prepared offline from the repository's file tree. This source only serves entries selected as
    `new_candidate`: report PDFs that our collection did not already hold by file name, URL slug or
    title. The collection is a third-party aggregation of browser print copies; CyberMonitor is not
    the publisher of the reports.
    """

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.stop_event = stop_event

    def discover(self):
        data = manifest.load(self.source, COLLECTION)
        yield from manifest.reports(self.source, data, COLLECTION, self.stop_event,
                                    accepts=lambda item: item.get("selection") == SELECTION)
