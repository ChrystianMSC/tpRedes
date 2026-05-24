# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
from protocolo import Packet

class ClienteJogo:
    MAX_TENTATIVAS = 3
    DURACAO_TIMEOUT = 1.0

    def __init__(self, host: str, porta: int):
        self.endereco = (host, porta)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.num_tentativa = 1

    def _validar_checksum(self, dados: bytes, checksum_recebido: int) -> bool:
        copia_dados = bytearray(dados)
        copia_dados[1] = 0
        return Packet.calculateChecksum(copia_dados) == checksum_recebido

    # Envia um pacote UDP e aguarda a resposta com tratamento de timeout e retransmissao
    def enviar_e_aguardar(self, pacote: bytes):
        for _ in range(self.MAX_TENTATIVAS):
            self.socket.sendto(pacote, self.endereco)
            try:
                self.socket.settimeout(self.DURACAO_TIMEOUT)
                dados, _ = self.socket.recvfrom(1024)

                if len(dados) < 4:
                    continue

                tipo, checksum_rec, seq = Packet.unpackHeader(dados)

                if self._validar_checksum(dados, checksum_rec):
                    payload = dados[4:].decode('ascii').strip()
                    return tipo, seq, payload
            except socket.timeout:
                continue

        print("SEM_RESPOSTA")
        sys.exit(0)

    # Inicia a partida enviando o pacote de inicializacao (START)
    def iniciar_jogo(self):
        pacote_inicio = Packet.build(Packet.TIPO_START, 0, "")
        tipo, seq, payload = self.enviar_e_aguardar(pacote_inicio)

        num_digitos = payload.count('?')
        print(f"ND={num_digitos}, NT={seq}")

    # Executa o loop principal do jogo, lendo os palpites do usuario via terminal
    def jogar(self):
        try:
            for linha in sys.stdin:
                palpite = linha.strip()
                if not palpite:
                    continue

                pacote_tentativa = Packet.build(Packet.TIPO_TRY, self.num_tentativa, palpite)
                tipo, seq, payload = self.enviar_e_aguardar(pacote_tentativa)

                if tipo == Packet.TIPO_RESPONSE:
                    print(f"{self.num_tentativa}({seq}) {payload}")
                    self.num_tentativa += 1

                elif tipo == Packet.TIPO_ERROR:
                    if seq > 0:
                        print(f"REPETIR {seq}")
                    else:
                        print("ERRO")
                        sys.exit(0)
        except EOFError:
            pass

    # Envia uma sinalizacao de desistencia para o servidor e exibe a resposta (senha correta)
    def desistir(self):
        pacote_desistencia = Packet.build(Packet.TIPO_GIVE_UP, self.num_tentativa - 1, "")
        tipo, seq, payload = self.enviar_e_aguardar(pacote_desistencia)

        if tipo == Packet.TIPO_RESPONSE:
            print(f"Senha={payload}")

def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    host = sys.argv[1]
    porta = int(sys.argv[2])

    cliente = ClienteJogo(host, porta)
    cliente.iniciar_jogo()
    cliente.jogar()
    cliente.desistir()

if __name__ == "__main__":
    main()