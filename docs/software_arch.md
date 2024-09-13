# Software Architecture

This document provides an overview of the Maya submitter plug-in and adaptor that are in this repository.
The intent is to help you have a basic understanding of what the applications are doing to give you context
to understand what you are looking at when diving through the code. This is not a comprehensive deep dive of
the implementation.

## Maya Submitter Plug-in

The Maya plug-in is contructed in two parts:
1. A very bare-bones plug-in [module](https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=Maya_SDK_Distributing_Maya_Plug_ins_DistributingUsingModules_html)
   in the `/maya_submitter_plugin` directory. 
2. The `deadline.maya_submitter` Python package located in `/src/deadline/maya_submitter` that provides all of the actual business logic for the plugin.

### Plug-in Module

The plug-in module is mainly two files:

1. `DeadlineCloudForMaya.mod` -- The [module description file](https://help.autodesk.com/view/MAYAUL/2024/ENU/?guid=Maya_SDK_Distributing_Maya_Plug_ins_DistributingUsingModules_ModuleDescriptionFiles_html)
   for the plug-in.
2. `plug-ins/DeadlineCloudForMaya.py` -- The implementation of Maya's plug-in interface for the plugin. There is not much to this code.
   It is just building the shelf in Maya for AWSDeadline, and creating the button(s) in that shelf for the users to click to launch the submitter.
   Clicking the submitter button calls a function in the `deadline.maya_submitter` package to create the UI, and do all of the submitter functionality.

### `deadline.maya_submitter`

This Python module implements all of the functionality of the Maya plug-in itself. The entrypoints that Maya integrates with
are all defined in `deadline.maya_submitter.mel_commands`. These simply create a UI window to display to the user.

Fundamentally, what this submitter is doing is creating a [Job Bundle](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html)
and using the GUI creation code in the [`deadline` Python package](https://pypi.org/project/deadline/) to generate the UI
that is displayed to the user. The important parts to know about in a job bundle are:

1. The job template file. The submitter code dynamically generates the template based on properties of the specific scene file
   that is loaded. For example, it may contain a Step for each layer of the scene to render.
   Note: All job template files are currently derived from a standard static job template located at
   `src/deadline/maya_submitter/default_maya_job_template.yaml`.
2. Asset references. These are the files that the job, when submitted, will require to be able to run. The submitter contains code
   that introspects the loaded scene to automatically discover these. The submitter plug-in's UI allows the end-user to modify this
   list of files.

The job submission itself is handled by functionality within the `deadline` package that is hooked up when the UI is created.

## Maya Adaptor Application

See the [README](../README.md#maya-adaptor) for background on what purpose the adaptor application serves.

The implementation of the adaptor for Maya has two parts:

1. The adaptor application itself whose code is located in `src/deadline/maya_adaptor/MayaAdaptor`. This is the
   implementation of the command-line application (named `maya-openjd`) that is run by Jobs created by the Maya submitter.
2. A "MayaClient" application located in `src/deadline/maya_adaptor/MayaClient`. This is an application that is
   run within Maya by the adaptor application when it launches Maya. The MayaClient remains running as long as the Maya
   process is running. It facilitates communication between the adaptor process and the running Maya process; communication
   to tell Maya to, say, load a scene file, or render frame 20 of the loaded scene.

The adaptor application is built using the [Open Job Description Adaptor Runtime](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python)
package. This package supplies the application entrypoint that defines and parses the command-line subcommands and options, as well as
the business logic that drives the state machine of the adaptor itself. Please see the README for the runtime package for information on
the lifecycle states of an adaptor, and the command line options that are available. 

Digging through the code for the adaptor, you will find that the `MayaAdaptor.on_start()` method is where the Maya application is started.
The application is started with arguments that tell Maya to run the "MayaClient" application. This application is, essentially, a secure web
server that is running over named pipes rather than network sockets. The adaptor sends the client commands (look for calls to `enqueue_action()`
in the adaptor) to instruct Maya to do things, and then waits for the results of those actions to take effect. 

You can see the definitions of the available commands, and the actions that they take by inspecting `src/deadline/MayaClient/maya_client.py`. You'll
notice that the commands that it directly defines are minimal, and that the set of commands that are available is updated when the adaptor sends
it a command to set the renderer being used. Each renderer has its own command handler defined under `src/deadline/MayaClient/render_handlers`.

The final thing to be aware of is that the adaptor defines a number of stdout/stderr handlers. These are registered when launching the Maya process
via the `LoggingSubprocess` class. Each handler defines a regex that is compared against the output stream of Maya itself, and code that is run
when that regex is matched in Maya's output. This allows the adaptor to, say, translate the rendering progress status from Maya into a form
that can be understood and reported to Deadline Cloud.
