# Converting MMIF to PBCore

Code to convert an MMIF file to a PBCore document, only keeping those annotations that are useful metadata (and reducing the size of the file by one or two orders of magnitude).

See `run.py` for some of the limitations of the code. One thing that needs to be stressed is that the pbcoreIdentifier is simply taken from the location.



## Usage

To test the application by just running the converter on the sample input document:

```bash
$> python run.py -t
```

 The output should be something like

```xml
<?xml version="1.0" encoding="utf-8"?>
<pbcoreDescriptionDocument xmlns="http://www.pbcore.org/PBCore/PBCoreNamespace.html">
 <pbcoreAssetDate dateType="broadcast">today</pbcoreAssetDate>
 <pbcoreIdentifier source="http://americanarchiveinventory.org">17</pbcoreIdentifier>
 <pbcoreDescription descriptionType="bars-and-tone" end="2600" start="0"></pbcoreDescription>
 <pbcoreDescription descriptionType="slate" end="5300" start="2700"></pbcoreDescription>
 <pbcoreSubject end="5500" start="0" subjectType="Person">Jim Lehrer</pbcoreSubject>
 <pbcoreSubject end="5100" start="3000" subjectType="Person">Sara Just</pbcoreSubject>
 <pbcoreSubject end="21100" start="21000" subjectType="Location">New York</pbcoreSubject>
 <pbcoreSubject end="5500" start="0" subjectType="Organization">PBS</pbcoreSubject>
</pbcoreDescriptionDocument>
```

To start a Flask server:

```bash
$> python run.py
```

To ping it (do this from a different terminal than the run.py script):

```bash
$> curl -i -H -X GET http://0.0.0.0:5000/
$> curl -i -H "Accept: application/json" -X POST -d@input.mmif http://0.0.0.0:5000/
```



## Docker

Building the image (use any name of your liking for the tag):

```bash
$> docker build --tag mmif-pbcore-converter .
```

Entering the container and testing the converter:

```bash
$> docker run --rm -it mmif-pbcore-converter bash
$> python run.py -t
```

 In real life, the second prompt will be the container prompt, something like `root@f9deb9a6115f:/app#`.

To run the Flask server in a Docker container:

```bash
$> docker run --rm -d -p 5000:5000 mmif-pbcore-converter
$> curl -i -H "Accept: application/json" -X POST -d@input.mmif http://0.0.0.0:5000/
```

