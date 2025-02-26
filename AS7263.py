import smbus
import time
import numpy as np
import csv
import requests
from scipy.signal import savgol_filter

# AS7263 I2C Address
AS7263_ADDR = 0x49

# Register Addresses
HW_VERSION = 0x00
CTRL_SETUP = 0x04
INT_T = 0x05
LED_CTRL = 0x07
DATA_START = 0x08  # Data registers start here

# Integration time (adjustable for noise reduction)
INTEGRATION_TIME = 0xC0  # Experiment with different values (0x80, 0xFF)

# Web server URL (Replace with your actual server address)
WEB_SERVER_URL = "http://your-server-ip:5000/update"

# Initialize I2C bus
bus = smbus.SMBus(1)  # Raspberry Pi 4B uses I2C-1

# Predefined spectral data for microplastic identification (example values)
MICROPLASTIC_DATABASE = {
    "Polyethylene (PE)": [1200, 1500, 1100, 1300, 1400, 1250],
    "Polypropylene (PP)": [1000, 1400, 1150, 1250, 1350, 1200],
    "Polyvinyl Chloride (PVC)": [800, 1100, 900, 1000, 950, 850],
    "Polystyrene (PS)": [750, 950, 850, 900, 870, 800],
    "Polyethylene Terephthalate (PET)": [700, 920, 800, 850, 880, 760],
    "Acrylic (PMMA)": [680, 890, 770, 820, 800, 740]
}

def write_register(register, value):
    bus.write_byte_data(AS7263_ADDR, register, value)
    time.sleep(0.1)

def read_register(register):
    return bus.read_byte_data(AS7263_ADDR, register)

def read_sensor_data():
    # Read all 6 NIR channels
    data = []
    for i in range(6):
        high_byte = read_register(DATA_START + (i * 2) + 1)
        low_byte = read_register(DATA_START + (i * 2))
        value = (high_byte << 8) | low_byte
        data.append(value)
    
    # Apply Savitzky-Golay smoothing filter
    smoothed_data = savgol_filter(data, window_length=5, polyorder=2)
    
    # Normalize the readings
    normalized_data = (smoothed_data - np.min(smoothed_data)) / (np.max(smoothed_data) - np.min(smoothed_data))
    
    return normalized_data.tolist()

def identify_microplastic(readings):
    min_distance = float('inf')
    identified_plastic = "Unknown"
    
    for plastic, reference in MICROPLASTIC_DATABASE.items():
        distance = np.linalg.norm(np.array(readings) - np.array(reference))
        if distance < min_distance:
            min_distance = distance
            identified_plastic = plastic
    
    return identified_plastic

def estimate_concentration(readings):
    return round(np.mean(readings) * 10, 2)  # Improved scaling factor for concentration estimation

def log_data(readings, microplastic_type):
    """Logs spectral readings into a CSV file."""
    with open("microplastic_data.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(readings + [microplastic_type])
    print("Data logged successfully.")

def send_data_to_server(microplastic, concentration):
    """Sends detected data to a web server."""
    payload = {"microplastic": microplastic, "concentration": concentration}
    try:
        response = requests.post(WEB_SERVER_URL, json=payload)
        if response.status_code == 200:
            print("Data successfully sent to server.")
        else:
            print(f"Server error: {response.status_code}")
    except Exception as e:
        print(f"Failed to send data: {e}")

def setup_sensor():
    # Reset sensor
    write_register(CTRL_SETUP, 0x80)
    time.sleep(1)
    
    # Set integration time
    write_register(INT_T, INTEGRATION_TIME)
    
    # Set measurement mode (continuous reading)
    write_register(CTRL_SETUP, 0x03)

def main():
    setup_sensor()
    data_logging = input("Enable data logging? (yes/no): ").strip().lower() == "yes"
    
    while True:
        readings = read_sensor_data()
        microplastic_type = identify_microplastic(readings)
        concentration = estimate_concentration(readings)
        
        print(f"Detected: {microplastic_type}, Concentration: {concentration} mg/L")
        
        # Send results to web server
        send_data_to_server(microplastic_type, concentration)
        
        if data_logging:
            label = input("Enter microplastic type (or press Enter to skip): ").strip()
            if label:
                log_data(readings, label)
        
        time.sleep(2)  # Read every 2 seconds

if __name__ == "__main__":
    main()
