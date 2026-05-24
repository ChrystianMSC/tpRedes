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

    _TAMANHO_MAX_PAYLOAD = 8
    _CABECALHO_FORMATO = '!BBH'
    _CABECALHO_TAMANHO = 4

    @staticmethod
    def calcular_checksum(dados: bytes) -> int:
        checksum = 0
        for byte in dados:
            checksum ^= byte
        return checksum

    @classmethod
    def build(cls, tipo: int, num_seq: int, payload: bytes = b'') -> bytes:
        if len(payload) > cls._TAMANHO_MAX_PAYLOAD:
            payload = payload[:cls._TAMANHO_MAX_PAYLOAD]

        cabecalho_temp = struct.pack(cls._CABECALHO_FORMATO, tipo, 0, num_seq)
        dados_completos = cabecalho_temp + payload
        checksum = cls.calcular_checksum(dados_completos)

        return struct.pack(cls._CABECALHO_FORMATO, tipo, checksum, num_seq) + payload

    @classmethod
    def unpack_header(cls, dados: bytes):
        if len(dados) < cls._CABECALHO_TAMANHO:
            return None, None, None
        return struct.unpack(cls._CABECALHO_FORMATO, dados[:cls._CABECALHO_TAMANHO])

    @classmethod
    def validar_checksum(cls, dados: bytes) -> bool:
        if len(dados) < cls._CABECALHO_TAMANHO:
            return False

        _, checksum_recebido, _ = cls.unpack_header(dados)

        copia = bytearray(dados)
        copia[1] = 0
        checksum_calculado = cls.calcular_checksum(bytes(copia))

        return checksum_calculado == checksum_recebido