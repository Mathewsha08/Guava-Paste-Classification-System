"""
PLC Communication Module for Delta AS200
Supports Modbus TCP and Modbus RTU protocols
"""

import logging
from typing import Optional, Dict
from enum import Enum
import time

try:
    from pymodbus.client import ModbusTcpClient, ModbusSerialClient
    from pymodbus.exceptions import ModbusException
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    logging.warning("pymodbus not installed. Install with: pip install pymodbus")


class CommunicationProtocol(Enum):
    """Available communication protocols"""
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"


class PLCCommunicator:
    """Handles communication with Delta AS200 PLC via Modbus"""
    
    def __init__(self, protocol: CommunicationProtocol = CommunicationProtocol.MODBUS_TCP):
        """
        Initialize PLC communicator
        
        Args:
            protocol: Communication protocol to use
        """
        self.protocol = protocol
        self.client = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # Connection parameters
        self.connection_params = {}
        
        # Updated PLC memory addresses for Delta AS200 (using M-bits)
        self.output_addresses = {

            'comm_confirm': 1401,
            'system_ready': 1404,
            'heartbeat': 1406,
            'data_ready_tick': 1412,  # M1412 - The trigger for SFWRP
            'conveyor_running': 1416    # M6 - Conveyor Status Bit
        }

        # Inside plc_communicator.py
        self.register_addresses = {
            'classification_result': 498  # Changed from 4606 to 498 for AS200
        }
        
        #self.input_addresses = {
        #    'trigger': 0,        # X0 - Inspection trigger
        #    'reset': 1,          # X1 - Reset input
        #    'enable': 2          # X2 - System enable
        #}
        
        if not MODBUS_AVAILABLE:
            self.logger.error("pymodbus library not available. PLC communication disabled.")
    
    def send_to_fifo(self, is_good: bool) -> bool:
        """Writes result to D498 and triggers M1412 for the PLC FIFO"""
        if not self.connected:
            return False
        
        # 1 = PASS, 2 = REJECT
        val = 1 if is_good else 2
        address_d498 = self.register_addresses['classification_result']
        address_m1412 = self.output_addresses['data_ready_tick']
        
        try:
            # Step 1: Write the value to D498 (Register 4606)
            # We use a loop to try different parameter names (slave, unit, device_id)
            success_reg = False
            for param_name in ['slave', 'unit', 'device_id']:
                try:
                    self.client.write_register(address_d498, val, **{param_name: 1})
                    success_reg = True
                    break
                except TypeError:
                    continue

            if not success_reg:
                raise Exception("Could not find correct Modbus ID parameter name")

            time.sleep(0.02) # Small safety delay

            # Step 2: Trigger M1412 (Coil 9588)
            # Using your existing write_output logic to be safe
            self.write_output('data_ready_tick', True)
            
            self.logger.info(f"FIFO Sent: {'PASS' if is_good else 'REJECT'} (Val: {val})")
            return True
        except Exception as e:
            self.logger.error(f"Modbus FIFO Error: {e}")
            return False
    
    def connect_tcp(self, host: str = "192.168.1.5", port: int = 502, 
                   unit_id: int = 1, timeout: int = 3) -> bool:
        """
        Connect to PLC via Modbus TCP
        
        Args:
            host: PLC IP address
            port: Modbus TCP port (default 502)
            unit_id: Modbus unit/slave ID
            timeout: Connection timeout in seconds
            
        Returns:
            True if connection successful
        """
        if not MODBUS_AVAILABLE:
            self.logger.error("Cannot connect: pymodbus not installed")
            return False
        
        try:
            self.connection_params = {
                'host': host,
                'port': port,
                'unit_id': unit_id,
                'timeout': timeout
            }
            
            self.client = ModbusTcpClient(
                host=host,
                port=port,
                timeout=timeout
            )
            
            self.connected = self.client.connect()
            
            if self.connected:
                self.logger.info(f"Connected to PLC via Modbus TCP at {host}:{port}")
                # Set system ready flag
                self.write_output('system_ready', True)
            else:
                self.logger.error(f"Failed to connect to PLC at {host}:{port}")
            
            return self.connected
            
        except Exception as e:
            self.logger.error(f"TCP connection error: {e}")
            self.connected = False
            return False
    
    def connect_serial(self, port: str = "COM1", baudrate: int = 9600,
                      parity: str = 'N', stopbits: int = 1, bytesize: int = 8,
                      unit_id: int = 1, timeout: int = 3) -> bool:
        """
        Connect to PLC via Modbus RTU (Serial)
        
        Args:
            port: Serial port (e.g., 'COM1' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate (9600, 19200, 38400, etc.)
            parity: Parity ('N', 'E', 'O')
            stopbits: Stop bits (1 or 2)
            bytesize: Data bits (7 or 8)
            unit_id: Modbus unit/slave ID
            timeout: Communication timeout in seconds
            
        Returns:
            True if connection successful
        """
        if not MODBUS_AVAILABLE:
            self.logger.error("Cannot connect: pymodbus not installed")
            return False
        
        try:
            self.connection_params = {
                'port': port,
                'baudrate': baudrate,
                'parity': parity,
                'stopbits': stopbits,
                'bytesize': bytesize,
                'unit_id': unit_id,
                'timeout': timeout
            }
            
            self.client = ModbusSerialClient(
                port=port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=timeout
            )
            
            self.connected = self.client.connect()
            
            if self.connected:
                self.logger.info(f"Connected to PLC via Modbus RTU on {port} "
                               f"at {baudrate} baud")
                # Set system ready flag
                self.write_output('system_ready', True)
            else:
                self.logger.error(f"Failed to connect to PLC on {port}")
            
            return self.connected
            
        except Exception as e:
            self.logger.error(f"Serial connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from PLC"""
        if self.client and self.connected:
            try:
                # Clear system ready flag
                self.write_output('system_ready', False)
                self.client.close()
                self.connected = False
                self.logger.info("Disconnected from PLC")
            except Exception as e:
                self.logger.error(f"Disconnect error: {e}")

    def write_output(self, name: str, value: bool) -> bool:
        if not self.connected or name not in self.output_addresses:
            print(f"Unknown output: {name}") # This fixes your 'Unknown output' error
            return False
        
        address = self.output_addresses[name]
        try:
            # This logic works for Pymodbus 2.x, 3.x, and 4.x
            params = {"address": address, "value": value}
            
            # Try the newest parameter name first, then fall back
            try:
                return self.client.write_coil(**params, device_id=1).isError() == False
            except TypeError:
                try:
                    return self.client.write_coil(**params, slave=1).isError() == False
                except TypeError:
                    return self.client.write_coil(**params, unit=1).isError() == False
        except Exception as e:
            print(f"Write error for {name}: {e}")
            return False

    def read_input(self, name: str) -> Optional[bool]:
        if not self.connected or name not in self.input_addresses:
            return None
            
        address = self.input_addresses[name]
        try:
            # Flexible reading logic
            try:
                result = self.client.read_discrete_inputs(address, 1, device_id=1)
            except TypeError:
                try:
                    result = self.client.read_discrete_inputs(address, 1, slave=1)
                except TypeError:
                    result = self.client.read_discrete_inputs(address, 1, unit=1)
            
            return result.bits[0] if result and not result.isError() else None
        except Exception as e:
            print(f"Read error for {name}: {e}")
            return None            
    
    
    def send_inspection_result(self, is_good: bool, pulse_duration: float = 0.5) -> bool:
        """
        Send inspection result to PLC
        
        Args:
            is_good: True if part is good, False if bad
            pulse_duration: Duration of output pulse in seconds
            
        Returns:
            True if sent successfully
        """
        output_name = 'part_good' if is_good else 'part_bad'
        
        # Send pulse
        success = self.write_output(output_name, True)
        if success:
            time.sleep(pulse_duration)
            self.write_output(output_name, False)
            self.logger.info(f"Sent result: {output_name.upper()}")
        
        return success
    
    def get_connection_status(self) -> Dict:
        """
        Get current connection status
        
        Returns:
            Dictionary with connection information
        """
        return {
            'connected': self.connected,
            'protocol': self.protocol.value,
            'parameters': self.connection_params
        }
    
    def test_connection(self) -> bool:
        """
        Test PLC connection by attempting to read an input
        
        Returns:
            True if connection is working
        """
        if not self.connected:
            return False
        
        try:
            # Try to read first input
            result = self.read_input('trigger')
            return result is not None
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
        
    def read_bit(self, name: str) -> Optional[bool]:
            """Reads the status of a coil (M-bit) from the PLC using Function 01"""
            if not self.connected or name not in self.output_addresses:
                return None
            
            address = self.output_addresses[name]
            try:
                # Address is positional, all others MUST be keywords
                # We try 'slave' first, then 'unit', then just 'count'
                result = None
                try:
                    result = self.client.read_coils(address, count=1, slave=1)
                except TypeError:
                    try:
                        result = self.client.read_coils(address, count=1, unit=1)
                    except TypeError:
                        result = self.client.read_coils(address, count=1)
                        
                if result is None or result.isError():
                    return None
                return result.bits[0]
            except Exception as e:
                # Catching the error ensures the loop doesn't crash
                print(f"Read error for {name}: {e}")
                return None
