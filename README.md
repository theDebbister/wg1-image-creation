# Image creation

This repository contains the code to create the images for the MultiplEYE experiment. The folder `stimuli_toy` contains
examples of all input files that are necessary and the output files that will eventually be generated. You can always
refer to these as an examples.

## Prepare stimulus files

TBD --> for now just copy the files in the English folder and translate all the texts and questions. The title and ID
columns need to stay the same!

## Requirements

In order to run the scripts you need to install the necessary Python packages. It is best if you set up a
clean Python environment to do so. If you use an IDE you can create the environment there. For example for
PyCharm you can follow these [instructions](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html).

Once you have the environment you can install the necessary packages using the `requirements.txt` file.

## Create the images

Steps to create the images:

1. Go to the `image_config.py` file
2. Set the variable language on top of the file to the language you want to create the images for. Please use the
   two-character code from this list: [ISO 639-1 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
3. Create a new folder called `stimuli_[language]` where language is the same language code that you specified in the
   config
4. Paste the Excel files for the stimuli texts, the practice texts and the other screens into that folder.
5. Go again to the `image_config.py` file
6. Set the variables `RESOLUTION` and `SCREEN SIZE`. PLease make sure that both values reflect the size of the
   presentation monitor
   where you will present the screens to the participants.
   The screen size needs to be measured without the frame of the monitor. Only the actual screen. Note that the screen
   you use cannot be smaller than 37x28 cm.