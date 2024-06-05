from glob import glob
import serial

class PicoTemp:
    TERMINATOR = '\r'.encode('UTF8')

    def __init__(self, port=None, timeout=1):
        ports = glob('/dev/ttyA*')
        
        if port is None:
            if len(ports) == 0:
                raise ValueError('No serial ports found')
            if len(ports) == 1:
                port = ports[0]
            else:
                raise ValueError(f'Multiple serial ports found - please specify one of {ports}')
        
        self.port = port
        
        self.pico = serial.Serial(port, 115200, timeout=timeout)

    def read(self):
        line = 'read()\r\f'
        self.pico.write(line.encode('utf-8'))
        reply = self.receive()
        reply = reply.replace('>>> ','') # lines after first will be prefixed by a propmt
        
        if reply != 'read()':
            raise ValueError('expected read() got %s' % reply)
        
        temp = self.receive()
        return float(temp)

    def receive(self) -> str:
        line = self.pico.read_until(self.TERMINATOR)
        return line.decode('UTF8').strip()

    def close(self):
        self.pico.close()