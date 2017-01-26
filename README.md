# magor_938_demo

This is a demo.

The final system aims to be an automated transcription system that takes in audio/ video files as input, then performs sampling, diarization and transcription using both Google Speech APIs, as well as in-house LVCSR system.

## Setup

1. Clone thís project
1. Acquire the necessary files not included in the repository (`modules/google*/key.json` and `modules/lvcsr*/systems`)
1. Crawl (put) files into `/crawl`
1. Run the system: `$ python system.py`

## System structure

Non-critical files are omitted for brevity.

```
crawl/                  # folder for raw files (from crawler or manual input)
data/                   # folder for main data 
    file_id_1/
        raw/            # raw file
        resample/       # resampled file (.wav)
        diarization/    # diarization file (.seg)
        transcript/
            google/     # Google transcript (.txt, .TextGrid)
            lvcsr/      # LVCSR transcript (.stm, .ctm, .csv, .TextGrid)
    file_id_2/
        ...
    ...
modules/                # folder for modules
    raw*/
    resample*/
    diarize*/
    google*/
        key.json        # Google Service Account JSON key (not included in repository)
    lvcsr*/
        systems/        # LVCSR system (not included in repository)
        scripts/        # scripts for LVCSR system
manifest.json           # system manifest
system.py               # system executable
```

## Manifest file structure

An example would be the included `manifest.json`.

```json
{
    "modules":{
        "module-id-1":{
            "type":"",
            "version":"",
            "requires":[]
        },
        "module-id-2":{}
    },
    "procedures":{
        "procedure-id-1":{
            "raw":"",
            "resample":"",
            "diarize":"",
            "transcribe":""
        },
        "procedure-id-2":{}
    }
}
```

Field types and value constraints:

| Field | Type | Constraint
| --- | --- | --- 
| `module-id` | `str` | Must be the name of a subfolder under `/modules`
| -- `type` | `str` | Must be one of "raw", "resample", "diarize", "transcribe"
| -- `version` | `str` |
| -- `requires` | `list(str)` | Module dependencies (required paths under `modules/module-id`)
| `procedure-id` | `str` | 
| -- `raw` | `str` | Must be a `module-id`
| -- `resample` | `str` | Must be a `module-id`
| -- `diarize` | `str` | Must be a `module-id`
| -- `transcribe` | `str` | Must be a `module-id`

The specific instance of the class `Speech()` in `speech.py` would load the manifest and check whether the procedure is valid and all its modules and their dependencies (`requires`) are met before invoking the processing pipeline.