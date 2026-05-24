# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import random
from typing import Union, Optional, Tuple
from protocolo import Packet

class ServidorJogo:
    _TIMEOUT = 0.1
    _MAX_CLIENTES = 2
    _BYTE_OFFSET_ZERO = 48
    _BYTE_OFFSET_NOVE = 57
    _ERRO_SEQ = 0
    _ERRO_DIGITO_REPETIDO = 1

    def __init__(self, porta: int, senha_entrada: str, max_tentativas: int):
        self.porta = porta
        self.max_tentativas = max_tentativas
        self.senha_real = self._gerar_senha_real(senha_entrada)
        self.num_digitos = len(self.senha_real)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', porta))
        self.clientes = {}
        self.clientes_atendidos = 0

    @staticmethod
    def _gerar_senha_real(senha_entrada: str) -> str:
        if (senha_entrada.isdigit() and
                all(c == '0' for c in senha_entrada) and
                4 <= len(senha_entrada) <= 8):
            comprimento = len(senha_entrada)
            digitos = list('0123456789')
            random.shuffle(digitos)
            return ''.join(digitos[:comprimento])
        return senha_entrada

    def _validar_digitos(self, payload: bytes) -> Tuple[bool, Optional[list], Optional[str]]:
        if len(payload) < self.num_digitos:
            return False, None, 'TAMANHO_INVALIDO'

        digitos = list(payload[:self.num_digitos])

        for d in digitos:
            if not (self._BYTE_OFFSET_ZERO <= d <= self._BYTE_OFFSET_NOVE):
                return False, None, 'DIGITO_INVALIDO'

        if len(set(digitos)) != self.num_digitos:
            return False, None, 'DIGITO_REPETIDO'

        return True, digitos, None

    def _calcular_feedback(self, palpite: str) -> str:
        feedback = []
        for i in range(self.num_digitos):
            if palpite[i] == self.senha_real[i]:
                feedback.append('*')
            elif palpite[i] in self.senha_real:
                feedback.append('+')
            else:
                feedback.append('-')
        return ''.join(feedback)

    def _processar_tentativa(self, payload: bytes, num_seq: int, endereco) -> Tuple[Optional[str], Union[str, int]]:
        estado = self.clientes[endereco]
        seq_esperado = estado['tentativas'] + 1

        if num_seq != seq_esperado:
            return None, 'SEQ_INVALIDA'

        valido, digitos, erro = self._validar_digitos(payload)
        if not valido:
            return None, erro

        palpite = ''.join(chr(d) for d in digitos)
        feedback = self._calcular_feedback(palpite)

        estado['tentativas'] = num_seq
        tentativas_restantes = self.max_tentativas - num_seq

        return feedback, tentativas_restantes

    def _criar_payload(self, conteudo: str, tamanho: int = 8) -> bytes:
        return conteudo.ljust(tamanho, ' ').encode('ascii')

    def _enviar_resposta_hel(self, endereco):
        payload = bytearray(8)
        for i in range(self.num_digitos):
            payload[i] = ord('?')

        pacote = Packet.build(Packet.TIPO_RES, self.max_tentativas, bytes(payload))
        self.socket.sendto(pacote, endereco)

        self.clientes[endereco] = {
            'ultimo_seq': 0,
            'tentativas': 0,
            'aguardando_hel': False
        }

    def _enviar_resposta_try(self, endereco, feedback: str, tentativas_restantes: int):
        payload = self._criar_payload(feedback)
        pacote = Packet.build(Packet.TIPO_RES, tentativas_restantes, payload)
        self.socket.sendto(pacote, endereco)

        if feedback == '*' * self.num_digitos and not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_resposta_bye(self, endereco):
        payload = self._criar_payload(self.senha_real)
        pacote = Packet.build(Packet.TIPO_RES, 65535, payload)
        self.socket.sendto(pacote, endereco)

        if not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_erro(self, endereco, seq: int):
        pacote = Packet.build(Packet.TIPO_ERR, seq, b'')
        self.socket.sendto(pacote, endereco)

    def _processar_cliente_novo(self, tipo: int, num_seq: int, endereco):
        if tipo == Packet.TIPO_HEL and num_seq == 0:
            self._enviar_resposta_hel(endereco)
        else:
            self._enviar_erro(endereco, 0)

    def _processar_comando_try(self, payload: bytes, num_seq: int, endereco, estado: dict):
        if estado['tentativas'] >= self.max_tentativas:
            self._enviar_erro(endereco, 0)
            return

        resultado = self._processar_tentativa(payload, num_seq, endereco)

        if resultado[0] is None:
            codigo_erro = self._ERRO_DIGITO_REPETIDO if resultado[1] == 'DIGITO_REPETIDO' else 0
            self._enviar_erro(endereco, codigo_erro)
        else:
            feedback, restantes = resultado
            self._enviar_resposta_try(endereco, feedback, restantes)

    def _processar_comando_bye(self, num_seq: int, endereco, estado: dict):
        seq_esperado = estado['tentativas']
        if num_seq == seq_esperado:
            self._enviar_resposta_bye(endereco)
        else:
            self._enviar_erro(endereco, 0)

    def _processar_pacote(self, dados: bytes, endereco):
        if not Packet.validar_checksum(dados):
            return

        tipo, _, num_seq = Packet.unpack_header(dados)
        payload = dados[4:] if len(dados) > 4 else b''

        if endereco not in self.clientes:
            self._processar_cliente_novo(tipo, num_seq, endereco)
            return

        estado = self.clientes[endereco]

        if tipo == Packet.TIPO_TRY:
            self._processar_comando_try(payload, num_seq, endereco, estado)
        elif tipo == Packet.TIPO_BYE:
            self._processar_comando_bye(num_seq, endereco, estado)
        elif tipo == Packet.TIPO_HEL:
            self._enviar_resposta_hel(endereco)
        else:
            self._enviar_erro(endereco, 0)

    def iniciar(self):
        self.socket.settimeout(self._TIMEOUT)

        while self.clientes_atendidos < self._MAX_CLIENTES:
            try:
                dados, endereco = self.socket.recvfrom(1024)
            except socket.timeout:
                continue

            if len(dados) < 4:
                continue

            self._processar_pacote(dados, endereco)

def main():
    if len(sys.argv) != 4:
        print("Uso: python3 servidor.py <porta> <senha> <max_tentativas>")
        sys.exit(1)

    porta = int(sys.argv[1])
    senha = sys.argv[2]
    max_tentativas = int(sys.argv[3])

    servidor = ServidorJogo(porta, senha, max_tentativas)
    servidor.iniciar()

if __name__ == '__main__':
    main()