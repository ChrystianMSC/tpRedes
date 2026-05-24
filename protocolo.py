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

    TAMANHO_MAX_PAYLOAD = 8
    CABECALHO_FORMATO = '!BBh'
    CABECALHO_TAMANHO = 4

    @staticmethod
    def calcular_checksum(dados):
        checksum = 0
        for byte in dados:
            checksum ^= byte
        return checksum

    @classmethod
    def build(cls, tipo, num_seq, payload):
        if len(payload) > cls.TAMANHO_MAX_PAYLOAD:
            payload = payload[:cls.TAMANHO_MAX_PAYLOAD]

        cabecalho_temp = struct.pack(cls.CABECALHO_FORMATO, tipo, 0, num_seq)
        dados_completos = cabecalho_temp + payload
        checksum = cls.calcular_checksum(dados_completos)

        return struct.pack(cls.CABECALHO_FORMATO, tipo, checksum, num_seq) + payload

    @classmethod
    def unpack_header(cls, dados):
        if len(dados) < cls.CABECALHO_TAMANHO:
            return None, None, None
        return struct.unpack(cls.CABECALHO_FORMATO, dados[:cls.CABECALHO_TAMANHO])
    
    @classmethod
    def validar_checksum(cls, dados):
        if len(dados) < cls.CABECALHO_TAMANHO:
            return False

        _, checksum_recebido, _ = cls.unpack_header(dados)

        copia = bytearray(dados)
        copia[1] = 0
        checksum_calculado = cls.calcular_checksum(bytes(copia))

        return checksum_calculado == checksum_recebido