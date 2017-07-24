# magor_sgenglish

This is in development.

The final system takes in audio/ video files as input, then performs a number of processing tasks in a pipeline - sampling, diarization, transcription using Google Speech APIs/ in-house LVCSR system, keyframe captioning, etc.

The repository includes the core system, as well as a collection of reference modules for the above-mentioned tasks.

## System pre-requisites

This is the requisites for the core system only. For module-specific requirements, consult the [Modules](#modules-and-procedures) section below.

1. Linux
1. Python (either 2 or 3)

The system was developed using Python 2.7.12 on Lubuntu 16.04.1.

## Setup

1. Clone this project: `$ git clone https://github.com/nguyenhuyanhh/magor_sgenglish.git --recursive`
1. Install python dependencies: `$ sudo pip install -r requirements.txt`
1. Setup the individual module dependencies as prescribed in [Modules](#modules-and-procedures)
1. Crawl (put) files into `/crawl`
1. Run the system: `$ python system.py [options]` (for a list of options, see `$ python system.py -h` or consult [Command-line interface](#command-line-interface) section below).

## Documentation

### Command-line interface

```
$ python system.py -h
usage: system.py [-h] [-p [procedure_id [procedure_id ...]]] [-t]

optional arguments:
  -h, --help            show this help message and exit
  -p [procedure_id [procedure_id ...]], --procedures [procedure_id [procedure_id ...]]
                        procedures to pass to workflow
  -t, --test            just do system checks and exit
```

### Overall repository structure

Non-critical files are omitted for brevity.

```
crawl/                  # raw files (from crawler or manual input)
data/                   # main data 
modules/                # modules
manifest.json           # system manifest
system.py               # core system executable
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
    },
    "file_types":{
        "audio":[
            ".mp3",
            ".wav"
        ],
        "video":[]
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
| `procedure-id` | `list(str)` | List of modules in the procedure
| `audio` | `list(str)` | List of accepted audio extensions
| `video` | `list(str)` | List of accepted video extensions

The method `manifest_check()` called at system start-up would check the manifest for consistency with the actual system, and disable violating modules/ procedures.

### Modules and procedures

Each module in the system performs a function, which takes input files from certain subfolders under `data/file-id` and produce output files in other subfolders under `data/file-id`, as specified in the [manifest file](#manifest-file-structure). Modules could be pipelined into procedures, if their input and output requirements are linked.

The modules included within this repository are:

| Module | Version | `module-id` | Author/ Contributor | Requirements/ Setup
| --- | --- | --- | --- | ---
| `resample` | 1.0 | `resample-1.0` | Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg`
| `convert` | 1.0 | `convert-1.0` | Nguyen Huy Anh | `ffmpeg` installed, via `$ sudo apt-get install ffmpeg`
| `diarize` | 8.4.1 | `diarize-8.4.1` | Nguyen Huy Anh | Java 7 (at least) installed. Recommended to install [JDK 7/8](http://www.webupd8.org/2012/09/install-oracle-java-8-in-ubuntu-via-ppa.html)
| `google` | 1 | `google-1` | Nguyen Huy Anh | A valid Google Service Account Key as `google*/key.json`. [How to acquire key](https://support.google.com/googleapi/answer/6158849)
| `lvcsr` | 1701 | `lvcsr-1701` | Xu Haihua/ Nguyen Huy Anh | <ol><li>Install [Kaldi](https://github.com/kaldi-asr/kaldi) with `sequitur` (included in `/tools` after successful installation)</li><li>Include `$KALDI_ROOT` as an environment variable in `~/.bashrc`</li><li>Acquire the models and put into `/lvcsr*/systems` (The Singapore-English LVCSR models by Xu Haihua is the property of [Speech and Language Technology Program, School of Computer Science and Engineering, NTU](http://www.ntu.edu.sg/home/aseschng/SpeechTechWeb/About_Us/about_us.html))</li></ol>
| `capgen` | 1.0 | `capgen-1.0` | Peter/ Nguyen Huy Anh | Follow the instructions [here](https://github.com/karpathy/neuraltalk2). Also, put the cpu checkpoints in `capgen*/neuraltalk2/model/`

Some of the setup procedures could be quite tedious; automatic installation/ configuration scripts would be included if there is time.

Three procedures are included with this repository: `google` to transcribe audios using Google Cloud Speech API, `lvcsr` to transcribe audios using in-house LVCSR system, and `capgen` to generate caption for keyframes in videos. 

### Data folder structure

The `/data` folder structure allows independent module inputs/ outputs to be stored in their respective folders. Each file is identifiable by `file_id`, a slug of the original file name.

```
data/
    file-id-1/
        raw/            # raw file (.mp3, .mp4, .wav)
        resample/       # output of module resample: resampled file (.wav)
        convert/        # output of module convert: converted video file (.mp4)
        diarization/    # output of module diarize: diarization file (.seg)
        transcript/
            google/     # output of module google: Google transcript (.txt, .TextGrid)
            lvcsr/      # output of module lvcsr: LVCSR transcript (.stm, .ctm, .csv, .TextGrid)
        keyframes/      # output of module capgen: key frames and captions (.png, .json)
        temp/           # temp files for each module
            google/
            lvcsr/
    file-id-2/
        ...
    ...
```


