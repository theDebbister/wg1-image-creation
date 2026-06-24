# Image creation

This repository contains the code to create the images for the MultiplEYE experiment. The folder `stimuli_toy` contains
examples of all input files that are necessary and the output files that will eventually be generated. You can always
refer to these as an examples.

* [Prepare MultiplEYE stimulus files](#prepare-stimulus-files)
* [Create the images](#create-the-images)
* [What to do about typos in the final images?](#what-if-the-lab-notices-a-typo-after-the-piloting-has-started)
* [Requirements to run the scripts](#requirements)
* [Text length requirements](#text-length-requirements)
* [MultiplEYE Subcorpora](#generating-the-images-for-multipleye-subcorpora)


## Prepare stimulus files

Please follow the instructions in the MultiplEYE guidelines linked on this page to prepare the stimulus files: 
[MultiplEYE contribute](https://multipleye.eu/contribute/)

## Create the images

The readme gives a step by step explanation of what to do to create the images for the MultiplEYE experiment.
The steps below are to be performed if the images are created to be tested and checked for typos etc.

1. Please read the guidelines on the [MultiplEYE contribute](https://multipleye.eu/contribute/) page carefully before starting the image creation. 
Make sure you have all the necessary files and the data collection has been preregistered. Make sure to have the preregistration file at hand.
2. Create a new folder for the images of your lab that is called "stimuli_[dataset title]". The dataset title is specified in the preregistration file. 
For example: "stimuli_MultiplEYE_DE_CH_Zurich_1_2025".
3. Copy the Excel files for the stimuli texts, the questions and the instruction screens into that folder.
4. Create a folder called "config" in the new folder. 
5. In that config folder you create a file called "[dataset title]_lab_configuration.json".
6. Now you copy the content of the preregistration file into the lab configuration file. Make sure that all the curly braces are included
7. Go to the `image_config.py` file and set the variables `LANGUAGE`, `COUNTRY_CODE`, `CITY`, `LAB_NUMBER` and `YEAR` 
on top of the file to the language you want to create the images for (the same values as in the preregistration form).
8. If the images are created for testing purposes, set the variable `TESTING_IMAGES` to `True`. This is the case, when 
you create the images for the first time and people are checking for typos etc.
9. Run `text_to_picture.py`
10. Upload the stimuli folder to the SwitchDrive folder of the respective language.
11. Repeat the generation if necessary (i.e. if there are typos etc.). Make sure to upload a new folder each time and 
put the other one in an archive folder on the Drive.


### Creating the final images
If the images have been checked and the lab decides to start with the piloting, the images need to be created again 
one last time.

> NOTE: there is a bug currently that causes the images to be blurry (ONLY when presented within the experiment, 
> not visible here). Something that seems to help is to slightly reduce the image width, i.e. setting it to 36.5 instead of 
> 37 in the `image_config.py` file. 

1. Once the images have been checked according to the guidelines, set the variable `TESTING_IMAGES` to `False`. 
Now, more version will be created which means the process can take a lot longer!
2. If the lab uses multiple devices, please contact [multipleye@cl.uzh.ch](mailto:multipleye@cl.uzh.ch).
2. As soon as the images have been generated, upload the entire folder to the SwitchDrive folder of the respective language.

## What if the lab notices a typo after the piloting has started?
In this case, it is very important to make a copy of the stimulus folder FROM THE EXPERIMENT (not the one on drive 
nor the one here)!! Some files change during the experiment,
and we need to keep those. So:
1. Copy the entire data folder and save it on SwitchDrive in a folder that is clearly named: I.e.
`data_piloting_[dataset title]_participant_id_1_to_10`. 
2. Now, go back to the original stimuli files and make the necessary changes (i.e. correct typos) and regenerate the ALL images again. It is very important to regenerate the entire set of images again and not just single images!!!
3. Replace the stimulus folder in the experiment by the new one. Run a test session to see that it works.
4. Go to the copy of the old stimulus images and copy this file: `stimuli.../config/stimulus_order_versions ... .csv`. This is the file
that contains the information on what stimulus versions have been used for which participant.
5. Go to the newley generated stimuli that you have copied to the experiment. Search for the file with the same name and epalce the new file with the old one. There should only exist one version of this file. To check that it is correct you can check the column "participant_id" in the file. It should contain all participant numbers that you have used so far.
6. This process makes sure we store the information about which stimuli versions have been used already by which participant in the new stimuli images.

## Requirements

In order to run the scripts you need to install the necessary Python packages. It is best if you set up a
clean Python environment to do so. If you use an IDE you can create the environment there. For example for
PyCharm you can follow these [instructions](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html).

Once you have the environment you can install the necessary packages using the `requirements.txt` file.

In order to create images for right-to-left scripts, it is necessary to install more dependencies.


## Text length requirements

### Length of stimulus texts
For the default setting of `IMAGE_SIZE_CM = (37, 28)` the following applies:

The maximum number of character per line is 82. And the maximum number of lines per page is around 9, 
but it depends on the exact monitor size and resolution. This means that the last
line will be above the fixation dot in the corner of the screen. **This needs to be checked for each page**
However, as we do not split the words, if a word, for example, makes the line 85 characters long, 
this entire word will be moved to the next line. So the maximum number of chars per page is in theory around 738 (for 9 lines), 
but in reality this is rarely the case as the words usually don’t perfectly fit on the lines. 
So, if you like to count by hand how the pages fit, you can just determine the first word that exceeds the line 
limit (>82 chars) and this word will then be the first word of the new line.

The maximum number of characters can be specified in the `image_config.py` file using the variable MAX_CHARS_PER_LINE.
Changing this might cause the text to overflow the page!!

> NOTE: this is different for the participant instructions screens, where more characters per line and lines are allowed.
> It has not been a problem so far for any language that it would not fit. If it does not fit, one of the instructions screens
> can simply be split into two screens in the Excel file.

### Length of question-answer-options
The answer options to the questions have a maximum length as well. There are two types of boxes that each answer option can appear in.
This means we have to test for each option whether it fits in both boxes (and especially whether it fits in the smaller one).
As per default, 10 versions of the images with shuffled answer options will be created, all options should appear in each box type at least
once across all versions. If an option does not fit, the script will show a warning message but continue. In addition, as people also check
every screen manually, it will be noticed if an option does not fit.

## Generating the images for MultiplEYE Subcorpora

It is possible to generate images for Corpora using a subset of the MultiplEYE stimuli or changing the stimuli (e.g., shortening them).
In this case, the data collectors need to define a name for the corpus. This name can then be specified in the `image_config.py` file
using the argument `SUBCORPUS`. Please note that the stimuli files need to contain this name in the correct position.
Very importantly, it needs to be defined which stimuli IDs should be used of the original IDs in order to generate the correct randomization file. 
If it is a subset only. E.g., for the `aging` corpus this has been defined here: `src/subcorpus/aging.py`.

In order to set up the generation for a new subcorpus, please contact [multipleye.project@gmail.com](mailto:multipleye.project@gmail.com).

