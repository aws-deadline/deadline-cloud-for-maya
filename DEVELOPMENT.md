# Amazon Deadline Cloud for Maya Development

**You will need to have your runtimes set up via `asdf` or `pyenv` to match your build platform to
use `./build.sh` similarly to your build platform**

## Building

The build logic runs in `build.sh` which is relatively short
and straightforward enough that we recommend you read it directly to update/modify your build process.

## Adding Dependencies

All of the testing and development dependencies are in the `setup.cfg` and are meant to be included idiomatically.

## Testing

`./build.sh` will build and run `pytest`.

# Windows Development Workflow

WARNING: This workflow installs additional Python packages into your Maya's python distribution.

1. Create a development location within which to do your git checkouts. For example `~/deadline-clients`.
   Clone packages from this directory with commands like
   `git clone git@github.com:casillas2/deadline-maya.git`. You'll also want the `deadline` repo.
2. Switch to your Maya directory, like `cd "C:\Program Files\Autodesk\Maya2023"`.
3. Run `.\mayapy -m pip install -e C:\Users\<username>\deadline-clients\deadline` to install the Amazon Deadline Cloud Client
   Library in edit mode.
4. Run `.\mayapy -m pip install -e C:\Users\<username>\deadline-clients\deadline-nuke` to install the Nuke Submtiter
   in edit mode.
6. Edit (create if missing) your `~/Documents/maya/2023/Maya.env` file, and add the line
   `MAYA_MODULE_PATH=C:\Users\<username>\deadline-clients\deadline-maya\src\deadline_submitter_for_maya`
7. Run Maya. Go to Windows > Settings/Preferences > Plug-In Manager and you will find that
   `DeadlineSubmitter.py` is available as a plugin. Check the checkbox to have Maya load
   the plugin and create the Deadline tray for you. Click the icon on the tray to open the submitter.
