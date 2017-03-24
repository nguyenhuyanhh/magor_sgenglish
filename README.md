# magor_sgenglish

This is in development.

The final system takes in audio/ video files as input, then performs a number of processing tasks in a pipeline - sampling, diarization, transcription using Google Speech APIs/ in-house LVCSR system, keyframe captioning, etc.

The repository includes the core system, as well as a collection of reference modules for the above-mentioned tasks.

## System pre-requisites

This is the requisites for the core system only. For module-specific requirements, consult the [Modules](#modules) section below.

1. Linux
1. Python (either 2 or 3)

The system was developed using Python 2.7.12 on Lubuntu 16.04.1.

## Setup

1. Clone this project
1. Install python dependencies: `$ sudo pip install -r requirements.txt`
1. Setup the module dependencies as prescribed in [Modules](#modules)
1. Crawl (put) files into `/crawl`
1. Run the system: `$ python system.py` or `$ python system.py -p [list of procedures separated by space]` (see `$ python system.py --help`)

## Documentation

### Overall file structure

Non-critical files are omitted for brevity.

```
crawl/                  # raw files (from crawler or manual input)
data/                   # main data 
modules/                # modules
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

### Modules

WIP.

### Data folder structure

The `/data` folder structure allows independent module outputs to be stored in their respective folders. Each file is identifiable by `file_id`, a slug of the original file name.

```
data/
    file-id-1/
        raw/            # output of module raw: raw file (.mp3, .mp4, .wav)
        resample/       # output of module resample: resampled file (.wav)
        diarization/    # output of module diarize: diarization file (.seg)
        transcript/
            google/     # output of module google: Google transcript (.txt, .TextGrid)
            lvcsr/      # output of module lvcsr: LVCSR transcript (.stm, .ctm, .csv, .TextGrid)
        temp/           # temp files for each module
            google/
            lvcsr/
    file-id-2/
        ...
    ...
```

### Manifest file structure

An example would be the included `manifest.json`.

```json
{
    "modules":{
        "module-id-1":{
            "name":"",
            "version":"",
            "requires":[],
            "inputs":[],
            "outputs":[]
        },
        "module-id-2":{}
    },
    "procedures":{
        "procedure-id-1":[
            "raw*",
            "resample*",
            "diarize*",
            "google*"
        ],
        "procedure-id-2":[]
    }
}
```

Field types and value constraints:

| Field | Type | Constraint
| --- | --- | --- 
| `module-id` | `str` | Must be the name of a subfolder under `/modules`
| -- `name` | `str` | 
| -- `version` | `str` |
| -- `requires` | `list(str)` | Module dependencies (required paths under `/modules/module-id`)
| -- `inputs` | `list(str)` | Module inputs (subfolders under `/data/file-id`)
| -- `outputs` | `list(str)` | Module outputs (subfolders under `/data/file-id`)
| `procedure-id` | `str` | 
| -- procedures | `list(str)` | List of modules in the procedure

The method `manifest_check()` called at system start-up would check the manifest for consistency with the actual system, and disable violating modules/ procedures.
