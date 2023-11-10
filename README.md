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

In order to create images for right-to-left scripts, it is necessary to install more dependencies.

### Install dependencies for right-to-left scripts: MAC
The easiest way to install the dependencies is using `homwbrew`. 

```bash
brew install libraqm
```

The following dependencies are needed for `libraqm`. You might have some of them already installed:

```bash
brew install libtiff libjpeg webp little-cms2 pkg-config cmake freetype harfbuzz fribidi meson gtk-doc
```

In order to have `libraqm` available for Pillow, you need to build Pillow from source. 
If you have already installed it, you need to uninstall it and rebuild it:

```bash
pip uninstall Pillow
python3 -m pip install --upgrade Pillow --no-binary :all:
```

### Install dependencies for right-to-left scripts: Windows
Not tested so far. If you had to install it, please update the `README`.


## Create the images

Steps to create the images:

1. Go to the `image_config.py` file
2. Set the variable language on top of the file to the language you want to create the images for. Please use the
   two-character code from this list: [ISO 639-1 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
3. Create a new folder called `data/stimuli_[language]` where language is the same language code that you specified in the
   config
4. Paste the Excel files for the stimuli texts, the questions and the instruction screens into that folder.
5. Go again to the `image_config.py` file
6. Set the variables `RESOLUTION` and `SCREEN SIZE`. PLease make sure that both values reflect the size of the
   presentation monitor
   where you will present the screens to the participants.
   The screen size needs to be measured without the frame of the monitor. Only the actual screen. Note that the screen
   you use cannot be smaller than 37x28 cm.