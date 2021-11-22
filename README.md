# Nest Thermostat Menubar App

This is a basic menubar app that allows you to control your Nest thermostats.

To use this app, you first need to create a Nest developer account and set up authentication between this app and the Nest web site. Follow the [instructions in the Python-nest README](https://github.com/jkoelker/python-nest/blob/master/README.rst).

After launch, you can change the mode and temperature setting of each Nest thermostat:

![](screenshot-menu.png)

If you select the mode from the menu, you will be prompted to select the mode for the corresponding thermostat:

![](screenshot-mode.png)

## Requirements

* Python == 3.7
* [python-nest](https://github.com/jkoelker/python-nest) >= 4.1.0
* [rumps](https://github.com/jaredks/rumps) >= 0.3.0
* [py2app](https://py2app.readthedocs.io) >= 0.19

## Installation

    python3 -m venv venv
    source venv/bin/activate
    pip install wheel
    pip install --isolated -r requirements.txt
    python3 setup.py py2app
    cp -r dist/NestMenubar.app /Applications/

## Acknowledgements

The thermostat icon is from [the Noun Project](https://thenounproject.com/term/thermostat/379763/).
