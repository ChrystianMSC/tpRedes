# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import time
from protocolo import Packet


class ClienteJogo:
    def __init__(self, host: str, porta: int):
        self.endereco = (host, porta)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(Packet.TIMEOUT_SEGUNDOS)
        self.num_tentativa = 1  # Próximo TRY a ser enviado
        self.ultima_mensagem = None
        self.ultimo_tipo = None
        self.ultimo_seq = None

    def _enviar_e_esperar(self, tipo: int, num_seq: int, payload: bytes = b'') -> tuple:
        """Envia mensagem com retransmissão e aguarda resposta"""
        pacote = Packet.build(tipo, num_seq, payload)

        for tentativa in range(Packet.MAX_TENTATIVAS_ENVIO):
            self.socket.sendto(pacote, self.endereco)

            try:
                dados, _ = self.socket.recvfrom(1024)

                if len(dados) < 4:
                    continue

                if not Packet.validar_checksum(dados):
                    continue

                tipo_resp, _, seq_resp = Packet.unpack_header(dados)
                payload_resp = dados[4:] if len(dados) > 4 else b''

                return tipo_resp, seq_resp, payload_resp

            except socket.timeout:
                continue

        # Esgotou tentativas
        print("SEM_RESPOSTA")
        sys.exit(0)

    def iniciar(self):
        """Envia HEL e processa resposta inicial"""
        tipo_resp, seq_resp, payload = self._enviar_e_esperar(Packet.TIPO_HEL, 0)

        if tipo_resp != Packet.TIPO_RES:
            print("ERRO")
            sys.exit(1)

        # Extrai NA (conta interrogações) e NT (seq_resp)
        payload_str = payload.decode('ascii').rstrip()
        na = payload_str.count('?')
        nt = seq_resp

        print(f"NA={na}, NT={nt}")

        self.num_digitos = na
        self.max_tentativas = nt
        self.tentativas_feitas = 0

        return na, nt

    def jogar(self):
        """Loop principal do jogo"""
        try:
            for linha in sys.stdin:
                palpite = linha.strip()
                if not palpite:
                    continue

                # Verifica comando especial BYE (não faz parte da especificação, mas útil)
                if palpite.upper() == 'BYE':
                    break

                # Valida tamanho do palpite
                if len(palpite) != self.num_digitos:
                    # Envia erro e continua
                    continue

                # Converte para bytes
                payload = palpite.encode('ascii')
                if len(payload) < 8:
                    payload = payload.ljust(8, b' ')

                tipo_resp, seq_resp, payload_resp = self._enviar_e_esperar(
                    Packet.TIPO_TRY, self.num_tentativa, payload
                )

                if tipo_resp == Packet.TIPO_RES:
                    feedback = payload_resp.decode('ascii').rstrip()
                    print(f"{self.num_tentativa}({seq_resp}) {feedback}")
                    self.num_tentativa += 1
                    self.tentativas_feitas += 1

                    # Verifica se acertou
                    if feedback == '*' * self.num_digitos:
                        # Acertou! Envia BYE
                        self._enviar_bye()
                        return

                elif tipo_resp == Packet.TIPO_ERR:
                    if seq_resp > 0:
                        print(f"RETRY {seq_resp}")
                        # Não incrementa num_tentativa em caso de RETRY
                    else:
                        print("ERRO")
                        sys.exit(0)

        except EOFError:
            pass

        # Fim da entrada: envia BYE
        self._enviar_bye()

    def _enviar_bye(self):
        """Envia mensagem BYE e processa resposta"""
        seq = self.num_tentativa - 1  # Último TRY enviado
        tipo_resp, seq_resp, payload = self._enviar_e_esperar(Packet.TIPO_BYE, seq)

        if tipo_resp == Packet.TIPO_RES:
            senha = payload.decode('ascii').rstrip()
            print(f"Senha={senha}")
        else:
            print("ERRO")
            sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print("Uso: python3 cliente.py <host> <porta>")
        sys.exit(1)

    host = sys.argv[1]
    porta = int(sys.argv[2])

    cliente = ClienteJogo(host, porta)
    cliente.iniciar()
    cliente.jogar()


if __name__ == '__main__':
    main()