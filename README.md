# TimeMQTT 
Script for using the MQTT (Message Queuing Telemetry Transport) protocol to transmit data formats used in Time and Frequency metrology. The MQTT protocol, commonly used in the context of IoT (Internet of Things), was used to experimentally transmit GNSS and environment variables data from the UTC (INXE) publisher to different subscribers.

***Note: Due to security concerns, this code do not contain the full features used in laboratory***

# Getting Started

## Install and Run Dependencies

If you have just downloaded the project and it fails due to missing modules, you may need to install its requirements first:

1. Install dependencies: python -m pip install -r requirements.txt.
2. Run the script: python TimeMQTT.py

## Important note

   The TimeMQTT app will search for the HROG-10 equipment (Symmetricon) connected via serial interface.
   The code ***emulates a plug and play feature***, by checking if the ID of the conected equipment contains the string "HROG".
   Once the "HROG" ID is found, the code identify the correspondent serial port and try to conect with the equipment.
