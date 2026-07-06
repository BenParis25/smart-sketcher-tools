import asyncio
import sys

try:
    import asyncclick as click
    _HAS_ASYNCCLICK = True
except ModuleNotFoundError:
    _HAS_ASYNCCLICK = False

    class _FallbackCommandGroup:
        def __init__(self, function):
            self.function = function
            self.commands = {}

        def command(self, *args, **kwargs):
            def decorator(command_function):
                self.commands[command_function.__name__] = command_function
                return command_function

            return decorator

        def __call__(self, *args, **kwargs):
            if len(sys.argv) < 2:
                raise SystemExit("asyncclick is not installed. Run 'python3 sketcher.py selftest' or install dependencies for sendimage/scan.")

            command_name = sys.argv[1]
            command = self.commands.get(command_name)
            if command is None:
                raise SystemExit(f"Unknown command: {command_name}")

            if asyncio.iscoroutinefunction(command):
                return asyncio.run(command())
            return command()

    class _FallbackClick:
        def group(self, *args, **kwargs):
            def decorator(function):
                return _FallbackCommandGroup(function)

            return decorator

        def option(self, *args, **kwargs):
            def decorator(function):
                return function

            return decorator

        def argument(self, *args, **kwargs):
            def decorator(function):
                return function

            return decorator

        def pass_context(self, function):
            return function

        def Path(self, *args, **kwargs):
            return str

    click = _FallbackClick()
from rgb565_utils import rgb_to_rgb565_bytes

ble_char_uuid = "0000ffe3-0000-1000-8000-00805f9b34fb"

# delay between sending each line in the image. The device does send an OK notification when it's ready to receive a new line,
# but i can see that these are sometimes bundled together as one "OKOK" message and it just seems a bit unreliable. 
# Setting a fixed delay seemed to work better. If things seems unstable, try increaseing this a tiny bit.
delay_between_image_lines = 0.05 

def ble_notify_callback(sender: int, data: bytearray):
    '''Callback when receiving notifications from BLE device'''
    global state
    # print(f"Received: {data}")
    state = 1


@click.group()
@click.option('--adr', help='BT address of device e.g. 11:22:33:44:55:66')
@click.pass_context
async def cli(ctx,adr):
    '''example usage: sketcher.py --adr 11:22:33:44:55:66 sendimage'''
    ctx.ensure_object(dict)

    ctx.obj['adr'] = adr
    pass


@cli.command()
async def selftest():
    """Run a small RGB565 packing check without any Bluetooth hardware."""
    cases = {
        "black": ((0, 0, 0), (0x00, 0x00)),
        "red": ((255, 0, 0), (0x00, 0xF8)),
        "green": ((0, 255, 0), (0xE0, 0x07)),
        "blue": ((0, 0, 255), (0x1F, 0x00)),
        "white": ((255, 255, 255), (0xFF, 0xFF)),
    }

    failures = []
    for name, (rgb, expected) in cases.items():
        result = rgb_to_rgb565_bytes(*rgb)
        if result != expected:
            failures.append(f"{name}: expected {expected}, got {result}")

    if failures:
        print("RGB565 self-test failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("RGB565 self-test passed")


@cli.command()
async def scan():
    """Scan for nearby BLE devices and print the Smart Sketcher address if found."""
    try:
        from bleak import BleakScanner
    except ModuleNotFoundError:
        raise SystemExit("scan requires the 'bleak' package. Install dependencies with 'pip3 install -r requirements.txt'.")

    devices = await BleakScanner.discover()
    if not devices:
        print("No BLE devices found.")
        return

    sketcher_found = False
    for device in devices:
        print(f"{device.address}  {device.name or 'unknown'}")
        if device.name == "smART_sketcher2.0":
            sketcher_found = True

    if sketcher_found:
        print("\nFound smART_sketcher2.0 above.")
    else:
        print("\nsmART_sketcher2.0 was not seen in this scan.")

@cli.command()
@click.pass_context
@click.argument('filename',type=click.Path(exists=True))
async def sendimage(ctx,filename):
    from bleak import BleakClient, BleakScanner
    from PIL import Image
    from progress.bar import Bar

    adr = ctx.obj['adr']
    image = Image.open(filename)
    # print(image.mode) # Output: RGB
    # print(f"Image size = {image.size}") # Output: (1920, 1280)

    if(image.size[0] != 160 or image.size[1] != 128):
        print("Image size is not 160x128, performing resizing.... (aspect ratio might be wrong)")
        image = image.resize(size=(160,128))

    image = image.convert('RGB')

    if adr is None:
        print("BT Address not given. Scanning for device instead...")

        devices = await BleakScanner.discover()
        detected_adr = None
        for d in devices:
            if d.name == "smART_sketcher2.0":
                detected_adr = d.address
                print(f'Found smART Sketchet 2.0 device with address {detected_adr}')
                break

        if detected_adr is None:
            print("Could not find a device nearby.")
            exit(0)

        adr = detected_adr

    print(f"Connecting to device with address {adr}")

    async with BleakClient(adr) as client:
        
        # for service in client.services:
        #     print(service)

        await client.start_notify(ble_char_uuid, ble_notify_callback)

        # "Send Image" command 
        data = bytes([0x01,0x00,0x00,0x00,0x50,0x00,0x01,0x00])
        await client.write_gatt_char(char_specifier=ble_char_uuid,data=data)
        send_lines = 0
        x = 0
        y = 0
        bar = Bar('Sending image data', max=128,suffix="%(index)d / %(max)d Lines")
        while send_lines < 128:
            line_data = bytearray()
            for x in range(0,160):
                r,g,b = image.getpixel((x,y))

                byte1, byte2 = rgb_to_rgb565_bytes(r, g, b)
                line_data.append(byte1)
                line_data.append(byte2)

            await asyncio.sleep(delay_between_image_lines) 
            # Send actual image data
            await client.write_gatt_char(char_specifier=ble_char_uuid,data=line_data)
            bar.next()
            send_lines+=1
            y += 1

        print("\r\nDone")

if __name__ == '__main__':
    if _HAS_ASYNCCLICK:
        cli()
    else:
        cli()