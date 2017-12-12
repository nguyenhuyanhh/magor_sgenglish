# magor_sgenglish

This is in development.

The final system takes in audio/ video files (both single files and multi-channel recordings) as input, then performs a number of processing tasks in a pipeline - sampling, diarization, transcription using Google Speech APIs/ in-house LVCSR system, keyframe captioning, visualization etc.

The repository includes the core system, as well as a collection of reference modules for the above-mentioned tasks.

## System pre-requisites

This is the requisites for the core system only. For module-specific requirements, consult the [Modules](#modules-and-procedures) section below.

1. Linux
1. Python 2

The system was developed using Python 2.7.12 on Lubuntu 16.04.2 LTS.

## Setup

1. Clone this project: `$ git clone https://github.com/nguyenhuyanhh/magor_sgenglish.git --recursive`
1. Setup the individual module dependencies **automatically** (`$ python system.py setup --all`) or **manually** (as prescribed in [Modules](#modules-and-procedures))
1. Crawl (put) files into `/crawl`
1. Run the system: `$ python system.py process [options]` (for a list of options, see `$ python system.py process -h` or consult [Command-line interface](#command-line-interface) section below).

## Documentation

### Command-line interface

```
$ python system.py setup -h
usage: system.py setup [-h] [-m [module_id [module_id ...]]] [-a]

optional arguments:
  -h, --help            show this help message and exit
  -m [module_id [module_id ...]], --modules [module_id [module_id ...]]
                        module_ids to setup
  -a, --all             setup all available modules
```

```
$ python system.py process -h
usage: system.py process [-h] [-p [procedure_id [procedure_id ...]]]
                         [-f [file_name [file_name ...]]]
                         [-i [file_id [file_id ...]]] [-t] [-n]
                         [process_id]

positional arguments:
  process_id            process_id for this run

optional arguments:
  -h, --help            show this help message and exit
  -p [procedure_id [procedure_id ...]], --procedures [procedure_id [procedure_id ...]]
                        procedures to run
  -f [file_name [file_name ...]], --files [file_name [file_name ...]]
                        file_names to process
  -i [file_id [file_id ...]], --ids [file_id [file_id ...]]
                        file_ids to process
  -t, --test            just do system checks and exit
  -n, --simulate        simulate the run, without processing any file
```

### Overall repository structure

Non-critical files are omitted for brevity.

```
crawl/                  # raw files (from crawler or manual input)
data/                   # main data 
modules/                # modules
utils/                  # utility scripts
manifest.json           # system manifest
system.py               # core system executable
```

### Manifest file structure

An example would be the included `manifest.json`.

```json
{
    "processes": {
        "process-1": {
            "resample": "1.0",
            "diarize": "8.4.1",
            "google": "1",
            "lvcsr": "1701",
            "convert": "1.0",
            "capgen": "1.0",
            "visualize": "1.0",
            "vad": "1.0"
        },
        "process-2": {
            "resample": "0.9"
        }
    },
    "default_process": "process-1",
    "procedures":{
        "procedure-id-1":[
            "resample",
            "diarize",
            "google"
        ],
        "procedure-id-2":[]
    },
    "file_types":{
        "audio":[
            ".mp3",
            ".wav"
        ],
        "video":[
            ".mp4"
        ]
    }
}
```

All fields in the manifest file are of type `str`.

The manifest is initiated as an instance of the class `Manifest`, and manifest integrity checks would be executed before processing any file.

### Modules, procedures and processes

Each module in the system performs a function, which takes input files from certain subfolders under the working folder (`data/process-id/file-id`) and produce output files in other subfolders under the same working folder. Modules could be pipelined into procedures, if their input and output requirements are linked.

Processes are a certain configuration of procedures, each procedure having modules locked to a certain version (overwriting the default version, specified by the default process). The same procedure when applied to different processes might have different versions; this enables versioning of module outputs.

#### Module file structure

The `module-id` (module folder name) must be a composition of the module name and its version (in the form `{name}-{version}`).

```
modules/
    module-id-1/
        manifest.json       # module manifest
        setup               # setup script (`#!/bin/bash` is recommended)
        module.py           # core module executable
        [optional executables and data files]
    module-id-2/
        ...
    ...
```

#### Module manifest file structure

This is an example manifest file for module `resample-1.0`.

```json
{
    "name": "resample",
    "version": "1.0",
    "requires": [],
    "inputs": [
        "raw"
    ],
    "outputs": [
        "resample"
    ]
}
```

Field types and value constraints:

| Field | Type | Constraint
| --- | --- | --- 
| `name` | `str` | 
| `version` | `str` |
| `requires` | `list(str)` | Module dependencies (required paths under `/modules/module-id`)
| `inputs` | `list(str)` | Module inputs (subfolders under `/data/process-id/file-id`)
| `outputs` | `list(str)` | Module outputs (subfolders under `/data/process-id/file-id`)

#### Included modules and procedures

The modules included within this repository are:

| Module | Version | `module-id` | Author/ Contributor | System Requirements/ Setup | Python requirements
| --- | --- | --- | --- | --- | ---
| `resample` | 1.0 | `resample-1.0` | Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg` | `FFmpy`
| `convert` | 1.0 | `convert-1.0` | Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg` | `FFmpy`
| `vad` | 1.0 | `vad-1.0` | Pham Van Tung/ Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg` | `scipy`, `numpy`, `soundfile`, `FFmpy`
| `diarize` | 8.4.1 | `diarize-8.4.1` | Nguyen Huy Anh | Java 7 (at least) installed. Recommended to install [JDK 7/8](http://www.webupd8.org/2012/09/install-oracle-java-8-in-ubuntu-via-ppa.html) | None
| `google` | 1 | `google-1` | Nguyen Huy Anh | A valid Google Service Account Key as `google*/key.json`. [How to acquire key](https://support.google.com/googleapi/answer/6158849) | `google-cloud-speech`
| `lvcsr` | 1701 | `lvcsr-1701` | Xu Haihua/ Nguyen Huy Anh | <ol><li>Install [Kaldi](https://github.com/kaldi-asr/kaldi) with `sequitur` (included in `/tools` after successful installation)</li><li>Include `$KALDI_ROOT` as an environment variable in `~/.bashrc`</li><li>Acquire the models and put into `/lvcsr*/systems` (The Singapore-English LVCSR models by Xu Haihua is the property of [Speech and Language Research Group, School of Computer Science and Engineering, NTU](http://www.ntu.edu.sg/home/aseschng/#pf2), and is **not avalable outside NTU.**)</li></ol> | None
| `capgen` | 1.0 | `capgen-1.0` | Peter/ Nguyen Huy Anh | Follow the instructions [here](https://github.com/karpathy/neuraltalk2). Also, put the cpu checkpoints in `capgen*/neuraltalk2/model/` | None
| `visualize` | 1.0 | `visualize-1.0` | Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg` | `FFmpy`

Most of the setup procedures are automated into `setup` scripts.

Five procedures are included with this repository:

| Procedure | Description
| --- | ---
| `google` | Transcribe audios using Google Cloud Speech API
| `lvcsr` | Transcribe audios using in-house LVCSR system
| `capgen` | Generate caption for video keyframes in videos
| `vad` | Transcribe multi-channel recordings
| `visualize` | Visualize transcriptions and captions

### Data folder structure

The `/data` folder structure allows independent module inputs/ outputs to be stored in their respective folders. Each record is identifiable by `process_id`, the process used, and `file_id`, a slug of the original file name.

```
data/
    process-id-1/
        file-id-1/
            raw/            # raw file (.m4a, .mp3, .mp4, .wav)
            resample/       # output of module resample
            convert/        # output of module convert
            vad/            # output of module vad
            diarization/    # output of module diarize
            transcript/
                google/     # output of module google
                lvcsr/      # output of module lvcsr
            keyframes/      # output of module capgen
            visualize/      # output of module visualize
            temp/           # temp files for each module
                google/
                lvcsr/
                vad/
        file-id-2/
            ...
        ...
    process-id-2/
        ...
    ...
```
