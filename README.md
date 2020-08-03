# gramloadr
A simple Instagram® downloader designed for archivists, written in Python 3.

___

## Setup
Clone this repository, install dependencies with `pip3 install -r requirements.txt` and login with `gramloadr.py --username Username --password Password`. Edit the configuration to your liking, then run `gramloadr.py`. Gramloadr will download everything it can by default, but you can optionally specify which modules you would like to run like so: `gramloadr.py -l -s`.

___

## Configuration
Gramloadr consists of 4 modules: Highlights/IGTV, Livestreams, Pages and Stories. You can customize each modules's print color, cooldown period and account selection by editing the configuration stored in `config.json`. You can also customize the directory in which to store all downloaded files. Please note that the contents of `config.json` must be valid JSON.
