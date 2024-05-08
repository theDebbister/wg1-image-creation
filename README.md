# Image creation

This repository contains the code to create the images for the MultiplEYE experiment. The folder `stimuli_toy` contains
examples of all input files that are necessary and the output files that will eventually be generated. You can always
refer to these as an examples.

## Prepare stimulus files

TBD --> for now just copy the files in the English folder and translate all the texts and questions. The title and ID
columns need to stay the same!

For RTL texts - when there are English chunks of the texts and they are displayed in the
created images in wrong order, they order need to be changed in the xlsx file. For example:
if the ":1" is displayed in the wrong order, it need to be changed to "1:". The program has a problem when changing from RTL to LTR texts.

## Create the images

Steps to create the images:

1. Go to the `image_config.py` file
2. Set the variable `LANGUAGE` on top of the file to the language you want to create the images for. Please use the
   two-character code from this list: [ISO 639-1 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
   Set also variables `FULL_LANGUAGE`, `COUNTRY_CODE` and `LAB_NUMBER`
3. Create a new folder called `data/stimuli_[language]_[country_code]_[lab_number]` where language is the same language code that you specified in the
   config   
4. Paste the Excel files for the stimuli texts, the questions and the instruction screens into that folder. For now it works
   also without questions.
5. From `data/stimuli_toy_x_1/` copy the config folder into `data/stimuli_[language]_[country_code]_[lab_number]` - there should be three files `config_toy.py`,
   `shuffled_option_keys_toy.json` and `toy_x_1_lab_configuration.txt`
6. In the file `config_toy_x_1.py` change every occurrence of 'toy' to your language code (e.g. en for english) - inside the file
   and also in the file name
7. In the file `toy_x_1_lab_configuration.txt` change the first part of the name so it will represent your language, country code
   and lab number and inside the file change the variables 'RESOLUTION', 'SCREEN_SIZE_CM', 'DISTANCE_CM' and 'SCRIPT_DIRECTION'
   (not necessary for practice pictures)
8. Go again to the `image_config.py` file (inside the folder wg1-image-creation)
9. Set the variables `RESOLUTION` and `SCREEN SIZE`. Please make sure that both values reflect the size of the
   presentation monitor
   where you will present the screens to the participants.
   The screen size needs to be measured without the frame of the monitor. Only the actual screen. Note that the screen
   you use cannot be smaller than 37x28 cm.
10. Run `text_to_picture.py`

## Requirements

In order to run the scripts you need to install the necessary Python packages. It is best if you set up a
clean Python environment to do so. If you use an IDE you can create the environment there. For example for
PyCharm you can follow these [instructions](https://www.jetbrains.com/help/pycharm/creating-virtual-environment.html).

Once you have the environment you can install the necessary packages using the `requirements.txt` file.

In order to create images for right-to-left scripts, it is necessary to install more dependencies.


## Text length requirements

### Length of stimulus texts
For the default setting of `IMAGE_SIZE_CM = (37, 28)` the following applies:

The maximum number of character per line is 82. And the maximum number of lines per page is 9. This means that the last
line will be above the fixation dot in the corner of the screen.
However, as we do not split the words, if a word, for example, makes the line 80 characters long, 
this entire word will be moved to the next line. So the maximum number of chars per page is in theory 738, 
but in reality this is rarely the case as the words usually don’t perfectly fit on the lines. 
So, if you like to count by hand, how the pages fit, you can just determine the first word that exceeds the line 
limit (>82 chars) and this word will then be the first word of the new line, until you reach 9 lines.

The maximum number of characters can be specified in the `image_config.py` file using the variable MAX_CHARS_PER_LINE.
Changing this might cause the text to overflow the page!!

> NOTE: this is different for the participant instructions screens, where more characters per line and lines are allowed.
> The maximum number of characters per line is 85 and the maximum number of lines per page is 12.

### Length of question-answer-options
The answer options to the questions have a maximum length as well. There are two types of boxes that each answer option can appear in.
This means we have to test for each option whether it fits in both boxes (and especially whether it fits in the smaller one).
In order to test whether the answer options fit in the boxes
you need to do the following steps:
1. Set the variable `NUM_PERMUTATIONS` in the `image_config.py` file to 1
2. Go to the file `text_to_picture.py` and change the following lines (line 224 ca.):
```python
# shuffled_option_keys = ['left', 'up', 'right', 'down']
shuffled_option_keys = ['up', 'left', 'down', 'right']
# random.shuffle(shuffled_option_keys)
```
You should comment the random shuffle step so it won't shuffle the answer options but will be hardcoded for each question.
3. Run the script `text_to_picture.py`. If an option does not fit, it will show an error message. Please copy it once the script it through.
4. Now you need to go to the `text_to_picture.py` file and change the hardcoded positions of the answer options. This way, you can test all box types for all options.
```python
shuffled_option_keys = ['left', 'up', 'right', 'down']
# shuffled_option_keys = ['up', 'left', 'down', 'right']
# random.shuffle(shuffled_option_keys)
```
5. Now you need to go to the config folder in the stimulus folder of the respective language. E.g. for the toy example 
it is `data/stimuli_toy_x_1/config/` and delete the entire folder called `question_answer_option_shuffling_tox_x_1`.
You need it to make sure that the script will not use the shuffled options but the hardcoded ones.
6. Repeat step 3.
7. If all options fit, you can now set the `NUM_PERMUTATIONS` back to its original value and the random shuffle back to the original state.