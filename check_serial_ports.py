import serial.tools.list_ports

# Get a list of all available ports
ports = serial.tools.list_ports.comports()

for port in ports:
    print(f"Device: {port.device}")
    print(f"Description: {port.description}")
    print(f"Hardware ID: {port.hwid}\n")
