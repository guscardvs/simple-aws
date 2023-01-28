import io
from dataclasses import dataclass
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from xml.etree import ElementTree as ET

from simple_aws.exc import RequestFailed
from simple_aws.utils import xmlns

from .core import S3Core

DEFAULT_ENCODING = "UTF-8"


class ObjectTuple(NamedTuple):
    object_name: str
    version: Optional[str] = None


@dataclass(frozen=True)
class DeleteMany:
    core: S3Core
    objects: Sequence[ObjectTuple]

    def delete(self):
        url = self.core.get_uri_copy().add({"delete": ""}, path="/")
        payload = self._build_payload()

        with self.core.context.begin() as client:
            response = client.post(
                url,
                data=payload,
                headers={"content-type": "text/xml"},
            )
            if not response.ok:
                raise RequestFailed(response)

    def _build_payload(self):
        root = ET.Element("Delete", xmlns=xmlns)
        for item in self.objects:
            object_el = ET.SubElement(root, "Object")
            ET.SubElement(object_el, "Key").text = item.object_name
            if item.version:
                ET.SubElement(object_el, "VersionId").text = item.version
        et = ET.ElementTree(root)
        stream = io.BytesIO()
        et.write(stream, encoding=DEFAULT_ENCODING, xml_declaration=True)
        return stream.getvalue()
