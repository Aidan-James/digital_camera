import time
import numpy as np

FB = "/dev/fb1"
WIDTH = 480
HEIGHT = 320

# RGB565 colors
BLACK = np.zeros((HEIGHT, WIDTH), dtype=np.uint16)
WHITE = np.full((HEIGHT, WIDTH), 0xFFFF, dtype=np.uint16)

with open(FB, "wb") as f:
    while True:
        f.write(BLACK.tobytes())
        f.flush()
        time.sleep(1)

        f.write(WHITE.tobytes())
        f.flush()
        time.sleep(1)
