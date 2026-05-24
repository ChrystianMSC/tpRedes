# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import random
from protocolo import Packet

class ServidorJogo:
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

    def _processar_tentativa(self, payload: bytes, num_seq: int, endereco) -> tuple:
        estado = self.clientes[endereco]

        seq_esperado = estado['tentativas'] + 1
        if num_seq != seq_esperado:
            return None, 'SEQ_INVALIDA'

        if len(payload) < self.num_digitos:
            return None, 'TAMANHO_INVALIDO'

        digitos = [payload[i] for i in range(self.num_digitos)]

        for d in digitos:
            if d < 48 or d > 57:
                return None, 'DIGITO_INVALIDO'

        if len(set(digitos)) != self.num_digitos:
            return None, 'DIGITO_REPETIDO'

        palpite = ''.join(chr(d) for d in digitos)

        feedback = []
        for i in range(self.num_digitos):
            if palpite[i] == self.senha_real[i]:
                feedback.append('*')
            elif palpite[i] in self.senha_real:
                feedback.append('+')
            else:
                feedback.append('-')

        feedback_str = ''.join(feedback)
        estado['tentativas'] = num_seq
        tentativas_restantes = self.max_tentativas - num_seq

        return feedback_str, tentativas_restantes

    def _enviar_resposta_hel(self, endereco):
        payload = ('?' * self.num_digitos).ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, self.max_tentativas, payload)
        self.socket.sendto(pacote, endereco)

        self.clientes[endereco] = {
            'ultimo_seq': 0,
            'tentativas': 0,
            'aguardando_hel': False
        }

    def _enviar_resposta_try(self, endereco, feedback: str, tentativas_restantes: int):
        payload = feedback.ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, tentativas_restantes, payload)
        self.socket.sendto(pacote, endereco)

        if feedback == '*' * self.num_digitos and not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_resposta_bye(self, endereco):
        payload = self.senha_real.ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, 65535, payload)
        self.socket.sendto(pacote, endereco)

        if not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_erro(self, endereco, seq: int):
        pacote = Packet.build(Packet.TIPO_ERR, seq, b'')
        self.socket.sendto(pacote, endereco)

    def iniciar(self):
        self.socket.settimeout(0.1)

        while self.clientes_atendidos < 2:
            try:
                dados, endereco = self.socket.recvfrom(1024)
            except socket.timeout:
                continue

            if len(dados) < 4:
                continue

            if not Packet.validar_checksum(dados):
                continue

            tipo, _, num_seq = Packet.unpack_header(dados)
            payload = dados[4:] if len(dados) > 4 else b''

            if endereco not in self.clientes:
                if tipo == Packet.TIPO_HEL and num_seq == 0:
                    self._enviar_resposta_hel(endereco)
                else:
                    self._enviar_erro(endereco, 0)
                continue

            estado = self.clientes[endereco]

            if tipo == Packet.TIPO_TRY:
                if estado['tentativas'] >= self.max_tentativas:
                    self._enviar_erro(endereco, 0)
                    continue

                resultado = self._processar_tentativa(payload, num_seq, endereco)
                if resultado[0] is None:
                    if resultado[1] == 'DIGITO_REPETIDO':
                        self._enviar_erro(endereco, 1)
                    else:
                        self._enviar_erro(endereco, 0)
                else:
                    feedback, restantes = resultado
                    self._enviar_resposta_try(endereco, feedback, restantes)

            elif tipo == Packet.TIPO_BYE:
                seq_esperado = estado['tentativas']
                if num_seq == seq_esperado:
                    self._enviar_resposta_bye(endereco)
                else:
                    self._enviar_erro(endereco, 0)

            elif tipo == Packet.TIPO_HEL:
                self._enviar_resposta_hel(endereco)

            else:
                self._enviar_erro(endereco, 0)

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