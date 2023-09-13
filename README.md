# Image creation

This repository contains the code to create the images for the MultiplEYE experiment.

Steps to create the images:
1. Go to the `image_config.py` file
2. Set the variable language on top of the file to the language you want to create the images for.
3. Create a new folder called `stimuli_[language]` where language is the same language that you specified in the config
4. Paste the excel files for the stimuli texts, the practice texts and the other screens into that folder.
5. Go again to the config file
6. Set the variables RESOLUTION and SCREEN SIZE. PLease make sure that both values reflect the size of the presentation monitor.
 The screen size needs to be measured without the frame of the monitor. Only the actual screen.