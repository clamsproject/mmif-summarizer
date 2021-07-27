from clams.appmetadata import AppMetadata
from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri

VERSION = '0.0.2'
MMIF_VERSION = '0.4.0'
MMIF_PYTHON_VERSION = '0.4.5'
CLAMS_PYTHON_VERSION = '0.4.4'


METADATA = AppMetadata(
    identifier="https://apps.clams.ai/pbcore-converter",
    name="MMIF to PBCore Converter",
    description="Convert an MMIF file into a PBCore XML document.",
    app_version=VERSION,
    mmif_version=MMIF_VERSION,
    license='Apache 2.0',
)

METADATA.add_input(DocumentTypes.TextDocument)
METADATA.add_input(AnnotationTypes.TimeFrame)
METADATA.add_input(AnnotationTypes.BoundingBox)
METADATA.add_input(AnnotationTypes.Alignment)
METADATA.add_output(Uri.TOKEN)
