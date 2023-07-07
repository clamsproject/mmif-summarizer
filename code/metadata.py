from mmif import DocumentTypes, AnnotationTypes

from clams.appmetadata import AppMetadata
from lapps.discriminators import Uri


APP_VERSION = '0.2.0'
APP_LICENSE = 'Apache 2.0'
ANALYZER_VERSION = '0.1.0'
ANALYZER_LICENSE = 'Apache 2.0'
MMIF_VERSION = '0.4.2'
MMIF_PYTHON_VERSION = '0.4.8'
CLAMS_PYTHON_VERSION = '0.5.3'


# DO NOT CHANGE the function name
def appmetadata() -> AppMetadata:
    metadata = AppMetadata(
        name="MMIF Summarizer",
        description="Summarize a MMIF file.",
        identifier="https://apps.clams.ai/mmif-summarizer",
        url='https://github.com/clamsproject/mmif-summarizer',
        app_version=APP_VERSION,
        app_license=APP_LICENSE,
        analyzer_version=ANALYZER_VERSION,
        analyzer_license=ANALYZER_LICENSE,
    )

    metadata.add_input(DocumentTypes.TextDocument, required=False)
    metadata.add_input(AnnotationTypes.TimeFrame, required=False)
    metadata.add_input(AnnotationTypes.BoundingBox, required=False)
    metadata.add_input(AnnotationTypes.Alignment, required=False)
    metadata.add_input(Uri.TOKEN, required=False)
    metadata.add_input(Uri.NE, required=False)

    return metadata


# DO NOT CHANGE the main block
if __name__ == '__main__':
    import sys
    sys.stdout.write(appmetadata().json(indent=2))
