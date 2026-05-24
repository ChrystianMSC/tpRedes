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

    def build(self, tipo, num_seq, payload):
        if len(payload) > self.TAMANHO_MAX_PAYLOAD:
            payload = payload[:self.TAMANHO_MAX_PAYLOAD]

        cabecalho_temp = struct.pack(self.CABECALHO_FORMATO, tipo, 0, num_seq)
        dados_completos = cabecalho_temp + payload
        checksum = self.calcular_checksum(dados_completos)

        return struct.pack(self.CABECALHO_FORMATO, tipo, checksum, num_seq) + payload

    def unpack_header(self, dados):
        if len(dados) < self.CABECALHO_TAMANHO:
            return None, None, None
        return struct.unpack(self.CABECALHO_FORMATO, dados[:self.CABECALHO_TAMANHO])

    def validar_checksum(self, dados):
        if len(dados) < self.CABECALHO_TAMANHO:
            return False

        _, checksum_recebido, _ = self.unpack_header(dados)

        copia = bytearray(dados)
        copia[1] = 0
        checksum_calculado = self.calcular_checksum(bytes(copia))

        return checksum_calculado == checksum_recebido