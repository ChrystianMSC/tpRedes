# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import socket
import sys
import random
from protocolo import Packet

class ClientSession:
    def __init__(self):
        self.tryCount = 0
        self.lastRes = None
        self.lastSeq = -1
        self.finished = False

class GameServer:
    def __init__(self, port: int, senhaInput: str, ntMax: int):
        self.port = port
        self.ntMax = ntMax
        self.senhaReal = self._generateSenhaReal(senhaInput)
        self.na = len(self.senhaReal)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.estadoClientes = {}
        self.clientesAtendidos = 0

    # Define a senha do jogo ou gera uma aleatória caso receba uma sequência de zeros
    def _generateSenhaReal(self, senhaInput: str) -> str:
        if senhaInput.isdigit() and all(c == '0' for c in senhaInput) and 4 <= len(senhaInput) <= 8:
            length = len(senhaInput)
            digits = list("0123456789")
            random.shuffle(digits)
            return "".join(digits[:length])
        return senhaInput

    # Recupera a sessão ativa do cliente pelo endereço ou cria uma nova se for o primeiro contato
    def _getOrCreateSession(self, addr) -> ClientSession:
        if addr not in self.estadoClientes:
            self.estadoClientes[addr] = ClientSession()
        return self.estadoClientes[addr]

    # Recalcula e valida o checksum do pacote recebido do cliente
    def _validateChecksum(self, data: bytes, cksumRec: int) -> bool:
        dataRecalc = bytearray(data)
        dataRecalc[1] = 0
        return Packet.calculateChecksum(dataRecalc) == cksumRec

    # Valida as regras do palpite enviado e gera a string de feedback (*, +, -)
    def _processTry(self, data: bytes, seqnum: int, ctx: ClientSession) -> str:
        payloadInts = list(data[4:4 + self.na])
        payloadStr = "".join(str(x) for x in payloadInts)

        if (len(set(payloadInts)) != self.na
                or any(x > 9 for x in payloadInts)
                or seqnum != ctx.tryCount + 1):
            return None

        ctx.tryCount = seqnum
        feedback = ""
        for i in range(self.na):
            if payloadStr[i] == self.senhaReal[i]:
                feedback += "*"
            elif payloadStr[i] in self.senhaReal:
                feedback += "+"
            else:
                feedback += "-"
        return feedback

    # Inicializa o socket e executa o loop principal de recebimento e tratamento de pacotes
    def start(self):
        self.sock.bind(('0.0.0.0', self.port))

        while self.clientesAtendidos < 2:
            data, addr = self.sock.getbuffer() \
                if hasattr(self.sock, 'getbuffer') \
                else self.sock.recvfrom(1024)
            if isinstance(data, tuple):
                data, addr = data

            if len(data) < 4:
                continue

            tipo, cksumRec, seqnum = Packet.unpackHeader(data)

            if not self._validateChecksum(data, cksumRec):
                continue

            ctx = self._getOrCreateSession(addr)

            match tipo:
                case Packet.TIPO_START:
                    resPayload = "?" * self.na
                    ctx.lastRes = Packet.build(Packet.TIPO_RESPONSE, self.ntMax, resPayload)
                    self.sock.sendto(ctx.lastRes, addr)

                case Packet.TIPO_TRY:
                    feedback = self._processTry(data, seqnum, ctx)
                    if feedback is None:
                        errPkt = Packet.build(Packet.TIPO_ERROR, 1 if seqnum <= self.ntMax else 0, "")
                        self.sock.sendto(errPkt, addr)
                        continue

                    ctx.lastRes = Packet.build(Packet.TIPO_RESPONSE, self.ntMax - seqnum, feedback)
                    self.sock.sendto(ctx.lastRes, addr)

                case Packet.TIPO_GIVE_UP:
                    ctx.lastRes = Packet.build(Packet.TIPO_RESPONSE, 65535, self.senhaReal)
                    self.sock.sendto(ctx.lastRes, addr)
                    if not ctx.finished:
                        ctx.finished = True
                        self.clientesAtendidos += 1

                case Packet.TIPO_RESPONSE | Packet.TIPO_ERROR:
                    errPkt = Packet.build(Packet.TIPO_ERROR, 0, "")
                    self.sock.sendto(errPkt, addr)

def main():
    if len(sys.argv) != 4:
        sys.exit(1)

    port = int(sys.argv[1])
    senhaInput = sys.argv[2]
    ntMax = int(sys.argv[3])

    server = GameServer(port, senhaInput, ntMax)
    server.start()

if __name__ == "__main__":
    main()