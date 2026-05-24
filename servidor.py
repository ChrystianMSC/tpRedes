# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import random
from protocolo import Packet

class ServidorJogo:
    TIMEOUT = 0.1
    MAX_CLIENTES = 2
    BYTE_OFFSET_ZERO = 48
    BYTE_OFFSET_NOVE = 57
    ERRO_SEQ = 0
    ERRO_DIGITO_REPETIDO = 1

    def __init__(self, porta, senha_entrada, max_tentativas):
        self.porta = porta
        self.max_tentativas = max_tentativas
        self.senha_real = self.gerar_senha_real(senha_entrada)
        self.num_digitos = len(self.senha_real)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', porta))
        self.clientes = {}
        self.clientes_atendidos = 0

    @staticmethod
    def gerar_senha_real(senha_entrada):
        if (senha_entrada.isdigit() and
                all(c == '0' for c in senha_entrada) and
                4 <= len(senha_entrada) <= 8):
            comprimento = len(senha_entrada)
            digitos = list('0123456789')
            random.shuffle(digitos)
            return ''.join(digitos[:comprimento])
        return senha_entrada

    def validar_digitos(self, payload):
        if len(payload) < self.num_digitos:
            return False, None, 'TAMANHO_INVALIDO'

        digitos = list(payload[:self.num_digitos])

        for d in digitos:
            if not (self.BYTE_OFFSET_ZERO <= d <= self.BYTE_OFFSET_NOVE):
                return False, None, 'DIGITO_INVALIDO'

        if len(set(digitos)) != self.num_digitos:
            return False, None, 'DIGITO_REPETIDO'

        return True, digitos, None

    def calcular_feedback(self, palpite):
        feedback = []
        for i in range(self.num_digitos):
            if palpite[i] == self.senha_real[i]:
                feedback.append('*')
            elif palpite[i] in self.senha_real:
                feedback.append('+')
            else:
                feedback.append('-')
        return ''.join(feedback)

    def processar_tentativa(self, payload, num_seq, endereco):
        estado = self.clientes[endereco]

        if num_seq == estado['ultimo_seq'] and estado['ultimo_feedback'] is not None:
            return estado['ultimo_feedback'], estado['ultimo_restantes']

        seq_esperado = estado['tentativas'] + 1
        if num_seq != seq_esperado:
            return None, 'SEQ_INVALIDA'

        valido, digitos, erro = self.validar_digitos(payload)
        if not valido:
            return None, erro

        palpite = ''.join(chr(d) for d in digitos)
        feedback = self.calcular_feedback(palpite)

        estado['tentativas'] = num_seq
        estado['ultimo_seq'] = num_seq
        tentativas_restantes = self.max_tentativas - num_seq

        estado['ultimo_feedback'] = feedback
        estado['ultimo_restantes'] = tentativas_restantes

        return feedback, tentativas_restantes

    @staticmethod
    def criar_payload(conteudo, tamanho):
        return conteudo.ljust(tamanho, ' ').encode('ascii')

    def enviar_resposta_hel(self, endereco):
        payload = bytearray(8)
        for i in range(self.num_digitos):
            payload[i] = ord('?')

        pacote = Packet.build(Packet.TIPO_RES, self.max_tentativas, bytes(payload))
        self.socket.sendto(pacote, endereco)

        self.clientes[endereco] = {
            'ultimo_seq': 0,
            'tentativas': 0,
            'ultimo_feedback': None,
            'ultimo_restantes': None,
            'finalizado': False
        }

    def enviar_resposta_try(self, endereco, feedback, tentativas_restantes):
        payload = self.criar_payload(feedback, self.num_digitos)
        pacote = Packet.build(Packet.TIPO_RES, tentativas_restantes, payload)
        self.socket.sendto(pacote, endereco)

        if feedback == '*' * self.num_digitos and not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def enviar_resposta_bye(self, endereco):
        payload = self.criar_payload(self.senha_real, self.num_digitos)
        pacote = Packet.build(Packet.TIPO_RES, -1, payload)
        self.socket.sendto(pacote, endereco)

        if not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def enviar_erro(self, endereco, seq):
        pacote = Packet.build(Packet.TIPO_ERR, seq, b'')
        self.socket.sendto(pacote, endereco)

    def processar_cliente_novo(self, tipo: int, num_seq: int, endereco):
        if tipo == Packet.TIPO_HEL and num_seq == 0:
            self.enviar_resposta_hel(endereco)
        else:
            self.enviar_erro(endereco, 0)

    def processar_comando_try(self, payload, num_seq, endereco, estado):
        if num_seq == estado['ultimo_seq'] and estado['ultimo_feedback'] is not None:
            self.enviar_resposta_try(endereco, estado['ultimo_feedback'], estado['ultimo_restantes'])
            return

        if estado['tentativas'] >= self.max_tentativas:
            self.enviar_erro(endereco, 0)
            return

        resultado = self.processar_tentativa(payload, num_seq, endereco)

        if resultado[0] is None:
            codigo_erro = self.ERRO_DIGITO_REPETIDO if resultado[1] == 'DIGITO_REPETIDO' else 0
            self.enviar_erro(endereco, codigo_erro)
        else:
            feedback, restantes = resultado
            self.enviar_resposta_try(endereco, feedback, restantes)

    def processar_comando_bye(self, num_seq, endereco, estado):
        if estado['finalizado']:
            self.enviar_resposta_bye(endereco)
            return

        seq_esperado = estado['tentativas']
        if num_seq == seq_esperado:
            self.enviar_resposta_bye(endereco)
        else:
            self.enviar_erro(endereco, 0)

    def processar_pacote(self, dados, endereco):
        if not Packet.validar_checksum(dados):
            return

        tipo, _, num_seq = Packet.unpack_header(dados)
        payload = dados[4:] if len(dados) > 4 else b''

        if endereco not in self.clientes:
            self.processar_cliente_novo(tipo, num_seq, endereco)
            return

        estado = self.clientes[endereco]

        if tipo == Packet.TIPO_TRY:
            self.processar_comando_try(payload, num_seq, endereco, estado)
        elif tipo == Packet.TIPO_BYE:
            self.processar_comando_bye(num_seq, endereco, estado)
        elif tipo == Packet.TIPO_HEL:
            self.enviar_resposta_hel(endereco)
        else:
            self.enviar_erro(endereco, 0)

    def iniciar(self):
        self.socket.settimeout(self.TIMEOUT)

        while self.clientes_atendidos < self.MAX_CLIENTES:
            try:
                dados, endereco = self.socket.recvfrom(1024)
            except socket.timeout:
                continue

            if len(dados) < 4:
                continue

            self.processar_pacote(dados, endereco)

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