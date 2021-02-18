from mmif.vocabulary import DocumentTypes
from mmif.vocabulary import AnnotationTypes
from lapps.discriminators import Uri


METADATA = {
    "name": "MMIF to PBCore Converter",
    "app": "https://apps.clams.ai/pbcore-converter",
    "app_version": "0.0.1",
    "tool_version": "0.0.1",
    "mmif-spec-version": "0.2.2",
    "mmif-sdk-version": "0.2.2",
    "clams-version": "0.1.8",
    "description": "Convert an MMIF file into a PBCore XML document.",
    "vendor": "Team CLAMS",
    "requires": [DocumentTypes.TextDocument.value, Uri.NE,
                 AnnotationTypes.TimeFrame.value, AnnotationTypes.BoundingBox.value,
                 AnnotationTypes.Alignment.value],
    "produces": []
}
