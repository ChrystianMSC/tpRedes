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
    def calcular_checksum(dados: bytes) -> int:
        checksum = 0
        for byte in dados:
            checksum ^= byte
        return checksum

    # Constrói o pacote final em bytes empacotando o tipo, sequência, checksum e tratando o payload
    @classmethod
    def construir(cls, tipo: int, num_seq: int, dados_payload) -> bytes:
        if tipo == cls.TIPO_TRY:
            if isinstance(dados_payload, str):
                inteiros = [int(c) for c in dados_payload if c.isdigit()]
            else:
                inteiros = list(dados_payload)
            payload = bytes(inteiros).ljust(8, b'\x00')
        else:
            payload = dados_payload.ljust(8).encode('ascii')[:8]

        cabecalho_temp = struct.pack('!BBH', tipo, 0, num_seq)
        checksum = cls.calcular_checksum(cabecalho_temp + payload)

        return struct.pack('!BBH', tipo, checksum, num_seq) + payload

    # Desempacota os 4 bytes iniciais do pacote extraindo o tipo, checksum e número de sequência
    @classmethod
    def desempacotar_cabecalho(cls, dados: bytes):
        return struct.unpack('!BBH', dados[:4])