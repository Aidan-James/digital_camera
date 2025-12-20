from gpiozero import Button
from time import sleep

input_pin = Button(13, pull_up=True)

def capture():
    print("capturing...")
    
class Switch():
    def __init__(self):
        self.state = 1
        self.prev_state = 1
        self.gpio = input_pin

    def update_state(self):
        self.prev_state = self.state 
        self.state = not self.gpio.is_pressed


if __name__ == '__main__':
    
    swt = Switch()
    swt.update_state()    
    
    while True:
    
        swt.update_state()

        if swt.state is not swt.prev_state:
            capture()

        sleep(0.01)

