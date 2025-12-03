"""
Test WASAPI loopback device detection specifically
"""
import pyaudiowpatch as pyaudio

audio = pyaudio.PyAudio()

print("=== Testing WASAPI Loopback Detection ===\n")

try:
    # Get WASAPI info
    wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    print(f"WASAPI Host API Index: {wasapi_info['index']}")
    print(f"Default Output Device Index: {wasapi_info['defaultOutputDevice']}")
    print(f"Default Input Device Index: {wasapi_info['defaultInputDevice']}\n")

    # Get default output device
    default_output = audio.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    print(f"Default Output Device: {default_output['name']}")
    print(f"  Is Loopback: {default_output.get('isLoopbackDevice', False)}")
    print(f"  Max Input Channels: {default_output['maxInputChannels']}")
    print(f"  Max Output Channels: {default_output['maxOutputChannels']}\n")

    # Enumerate all loopback devices
    print("All WASAPI Loopback Devices:")
    loopback_devices = []
    for loopback in audio.get_loopback_device_info_generator():
        loopback_devices.append(loopback)
        print(f"  [{loopback['index']}] {loopback['name']}")
        print(f"      Host API: {loopback['hostApi']}")
        print(f"      Max Input Channels: {loopback['maxInputChannels']}")
        print(f"      Is Loopback: {loopback.get('isLoopbackDevice', False)}")

    print(f"\nTotal loopback devices found: {len(loopback_devices)}")

    # Recommend which one to use
    print("\n=== Recommendation ===")
    if default_output.get('isLoopbackDevice'):
        print(f"✓ Use default output device (already loopback): {default_output['name']}")
    else:
        # Find matching loopback for default output
        for loopback in loopback_devices:
            if default_output['name'] in loopback['name']:
                print(f"✓ Use loopback device: {loopback['name']}")
                print(f"  (matches default output: {default_output['name']})")
                break
        else:
            print("⚠️ No loopback device found matching default output")
            if loopback_devices:
                print(f"  Fallback: Use first loopback device: {loopback_devices[0]['name']}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

audio.terminate()
