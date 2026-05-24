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

        # Estado dos clientes: endereco -> {'ultimo_seq': int, 'tentativas': int, 'aguardando_hel': bool}
        self.clientes = {}
        self.clientes_atendidos = 0

    def _gerar_senha_real(self, senha_entrada: str) -> str:
        """Gera senha aleatória se entrada for sequência de zeros"""
        if (senha_entrada.isdigit() and
                all(c == '0' for c in senha_entrada) and
                4 <= len(senha_entrada) <= 8):
            comprimento = len(senha_entrada)
            digitos = list('0123456789')
            random.shuffle(digitos)
            return ''.join(digitos[:comprimento])
        return senha_entrada

    def _processar_tentativa(self, payload: bytes, num_seq: int, endereco) -> tuple:
        """Processa uma tentativa e retorna (feedback, remaining_tentativas) ou (None, motivo_erro)"""
        estado = self.clientes[endereco]

        # Verifica sequência
        seq_esperado = estado['tentativas'] + 1
        if num_seq != seq_esperado:
            return None, 'SEQ_INVALIDA'

        # Verifica tamanho do payload
        if len(payload) < self.num_digitos:
            return None, 'TAMANHO_INVALIDO'

        # Extrai os dígitos
        digitos = [payload[i] for i in range(self.num_digitos)]

        # Verifica se são dígitos válidos e sem repetição
        for d in digitos:
            if d < 48 or d > 57:  # '0' é 48, '9' é 57
                return None, 'DIGITO_INVALIDO'

        # Verifica repetição
        if len(set(digitos)) != self.num_digitos:
            return None, 'DIGITO_REPETIDO'

        # Converte para string para facilitar comparação
        palpite = ''.join(chr(d) for d in digitos)

        # Gera feedback
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
        """Envia resposta ao HEL: RES com NT e NA interrogações"""
        payload = ('?' * self.num_digitos).ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, self.max_tentativas, payload)
        self.socket.sendto(pacote, endereco)

        # Inicializa estado do cliente
        self.clientes[endereco] = {
            'ultimo_seq': 0,
            'tentativas': 0,
            'aguardando_hel': False
        }

    def _enviar_resposta_try(self, endereco, feedback: str, tentativas_restantes: int):
        """Envia resposta ao TRY: RES com feedback"""
        payload = feedback.ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, tentativas_restantes, payload)
        self.socket.sendto(pacote, endereco)

        # Verifica se acertou
        if feedback == '*' * self.num_digitos and not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_resposta_bye(self, endereco):
        """Envia resposta ao BYE: RES com -1 e a senha real"""
        payload = self.senha_real.ljust(8, ' ').encode('ascii')
        pacote = Packet.build(Packet.TIPO_RES, 65535, payload)  # -1 em unsigned short = 65535
        self.socket.sendto(pacote, endereco)

        if not self.clientes[endereco].get('finalizado', False):
            self.clientes[endereco]['finalizado'] = True
            self.clientes_atendidos += 1

    def _enviar_erro(self, endereco, seq: int, motivo: str):
        """Envia mensagem de erro"""
        # seq > 0: RETRY, seq == 0: ERRO fatal
        pacote = Packet.build(Packet.TIPO_ERR, seq, b'')
        self.socket.sendto(pacote, endereco)

    def iniciar(self):
        """Loop principal do servidor"""
        self.socket.settimeout(0.1)

        while self.clientes_atendidos < 2:
            try:
                dados, endereco = self.socket.recvfrom(1024)
            except socket.timeout:
                continue

            # Valida tamanho mínimo
            if len(dados) < 4:
                continue

            # Valida checksum
            if not Packet.validar_checksum(dados):
                continue

            # Extrai cabeçalho
            tipo, _, num_seq = Packet.unpack_header(dados)
            payload = dados[4:] if len(dados) > 4 else b''

            # Cliente não conhecido: só aceita HEL
            if endereco not in self.clientes:
                if tipo == Packet.TIPO_HEL and num_seq == 0:
                    self._enviar_resposta_hel(endereco)
                else:
                    # Cliente desconhecido enviou mensagem diferente de HEL
                    self._enviar_erro(endereco, 0, 'CLIENTE_DESCONHECIDO')
                continue

            estado = self.clientes[endereco]

            # Processa mensagens baseado no tipo
            if tipo == Packet.TIPO_TRY:
                if estado['tentativas'] >= self.max_tentativas:
                    self._enviar_erro(endereco, 0, 'TENTATIVAS_EXCEDIDAS')
                    continue

                resultado = self._processar_tentativa(payload, num_seq, endereco)
                if resultado[0] is None:
                    # Erro
                    if resultado[1] == 'DIGITO_REPETIDO':
                        self._enviar_erro(endereco, 1, 'DIGITO_REPETIDO')
                    else:
                        self._enviar_erro(endereco, 0, resultado[1])
                else:
                    feedback, restantes = resultado
                    self._enviar_resposta_try(endereco, feedback, restantes)

            elif tipo == Packet.TIPO_BYE:
                # Verifica sequência
                seq_esperado = estado['tentativas']
                if num_seq == seq_esperado:
                    self._enviar_resposta_bye(endereco)
                else:
                    self._enviar_erro(endereco, 0, 'SEQ_INVALIDA_BYE')

            elif tipo == Packet.TIPO_HEL:
                # Reinicia o jogo (segundo cliente)
                self._enviar_resposta_hel(endereco)

            else:
                # Tipo inválido
                self._enviar_erro(endereco, 0, 'TIPO_INVALIDO')


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