"""
Quick test to see if pyaudiowpatch can detect loopback devices
"""
import pyaudiowpatch as pyaudio

audio = pyaudio.PyAudio()

print("=== WASAPI Loopback Devices ===\n")
try:
    wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
    print(f"WASAPI Default Output Device: {wasapi_info['defaultOutputDevice']}")
    print(f"WASAPI Default Input Device: {wasapi_info['defaultInputDevice']}\n")

    print("Available loopback devices:")
    found_any = False
    for loopback in audio.get_loopback_device_info_generator():
        found_any = True
        print(f"  - {loopback['name']}")
        print(f"    Index: {loopback['index']}")
        print(f"    Channels: {loopback['maxInputChannels']}")
        print()

    if not found_any:
        print("  ❌ No loopback devices found!")
        print("  💡 This means pyaudiowpatch cannot capture system audio")
except Exception as e:
    print(f"❌ Error: {e}")

audio.terminate()
