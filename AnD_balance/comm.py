import serial.tools.list_ports

def scan_serial_ports(usb=True):
    ports = serial.tools.list_ports.comports()
    devices = []
    for port in ports:
        if usb and 'ttyUSB' not in port[0]:
            continue
        devices.append({
            "device": port.device,
            "name": port.name,
            "description": port.description,
            "manufacturer": port.manufacturer,
            "hwid": port.hwid,
            "vid": port.vid,
            "pid": port.pid,
            "serial_number": port.serial_number,
            "location": port.location,
            "product": port.product,
            "interface": port.interface,
        })
    return devices
