# gramloadr
___
A simple Instagram® downloader designed for archivists, written in Python 3 programmed by jltbb and Donaldduck8.

___
As of 2022, this project is officially deprecated and will no longer be getting updates. This project is intended for educational and archival purposes only. Using this program may put your account in jeopardy and thus we are not liable for any account damages. 

___
## Setup
Clone this repository, install dependencies with `pip install -r requirements.txt` and login with `gramloadr.py --username Username --password Password`. A default configuration file will automatically be created. Edit the configuration to your liking, then run `gramloadr.py`. Gramloadr will download everything it can by default, but you can optionally specify which modules you would like to run like so: `gramloadr.py -l -s`.

___
## Configuration
Gramloadr consists of 4 modules: Highlights/IGTV, Livestreams, Pages and Stories. You can customize each modules's print color, cooldown period and account selection by editing the configuration stored in `config.json`. By default, Gramloadr will download every user you follow, but this can be limited to whichever subset is specified in the configuration. You can also customize the directory in which to store all downloaded files. Please note that the contents of `config.json` must be valid JSON.
