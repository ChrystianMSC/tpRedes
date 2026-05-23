# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import struct

# Define a estrutura de pacotes do protocolo, lidando com cabeçalho, payload e integridade
class Packet:
    TIPO_START = 1
    TIPO_TRY = 2
    TIPO_RESPONSE = 3
    TIPO_GIVE_UP = 4
    TIPO_ERROR = 5

    # Calcula o checksum dos bytes do pacote utilizando a operação lógica XOR
    @staticmethod
    def calculateChecksum(data: bytes) -> int:
        checksum = 0
        for b in data:
            checksum ^= b
        return checksum

    # Constrói o pacote final em bytes empacotando o tipo, sequência, checksum e tratando o payload
    @classmethod
    def build(cls, tipo: int, seqnum: int, payloadData) -> bytes:
        if tipo == cls.TIPO_TRY:
            if isinstance(payloadData, str):
                ints = [int(c) for c in payloadData if c.isdigit()]
            else:
                ints = list(payloadData)
            payload = bytes(ints).ljust(8, b'\x00')
        else:
            payload = payloadData.ljust(8).encode('ascii')[:8]

        headerTemp = struct.pack('!BBH', tipo, 0, seqnum)
        cksum = cls.calculateChecksum(headerTemp + payload)

        return struct.pack('!BBH', tipo, cksum, seqnum) + payload

    # Desempacota os 4 bytes iniciais do pacote extraindo o tipo, checksum e número de sequência
    @classmethod
    def unpackHeader(cls, data: bytes):
        return struct.unpack('!BBH', data[:4])