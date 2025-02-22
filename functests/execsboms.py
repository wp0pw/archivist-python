"""
Tests the upload and download functionality of the SDK
"""
from contextlib import suppress
from filecmp import clear_cache, cmp
from json import dumps as json_dumps
from os import getenv, remove
from time import sleep

from archivist.archivist import Archivist
from archivist.errors import ArchivistBadRequestError
from archivist.timestamp import now_timestamp
from archivist.utils import get_auth

from archivist import logger

from .constants import TestCase

# pylint: disable=fixme
# pylint: disable=missing-docstring
# pylint: disable=unused-variable


DISPLAY_NAME = "Application display name"
CUSTOM_CLAIMS = {
    "serial_number": "TL1000000101",
    "has_cyclist_light": "true",
}

RKVST_SBOM_PATH = "functests/test_resources/bom.xml"
RKVST_SBOM_SPDX_PATH = "functests/test_resources/bom.spdx"
RKVST_SBOM_DOWNLOAD_PATH = "functests/test_resources/downloaded_bom.xml"

if getenv("RKVST_LOGLEVEL") is not None:
    logger.set_logger(getenv("RKVST_LOGLEVEL"))

LOGGER = logger.LOGGER


class TestSBOM(TestCase):
    """
    Test Archivist SBOM upload/download
    """

    maxDiff = None

    def setUp(self):
        auth = get_auth(
            auth_token=getenv("RKVST_AUTHTOKEN"),
            auth_token_filename=getenv("RKVST_AUTHTOKEN_FILENAME"),
            client_id=getenv("RKVST_APPREG_CLIENT"),
            client_secret=getenv("RKVST_APPREG_SECRET"),
            client_secret_filename=getenv("RKVST_APPREG_SECRET_FILENAME"),
        )
        self.arch = Archivist(getenv("RKVST_URL"), auth, verify=False)
        self.file_uuid: str = ""
        self.title = "TestSBOM"

        with suppress(FileNotFoundError):
            remove(RKVST_SBOM_DOWNLOAD_PATH)

    def tearDown(self) -> None:
        """Remove the downloaded sbom for subsequent test runs"""
        self.arch.close()
        with suppress(FileNotFoundError):
            remove(RKVST_SBOM_DOWNLOAD_PATH)

    def test_sbom_upload_with_private_privacy(self):
        """
        Test sbom upload with privacy
        """
        now = now_timestamp()
        LOGGER.debug("Public Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_PATH, "rb") as fd:
            metadata = self.arch.sboms.upload(
                fd, confirm=True, params={"privacy": "PRIVATE"}
            )
        LOGGER.debug("first upload %s", json_dumps(metadata.dict(), indent=4))
        identity = metadata.identity

        metadata1 = self.arch.sboms.read(identity)
        LOGGER.debug("read %s", json_dumps(metadata1.dict(), indent=4))
        self.assertEqual(
            metadata,
            metadata1,
            msg="Metadata not correct",
        )

    def test_sbom_upload_with_illegal_privacy(self):
        """
        Test sbom upload with privacy
        """
        now = now_timestamp()
        LOGGER.debug("Illegal Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_PATH, "rb") as fd:
            with self.assertRaises(ArchivistBadRequestError):
                metadata = self.arch.sboms.upload(
                    fd, confirm=True, params={"privacy": "XXXXXX"}
                )

    def test_sbom_upload_with_spdx(self):
        """
        Test sbom upload with spdx
        """
        now = now_timestamp()
        LOGGER.debug("SPDX Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_SPDX_PATH, "rb") as fd:
            metadata = self.arch.sboms.upload(
                fd,
                confirm=True,
                params={
                    "sbomType": "spdx-tag",
                    "component": "spdx-test-component",
                    "version": "v0.0.1",
                },
            )
        LOGGER.debug("first upload %s", json_dumps(metadata.dict(), indent=4))
        identity = metadata.identity

        metadata1 = self.arch.sboms.read(identity)
        LOGGER.debug("read %s", json_dumps(metadata1.dict(), indent=4))
        self.assertEqual(
            metadata,
            metadata1,
            msg="Metadata not correct",
        )

    def test_sbom_upload_with_illegal_format(self):
        """
        Test sbom upload with illegal format
        """
        now = now_timestamp()
        LOGGER.debug("SPDX Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_SPDX_PATH, "rb") as fd:
            with self.assertRaises(ArchivistBadRequestError):
                metadata = self.arch.sboms.upload(
                    fd, confirm=True, params={"sbomType": "xxxxxxxx"}
                )

    def test_sbom_upload_with_confirmation(self):
        """
        Test sbom upload with confirmation
        """
        now = now_timestamp()
        LOGGER.debug("Confirmed Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_PATH, "rb") as fd:
            metadata = self.arch.sboms.upload(fd, confirm=True)
        LOGGER.debug("first upload %s", json_dumps(metadata.dict(), indent=4))
        identity = metadata.identity

        metadata1 = self.arch.sboms.read(identity)
        LOGGER.debug("read %s", json_dumps(metadata1.dict(), indent=4))
        self.assertEqual(
            metadata,
            metadata1,
            msg="Metadata not correct",
        )

        sleep(1)  # the data may have not reached cogsearch
        metadatas = list(self.arch.sboms.list(metadata={"uploaded_since": now}))
        self.assertEqual(
            len(metadatas),
            1,
            msg="No. of SBOMS should be 1",
        )

    def test_sbom_upload_with_cyclonedx_xml(self):
        """
        Test sbom upload with cyclonedx-xml
        """
        now = now_timestamp()
        LOGGER.debug("CycloneDX-XML Upload Title: %s %s", self.title, now)
        with open(RKVST_SBOM_PATH, "rb") as fd:
            metadata = self.arch.sboms.upload(
                fd, params={"sbomType": "cyclonedx-xml"}, confirm=True
            )
        LOGGER.debug("first upload %s", json_dumps(metadata.dict(), indent=4))
        identity = metadata.identity

        metadata1 = self.arch.sboms.read(identity)
        LOGGER.debug("read %s", json_dumps(metadata1.dict(), indent=4))
        self.assertEqual(
            metadata,
            metadata1,
            msg="Metadata not correct",
        )

        sleep(1)  # the data may have not reached cogsearch
        metadatas = list(self.arch.sboms.list(metadata={"uploaded_since": now}))
        self.assertEqual(
            len(metadatas),
            1,
            msg="No. of SBOMS should be 1",
        )

    def test_sbom_upload_and_download(self):
        """
        Test sbom upload and download through the SDK
        """
        now = now_timestamp()
        LOGGER.debug("Title: %s %s", self.title, now)
        with open(RKVST_SBOM_PATH, "rb") as fd:
            metadata = self.arch.sboms.upload(fd, confirm=True)

        LOGGER.debug("first upload %s", json_dumps(metadata.dict(), indent=4))
        identity = metadata.identity
        with open(RKVST_SBOM_DOWNLOAD_PATH, "wb") as fd:
            sbom = self.arch.sboms.download(identity, fd)

        LOGGER.debug("sbom %s", sbom)
        clear_cache()
        self.assertTrue(cmp(RKVST_SBOM_PATH, RKVST_SBOM_DOWNLOAD_PATH, shallow=False))

        metadata1 = self.arch.sboms.read(identity)
        LOGGER.debug("read %s", json_dumps(metadata1.dict(), indent=4))
        self.assertEqual(
            metadata,
            metadata1,
            msg="Metadata not correct",
        )

        sleep(1)  # the data may have not reached cogsearch
        metadatas = list(self.arch.sboms.list(metadata={"uploaded_since": now}))
        self.assertEqual(
            len(metadatas),
            1,
            msg="No. of SBOMS should be 1",
        )
        self.assertEqual(
            metadatas[0],
            metadata,
            msg="Metadata not correct",
        )

        for i, m in enumerate(metadatas):
            LOGGER.debug("%d: %s", i, json_dumps(m.dict(), indent=4))

        metadata2 = self.arch.sboms.publish(identity, confirm=True)
        LOGGER.debug("publish %s", json_dumps(metadata2.dict(), indent=4))
        self.assertNotEqual(
            metadata1.published_date,
            metadata2.published_date,
            msg="Published_date not correct",
        )
        metadata3 = self.arch.sboms.publish(identity, confirm=True)
        LOGGER.debug("publish again %s", json_dumps(metadata3.dict(), indent=4))
        self.assertEqual(
            metadata2.published_date,
            metadata3.published_date,
            msg="Published_date not correct",
        )

        metadata4 = self.arch.sboms.withdraw(identity, confirm=True)
        LOGGER.debug("withdraw %s", json_dumps(metadata4.dict(), indent=4))
        self.assertNotEqual(
            metadata3.withdrawn_date,
            metadata4.withdrawn_date,
            msg="Withdrawn_date not correct",
        )
        self.assertEqual(
            metadata2.published_date,
            metadata4.published_date,
            msg="Published_date not correct",
        )

        metadata5 = self.arch.sboms.withdraw(identity, confirm=True)
        LOGGER.debug("withdraw again %s", json_dumps(metadata5.dict(), indent=4))
        self.assertEqual(
            metadata4.withdrawn_date,
            metadata5.withdrawn_date,
            msg="Withdrawn_date not correct",
        )

        metadatas = list(
            self.arch.sboms.list(
                page_size=50,
                metadata={
                    "search": "*",
                    "privacy": "PUBLIC",
                },
            )
        )
        for i, m in enumerate(metadatas):
            LOGGER.debug("%d: %s", i, json_dumps(m.dict(), indent=4))
