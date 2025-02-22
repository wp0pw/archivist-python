"""Attachments interface

   Direct access to the attachments endpoint

   The user is not expected to use this class directly. It is an attribute of the
   :class:`Archivist` class.

   For example instantiate an Archivist instance and execute the methods of the class:

   .. code-block:: python

      with open(".auth_token", mode="r", encoding="utf-8") as tokenfile:
          authtoken = tokenfile.read().strip()

      # Initialize connection to Archivist
      arch = Archivist(
          "https://app.rkvst.io",
          authtoken,
      )
      with open("something.jpg") as fd:
          attachment = arch.attachments.upload(fd)

"""

# pylint:disable=too-few-public-methods

from __future__ import annotations
from copy import deepcopy
from io import BytesIO
from logging import getLogger
from os import path
from typing import BinaryIO, Optional, Any

from requests.models import Response

# pylint:disable=cyclic-import      # but pylint doesn't understand this feature
from . import archivist

from .constants import (
    ATTACHMENTS_SUBPATH,
    ATTACHMENTS_LABEL,
)
from .dictmerge import _deepmerge
from .utils import get_url

LOGGER = getLogger(__name__)


class Attachment(dict):
    """Attachment

    Attachment object has dictionary attributes.

    """


class _AttachmentsClient:
    """AttachmentsClient

    Access to attachments entities using CRUD interface. This class is usually
    accessed as an attribute of the Archivist class.

    Args:
        archivist (Archivist): :class:`Archivist` instance

    """

    def __init__(self, archivist_instance: archivist.Archivist):
        self._archivist = archivist_instance
        self._subpath = f"{archivist_instance.root}/{ATTACHMENTS_SUBPATH}"
        self._label = f"{self._subpath}/{ATTACHMENTS_LABEL}"

    def __str__(self) -> str:
        return f"AttachmentsClient({self._archivist.url})"

    def get_default_key(self, data: dict[str, str]) -> str:
        """
        Return a key to use if no key was provided
        either use filename or url as one of them is required
        """
        attachment_key = (
            data.get("filename", "")
            if data.get("filename", "")
            else data.get("url", "")
        )
        return attachment_key.replace(".", "_")

    def create(self, data: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
        """
        Create an attachment and return struct suitable for use in an asset
        or event creation.

        Args:
            data (dict): dictionary

        A YAML representation of the data argument would be:

            .. code-block:: yaml

                filename: functests/test_resources/doors/assets/gdn_front.jpg
                content_type: image/jpg
                display_name: arc_primary_image

            OR

            .. code-block:: yaml

                url: https://secure.eicar.org/eicar.com.zip"
                content_type: application/zip
                display_name: Test malware

             Either 'filename' or 'url' is required.
             'content_type' is required.

        Returns:

            A dict suitable for adding to an asset or event creation

        A YAML representation of the result would be:

            .. code-block:: yaml

                arc_display_name: Telephone
                arc_blob_identity: blobs/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                arc_blob_hash_alg: SHA256
                arc_blob_hash_value: xxxxxxxxxxxxxxxxxxxxxxx
                arc_file_name: gdn_front.jpg

        """
        result = None
        file_part = None
        filename = data.get("filename")
        if filename is not None:
            _, file_part = path.split(filename)
            with open(filename, "rb") as fd:
                attachment = self.upload(fd, mtype=data.get("content_type"))

        else:
            url = data["url"]
            fd = BytesIO()
            get_url(url, fd)
            attachment = self.upload(fd, mtype=data.get("content_type"))

        result = {
            "arc_attribute_type": "arc_attachment",
            "arc_blob_identity": attachment["identity"],
            "arc_blob_hash_alg": attachment["hash"]["alg"],
            "arc_blob_hash_value": attachment["hash"]["value"],
        }

        if file_part:
            result["arc_file_name"] = file_part

        display_name = data.get("display_name")
        if display_name is not None:
            result["arc_display_name"] = display_name

        return result

    def upload(self, fd: BinaryIO, *, mtype: Optional[str] = None) -> Attachment:
        """Create attachment

        Creates attachment from opened file or other data source.

        Args:
            fd (file): opened file descriptor or other file-type iterable.
            mtype (str): mimetype of data.

        Returns:
            :class:`Attachment` instance

        """

        LOGGER.debug("Upload Attachment")
        return Attachment(
            **self._archivist.post_file(
                self._label,
                fd,
                mtype,
            )
        )

    def __params(self, params: Optional[dict[str, Any]]) -> dict[str, Any]:
        params = deepcopy(params) if params else {}
        # pylint: disable=protected-access
        return _deepmerge(self._archivist.fixtures.get(ATTACHMENTS_LABEL), params)

    def download(
        self,
        identity: str,
        fd: BinaryIO,
        *,
        params: Optional[dict[str, Any]] = None,
    ) -> Response:
        """Read attachment

        Reads attachment into data sink (usually a file opened for write)..
        Note that returns the response as the body will be consumed by the
        fd iterator

        Args:
            identity (str): attachment identity e.g. blobs/xxxxxxxxxxxxxxxxxxxxxxx
            fd (file): opened file descriptor or other file-type sink..
            params (dict): e.g. {"allow_insecure": "true"} OR {"strict": "true" }

        Returns:
            JSON as dict

        """
        return self._archivist.get_file(
            f"{self._subpath}/{identity}",
            fd,
            params=self.__params(params),
        )

    def info(
        self,
        identity: str,
    ) -> dict[str, Any]:
        """Read attachment info

        Reads attachment info

        Args:
            identity (str): attachment identity e.g. blobs/xxxxxxxxxxxxxxxxxxxxxxx

        Returns:
            REST response

        """
        return self._archivist.get(f"{self._subpath}/{identity}/info")
