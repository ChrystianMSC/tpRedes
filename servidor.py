# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import random
from protocolo import Packet

class ClienteSessao:
    def __init__(self):
        self.tentativas = 0
        self.ultima_resposta = None
        self.ultimo_seq = -1
        self.finalizado = False

class ServidorJogo:
    def __init__(self, porta: int, senha_entrada: str, max_tentativas: int):
        self.porta = porta
        self.max_tentativas = max_tentativas
        self.senha_real = self._gerar_senha_real(senha_entrada)
        self.num_digitos = len(self.senha_real)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.estado_clientes = {}
        self.clientes_atendidos = 0

    # Define a senha do jogo ou gera uma aleatória caso receba uma sequência de zeros
    def _gerar_senha_real(self, senha_entrada: str) -> str:
        if senha_entrada.isdigit() and all(c == '0' for c in senha_entrada) and 4 <= len(senha_entrada) <= 8:
            comprimento = len(senha_entrada)
            digitos = list("0123456789")
            random.shuffle(digitos)
            return "".join(digitos[:comprimento])
        return senha_entrada

    # Recupera a sessão ativa do cliente pelo endereço ou cria uma nova se for o primeiro contato
    def _obter_ou_criar_sessao(self, endereco) -> ClienteSessao:
        if endereco not in self.estado_clientes:
            self.estado_clientes[endereco] = ClienteSessao()
        return self.estado_clientes[endereco]

    # Recalcula e valida o checksum do pacote recebido do cliente
    def _validar_checksum(self, dados: bytes, checksum_recebido: int) -> bool:
        dados_recalculados = bytearray(dados)
        dados_recalculados[1] = 0
        return Packet.calcular_checksum(dados_recalculados) == checksum_recebido

    # Valida as regras do palpite enviado e gera a string de feedback (*, +, -)
    def _processar_tentativa(self, dados: bytes, num_seq: int, contexto: ClienteSessao) -> str:
        if len(dados) < 4 + self.num_digitos:
            return None

        payload_inteiros = list(dados[4:4 + self.num_digitos])
        payload_str = "".join(str(x) for x in payload_inteiros)

        seq_esperado = contexto.tentativas + 1
        if num_seq != seq_esperado:
            return None

        if (len(set(payload_inteiros)) != self.num_digitos
                or any(x > 9 for x in payload_inteiros)):
            return None

        contexto.tentativas = num_seq

        feedback = ""
        for i in range(self.num_digitos):
            if payload_str[i] == self.senha_real[i]:
                feedback += "*"
            elif payload_str[i] in self.senha_real:
                feedback += "+"
            else:
                feedback += "-"
        return feedback

    # Inicializa o socket e executa o loop principal de recebimento e tratamento de pacotes
    def iniciar(self):
        self.socket.bind(('0.0.0.0', self.porta))
        self.socket.settimeout(0.1)

        while self.clientes_atendidos < 2:
            try:
                dados, endereco = self.socket.recvfrom(1024)
            except socket.timeout:
                continue

            if len(dados) < 4:
                continue

            tipo, checksum_recebido, num_seq = Packet.unpack_header(dados)

            if not self._validar_checksum(dados, checksum_recebido):
                continue

            contexto = self._obter_ou_criar_sessao(endereco)

            if tipo == Packet.TIPO_START:
                payload_resposta = "?" * self.num_digitos
                contexto.ultima_resposta = Packet.build(Packet.TIPO_RESPONSE, self.max_tentativas, payload_resposta)
                self.socket.sendto(contexto.ultima_resposta, endereco)

            elif tipo == Packet.TIPO_TRY:
                feedback = self._processar_tentativa(dados, num_seq, contexto)
                if feedback is None:
                    pacote_erro = Packet.build(Packet.TIPO_ERROR, 1 if num_seq <= self.max_tentativas else 0, "")
                    self.socket.sendto(pacote_erro, endereco)
                    continue

                contexto.ultima_resposta = Packet.build(Packet.TIPO_RESPONSE, self.max_tentativas - num_seq, feedback)
                self.socket.sendto(contexto.ultima_resposta, endereco)

                if feedback == "*" * self.num_digitos and not contexto.finalizado:
                    contexto.finalizado = True
                    self.clientes_atendidos += 1

            elif tipo == Packet.TIPO_GIVE_UP:
                contexto.ultima_resposta = Packet.build(Packet.TIPO_RESPONSE, 65535, self.senha_real)
                self.socket.sendto(contexto.ultima_resposta, endereco)
                if not contexto.finalizado:
                    contexto.finalizado = True
                    self.clientes_atendidos += 1

            elif tipo in (Packet.TIPO_RESPONSE, Packet.TIPO_ERROR):
                pacote_erro = Packet.build(Packet.TIPO_ERROR, 0, "")
                self.socket.sendto(pacote_erro, endereco)

def main():
    if len(sys.argv) != 4:
        sys.exit(1)

    porta = int(sys.argv[1])
    senha_entrada = sys.argv[2]
    max_tentativas = int(sys.argv[3])

    servidor = ServidorJogo(porta, senha_entrada, max_tentativas)
    servidor.iniciar()

if __name__ == "__main__":
    main()