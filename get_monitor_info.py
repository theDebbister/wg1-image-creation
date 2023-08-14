# if we want to check the screen information we can use this
from screeninfo import get_monitors

for m in get_monitors():
    print(str(m))