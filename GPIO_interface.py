import Jetson.GPIO as GPIO
import time
import spidev
import os

# GPIO.setmode(GPIO.BOARD)  # Use physical pin numbers
# GPIO.setup(32, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# while True:
#     state = GPIO.input(32)
#     print(f"Pin state: {state}")
#     time.sleep(1)

class Switch():
    def __init__(self, pin, callback=None):
        self.pin = pin
        self.state = 0
        self.prev_state = None
        self.callback = callback
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def get_state(self):
        return GPIO.input(self.pin)
    
    def update(self):
        new_state = self.get_state()
        
        # Check if state changed (skip on first update when prev_state is None)
        if self.prev_state is not None and new_state != self.prev_state:
            if self.callback is not None:
                self.callback()
        
        self.prev_state = new_state
        self.state = new_state

class Joystick():
    def __init__(self, x_channel, y_channel, z_pin, spi_bus=0, spi_device=0):
        """
        Initialize joystick with MCP3008 ADC via SPI
        
        Args:
            x_channel: MCP3008 channel for X-axis (0-7)
            y_channel: MCP3008 channel for Y-axis (0-7)
            z_pin: GPIO pin for button/switch (digital)
            spi_bus: SPI bus number (default 0 for SPI0)
            spi_device: SPI device number (default 0)
        """
        self.x_channel = x_channel
        self.y_channel = y_channel
        self.z_pin = z_pin
        self.state = (0, 0, 0)
        
        # Setup GPIO for button (z_pin)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.z_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Initialize SPI for MCP3008
        # Check if SPI device exists
        spi_device_path = f"/dev/spidev{spi_bus}.{spi_device}"
        if not os.path.exists(spi_device_path):
            # Find available SPI devices
            available_spi = []
            for bus in range(10):  # Check buses 0-9
                for dev in range(2):  # Check devices 0-1
                    if os.path.exists(f"/dev/spidev{bus}.{dev}"):
                        available_spi.append(f"spidev{bus}.{dev}")
            
            available_msg = f"Available SPI devices: {', '.join(available_spi)}" if available_spi else "No SPI devices found"
            
            raise FileNotFoundError(
                f"SPI device {spi_device_path} not found.\n"
                f"{available_msg}\n"
                f"Try using one of the available SPI buses, e.g.:\n"
                f"  Joystick(0, 1, 32, spi_bus=0)  # Use SPI0\n"
                f"  or\n"
                f"  Joystick(0, 1, 32, spi_bus=2)  # Use SPI2"
            )
        
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = 1000000  # 1 MHz
        self.spi.mode = 0  # SPI Mode 0
        self.spi.bits_per_word = 8
    
    def _read_adc(self, channel):
        """
        Read analog value from MCP3008 ADC channel
        
        Args:
            channel: ADC channel number (0-7)
            
        Returns:
            Integer value from 0-1023 (10-bit ADC)
        """
        # MCP3008 command format:
        # Start bit (1) + Single/Diff (1 for single-ended) + Channel (3 bits)
        # Channel 0: 0b11000 = 0x18
        # Channel 1: 0b11001 = 0x19, etc.
        command = 0x18 | (channel & 0x07)
        
        # Send SPI transaction: command byte + 2 dummy bytes for response
        response = self.spi.xfer2([command, 0x00, 0x00])
        
        # Extract 10-bit value from response
        # Response format: [ignored, high_byte, low_byte]
        # High byte: bits 9-2, Low byte: bits 1-0 (in upper 2 bits)
        adc_value = ((response[1] & 0x03) << 8) | response[2]
        
        return adc_value
    
    def get_state(self):
        """
        Read current joystick state
        
        Returns:
            Tuple (x_value, y_value, button_state)
            - x_value: 0-1023 (analog X-axis position)
            - y_value: 0-1023 (analog Y-axis position)
            - button_state: 0 or 1 (button pressed/released)
        """
        x_value = self._read_adc(self.x_channel)
        y_value = self._read_adc(self.y_channel)
        button_state = GPIO.input(self.z_pin)
        return (x_value, y_value, button_state)
    
    def update(self):
        """Update and store current joystick state"""
        self.state = self.get_state()
    
    def cleanup(self):
        """Close SPI device and cleanup GPIO"""
        if hasattr(self, 'spi'):
            self.spi.close()
        GPIO.cleanup(self.z_pin)


if __name__ == "__main__":
    joystick = Joystick(0, 1, 33)
    trigger_switch = Switch(32)
    cam_vid_switch = Switch(31)

    while True:
        joystick.update()
        trigger_switch.update()
        cam_vid_switch.update()
        time.sleep(0.1)
        print(f"Joystick: {joystick.state}, Switch: {trigger_switch.state} , Camera/Video Switch: {cam_vid_switch.state}")