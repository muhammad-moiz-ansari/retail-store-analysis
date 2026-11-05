import json
import xml.etree.ElementTree as ET

from .cvat_import import spans


def test_spans_split_on_outside():
    t = ET.fromstring('<track><box frame="10" outside="0"/><box frame="20" outside="1"/>'
                      '<box frame="30" outside="0"/><box frame="40" outside="0"/></track>')
    assert spans(t) == [(10, 19), (30, 40)]
