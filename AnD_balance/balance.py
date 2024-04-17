import serial

from .comm import scan_serial_ports

# a dict of valid commands for A&D FX balances
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
    'cancel': 'C',
    're-zero': 'Z',
}

# a dict of condition codes for A&D FX balances
condition_codes  = {
    'ST': 'Stable',
    'US': 'Unstable',
    'OL': 'Overload',
    'QT': 'Stable (counting)',
    'WT': 'Stable',
    'PT': 'Zero',
    'TN': 'Model Name',
    'SN': 'Serial Number',
    'ID': 'ID',
}

def encode_AnD(code, number, unit):
    """
    Encodes the given code, number, and unit into string in standard A&D format.

    Args:
        code (str): The code to be encoded.
        number (int): The number to be encoded.
        unit (str): The unit to be encoded.

    Returns:
        str: The encoded string in the format '<code>,<number><unit>'.
    """
    _code = f'{code},'
    
    if number < 0:
        _number = '-'
    else:
        _number = '+'
    _number += f'{number}'
    _number += '0' * (9 - len(_number))
    
    _unit = f'{unit}'
    _unit = ' ' * (3 - len(_unit)) + _unit
    
    return _code + _number + _unit

def decode_AnD(read):
    """
    Decode the given A&D 'read' string and extract the relevant information.

    Parameters
    ----------
    read : str
        The input string to be decoded.

    Returns
    -------
    tuple
        A tuple containing the extracted information:        
        - If 'read' is an empty string, returns (None, None, None).
        - If 'read' is not empty:
            - If the first character of 'data' is '+' or '-', returns a tuple containing:
                - The number extracted from the first 9 characters of 'data'.
                - The unit extracted from the remaining characters of 'data' after stripping leading/trailing whitespace.
                - The condition code corresponding to the 'code' parameter.
            - If the first character of 'data' is not '+' or '-', returns a tuple containing:
                - The 'data' string itself.
                - None for the unit.
                - The condition code corresponding to the 'code' parameter.
    """

    if read == '':
        return None, None, None
    code, data = read.split(',')
    if data[0] in '+-':
        number = float(data[:9])
        unit = data[9:].strip()
        return number, unit.strip(), condition_codes[code]
    else:
        return data.strip(), None, condition_codes[code]

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
        """
        self.comm = serial.Serial(self.port, 2400, bytesize=7, parity='E', stopbits=1, timeout=1)

        self.model = self.get_model_name()
        self.serial_number = self.get_serial_number()
        self.id = self.get_id()
        
    def on(self):
        """
        Turns on the balance.

        This method sends the 'on' command to the balance, which turns it on.
        """
        self._write(commands['on'].encode())
    
    def off(self):
        """
        Turns off the balance.

        This method sends the 'off' command to the balance, effectively turning it off.
        """
        self._write(commands['off'].encode())
    
    def _write(self, command):
        """
        Writes a command to the communication interface and reads the response.

        Parameters
        ----------
        command : bytes
            The command to be sent. A line termination is added if it is not present.

        Returns
        -------
            list: A list of strings representing the response, split by commas.
        """
        if command[-2:] != b'\x0D\x0A':
            command += b'\x0D\x0A'  # add CR LF line termination

        self.comm.write(command)

        return decode_AnD(self.comm.read_until(b'\x0D\x0A').decode().strip())
    
    def get_weight(self, mode='stable'):
            """
            Get the weight from the balance.

            Parameters
            ----------
            mode : str, optional
                The mode for retrieving the weight. Can be one of 'stable', 'immediate', or 'continuous'. Default is 'stable'.

            Returns
            -------
            tuple
                Containing the weight (float), unit (str), and condition of the measurement (str).

            Raises
            ------
            ValueError
                If an invalid mode is provided.

            """
            match mode:
                case 'stable':
                    return self._write(commands['get_weight'].encode())
                case 'immediate':
                    return self._write(commands['get_immediate_weight'].encode())
                case 'continuous':
                    return self._write(commands['get_continuous_weight'].encode())
                case default:
                    raise ValueError("Invalid mode provided - must be one of 'stable', 'immediate' or 'continuous'.")
    
    def get_id(self):
        """
        Get the ID of the balance.

        Returns
        -------
        str
            The ID of the balance.

        """
        return self._write(commands['get_id'].encode())[0]
    
    def get_serial_number(self):
        """
        Get the serial number of the balance.

        Returns
        -------
        str
            The serial number of the balance.

        """
        return self._write(commands['get_serial_number'].encode())[0]
    
    def get_model_name(self):
        """
        Get the model name of the balance.

        Returns
        -------
        str
            The model name of the balance.

        """
        return self._write(commands['get_model_name'].encode())[0]
    
    def get_tare(self):
        """
        Get the tare weight from the balance.

        Returns
        -------
        tuple
            Containing the zero weight (float), unit (str), and measurement condition (str).
        """
        return self._write(commands['get_tare'].encode())
    
    def tare(self, value=None, units='g'):
        """
        Tare the balance, or set a specific zero value.

        Returns
        -------
        tuple
            Containing the zero weight (float), unit (str), and measurement condition (str).
        """
        if value is None:
            self._write(commands['tare'].encode())
            
        else:
            msg = f'PT:{value:.3f}{units.rjust(3)}'
            self._write(msg.encode())
        
        return self.get_tare()
    
    def __repr__(self):
        msg = []
        
        msg.append(f'A&D {self.model} Balance')
        msg.append(f'  Serial Number: {self.serial_number}')
        msg.append(f'  ID: {self.id}')
        msg.append('---')
        weight, unit, status = self.get_weight()
        msg.append(f'Current Weight: {weight} {unit} ({status})')
        zweight, zunit, _ = self.get_tare()
        msg.append(f'   Zero: {zweight} {zunit}')
        maxlen = max(len(x) for x in msg)
        msg.insert(0, '*' * maxlen)
        msg.append('*' * maxlen)
        
        return '\n'.join(msg)
        