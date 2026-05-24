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
        """Calcula o checksum XOR de todos os bytes"""
        checksum = 0
        for byte in dados:
            checksum ^= byte
        return checksum

    @classmethod
    def build(cls, tipo: int, num_seq: int, payload: bytes = b'') -> bytes:
        """
        Constrói um pacote no formato:
        TIPO (1 byte) | Checksum (1 byte) | NUMSEQ (2 bytes) | Payload (0-8 bytes)
        """
        # Payload deve ter no máximo 8 bytes
        if len(payload) > 8:
            payload = payload[:8]

        # Prepara o cabeçalho temporário (checksum temporário = 0)
        cabecalho_temp = struct.pack('!BBH', tipo, 0, num_seq)

        # Calcula o checksum
        dados_completos = cabecalho_temp + payload
        checksum = cls.calcular_checksum(dados_completos)

        # Monta pacote final com checksum correto
        return struct.pack('!BBH', tipo, checksum, num_seq) + payload

    @classmethod
    def unpack_header(cls, dados: bytes):
        """Extrai tipo, checksum e num_seq dos primeiros 4 bytes"""
        if len(dados) < 4:
            return None, None, None
        return struct.unpack('!BBH', dados[:4])

    @classmethod
    def validar_checksum(cls, dados: bytes) -> bool:
        """Verifica se o checksum do pacote está correto"""
        if len(dados) < 4:
            return False

        # Extrai checksum recebido
        _, checksum_recebido, _ = cls.unpack_header(dados)

        # Recalcula checksum (zerando o campo checksum original)
        copia = bytearray(dados)
        copia[1] = 0
        checksum_calculado = cls.calcular_checksum(bytes(copia))

        return checksum_calculado == checksum_recebido