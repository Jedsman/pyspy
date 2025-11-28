"""
Quick diagnostic to see all audio devices via sounddevice
"""
import sounddevice as sd

print("=== All Audio Devices ===\n")
devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"Index {i}:")
    print(f"  Name: {device['name']}")
    print(f"  Inputs: {device['max_input_channels']}")
    print(f"  Outputs: {device['max_output_channels']}")
    print(f"  Host API: {device['hostapi']}")
    print()

print("\n=== Host APIs ===\n")
host_apis = sd.query_hostapis()
for i, api in enumerate(host_apis):
    print(f"Index {i}: {api['name']}")
    if 'WASAPI' in api['name']:
        print(f"  Default Output: {api.get('default_output_device', 'N/A')}")
        print(f"  Default Input: {api.get('default_input_device', 'N/A')}")
    print()

print("\n=== Looking for WASAPI Loopback Devices ===\n")
wasapi_index = None
for i, api in enumerate(host_apis):
    if 'WASAPI' in api['name']:
        wasapi_index = i
        break

if wasapi_index is not None:
    print(f"WASAPI Host API Index: {wasapi_index}\n")
    for i, device in enumerate(devices):
        if device['hostapi'] == wasapi_index and device['max_input_channels'] > 0:
            print(f"WASAPI Input Device {i}: {device['name']}")
            print(f"  Channels: {device['max_input_channels']}")
else:
    print("WASAPI not found!")
