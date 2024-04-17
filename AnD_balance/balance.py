import serial

from .comm import scan_serial_ports

commands = {
    'get_id': '?ID',
    'get_serial_number': '?SN',
    'get_model_name': '?TN',
    'get_weight': 'S',  # returns weight when stabilised
    'get_immediate_weight': 'SI',  # returns weight immediately
    'get_continuous_weight': 'SIR',  # stream weight continuously
    'get_tare': '?PT',
    'set_tare': 'PT',
    'tare': 'T',
    'on': 'ON',
    'off': 'OFF',
}

condition_codes  = {
    'ST': 'Stable',
    'US': 'Unstable',
    'OL': 'Overload',
    'QT': 'Stable (counting)',
    'WT': 'Stable',
    'PT': 'Zero'
}

class FX_Balance:
    """
    A general class for communication with A&D FX-i/FX-iN balances.
    
    Parameters
    ----------
    port : str, optional
        The serial port to connect to. If not provided, the first USB port found will be used.
        
    Attributes
    ----------
    port : str
        The serial port the balance is connected to.
    model : str
        The model name of the balance.
    serial_number : str
        The serial number of the balance.
    id : str
        The ID of the balance.
    comm : serial.Serial
        The serial communication object.
    """
    def __init__(self, port=None):
        if port is None:
            devices = scan_serial_ports()
            if len(devices) == 1:
                port = devices[0]['device']

        self.port = port        
        self.connect()
    
        self.on()
    
    def connect(self):
        """
        Establishes a connection with the balance.

        This function initializes the communication with the balance by creating a serial connection
        with the specified port and settings. It also retrieves the model name, serial number, and ID
        of the balance.

        Parameters:
        - self: The instance of the Balance class.

        Returns:
        - None

        Raises:
        - None
        """
        self.comm = serial.Serial(self.port, 2400, bytesize=7, parity='E', stopbits=1, timeout=1)

        self.model = self.get_model_name()[-1].strip()
        self.serial_number = self.get_serial_number()[-1].strip()
        self.id = self.get_id()[-1].strip()
        
    def on(self):
        self._write(commands['on'].encode())
    
    def off(self):
        self._write(commands['off'].encode())
    
    def disconnect(self):
        self.comm.close()
    
    def _write(self, command):
        command += b'\x0D\x0A'  # add CR LF line termination

        self.comm.write(command)

        return self.comm.read_until(b'\x0D\x0A').decode().strip().split(',')
    
    def _parse_weight(self, read):
        condition_code, raw_weight = read
        weight, unit = float(raw_weight[:9].strip()), raw_weight[9:].strip()
        return weight, unit, condition_codes[condition_code]
    
    def get_weight(self, mode='stable'):
        match mode:
            case 'stable':
                return self._parse_weight(self._write(commands['get_weight'].encode()))
            case 'immediate':
                return self._parse_weight(self._write(commands['get_immediate_weight'].encode()))
            case 'continuous':
                return self._parse_weight(self._write(commands['get_continuous_weight'].encode()))
    
    def get_id(self):
        return self._write(commands['get_id'].encode())
    
    def get_serial_number(self):
        return self._write(commands['get_serial_number'].encode())
    
    def get_model_name(self):
        return self._write(commands['get_model_name'].encode())
    
    def get_tare(self):
        return self._parse_weight(self._write(commands['get_tare'].encode()))
    
    def tare(self, value=None):
        if value is None:
            return self._parse_weight(self._write(commands['tare'].encode()))
    
    def __repr__(self):
        msg = []
        
        msg.append(f'A&D {self.model} Balance')
        msg.append(f'  Serial Number: {self.serial_number}')
        msg.append(f'  ID: {self.id}')
        msg.append('---')
        weight, unit, status = self.get_weight()
        msg.append(f'Current Weight: {weight} {unit} ({status})')
        
        maxlen = max(len(x) for x in msg)
        msg.insert(0, '*' * maxlen)
        msg.append('*' * maxlen)
        
        return '\n'.join(msg)
        