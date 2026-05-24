# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import struct

class Packet:
    TIPO_HEL = 1
    TIPO_TRY = 2
    TIPO_RES = 3
    TIPO_BYE = 4
    TIPO_ERR = 5

    MAX_TENTATIVAS_ENVIO = 3
    TIMEOUT_SEGUNDOS = 1.0

    @staticmethod
    def calcular_checksum(dados: bytes) -> int:
        checksum = 0
        for byte in dados:
            checksum ^= byte
        return checksum

    @classmethod
    def build(cls, tipo: int, num_seq: int, payload: bytes = b'') -> bytes:
        if len(payload) > 8:
            payload = payload[:8]

        cabecalho_temp = struct.pack('!BBH', tipo, 0, num_seq)

        dados_completos = cabecalho_temp + payload
        checksum = cls.calcular_checksum(dados_completos)

        return struct.pack('!BBH', tipo, checksum, num_seq) + payload

    @classmethod
    def unpack_header(cls, dados: bytes):
        if len(dados) < 4:
            return None, None, None
        return struct.unpack('!BBH', dados[:4])

    @classmethod
    def validar_checksum(cls, dados: bytes) -> bool:
        if len(dados) < 4:
            return False

        _, checksum_recebido, _ = cls.unpack_header(dados)

        copia = bytearray(dados)
        copia[1] = 0
        checksum_calculado = cls.calcular_checksum(bytes(copia))

        return checksum_calculado == checksum_recebido