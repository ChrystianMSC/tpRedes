# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
from protocolo import Packet

class GameClient:
    MAX_RETRIES = 3
    TIMEOUT_DURATION = 1.0

    def __init__(self, host: str, port: int):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tryNum = 1

    def _validateChecksum(self, data: bytes, cksumRec: int) -> bool:
        dataCopy = bytearray(data)
        dataCopy[1] = 0
        return Packet.calculateChecksum(dataCopy) == cksumRec

    # Envia um pacote UDP e aguarda a resposta com tratamento de timeout e retransmissão
    def sendAndWait(self, packet: bytes):
        for _ in range(self.MAX_RETRIES):
            self.sock.sendto(packet, self.addr)
            try:
                self.sock.settimeout(self.TIMEOUT_DURATION)
                data, _ = self.sock.recvfrom(1024)

                if len(data) < 4:
                    continue

                tipo, ckRec, seq = Packet.unpackHeader(data)

                if self._validateChecksum(data, ckRec):
                    payload = data[4:].decode('ascii').strip()
                    return tipo, seq, payload
            except socket.timeout:
                continue

        print("NO RES")
        sys.exit(0)

    # Inicia a partida enviando o pacote de inicialização (START)
    def startGame(self):
        startPacket = Packet.build(Packet.TIPO_START, 0, "")
        tipo, seq, payload = self.sendAndWait(startPacket)

        na = payload.count('?')
        print(f"NA={na}, NT={seq}")

    # Executa o loop principal do jogo, lendo os palpites do usuário via terminal
    def play(self):
        try:
            for line in sys.stdin:
                guess = line.strip()
                if not guess:
                    continue

                tryPacket = Packet.build(Packet.TIPO_TRY, self.tryNum, guess)
                tipo, seq, payload = self.sendAndWait(tryPacket)

                match tipo:
                    case Packet.TIPO_RESPONSE:
                        print(f"{self.tryNum}({seq}) {payload}")
                        self.tryNum += 1

                    case Packet.TIPO_ERROR:
                        if seq > 0:
                            print(f"RETRY {seq}")
                        else:
                            print("ERRO")
                            sys.exit(0)
        except EOFError:
            pass

    # Envia uma sinalização de desistência para o servidor e exibe a resposta (senha correta)
    def giveUp(self):
        giveUpPacket = Packet.build(Packet.TIPO_GIVE_UP, self.tryNum - 1, "")
        tipo, seq, payload = self.sendAndWait(giveUpPacket)

        if tipo == Packet.TIPO_RESPONSE:
            print(f"Senha={payload}")

def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])

    client = GameClient(host, port)
    client.startGame()
    client.play()
    client.giveUp()

if __name__ == "__main__":
    main()