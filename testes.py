# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

import unittest
import socket
import threading
import time
from protocolo import Packet
from servidor import GameServer, ClientSession

# Conjunto de testes de integração para validar o comportamento e o protocolo do servidor de jogo
class TesteProtocoloSenha(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portaTeste = 65432
        cls.server = GameServer(cls.portaTeste, "1234", 5)

        cls.serverThread = threading.Thread(target=cls.server.start, daemon=True)
        cls.serverThread.start()
        time.sleep(0.2)

    def setUp(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.5)
        self.addr = ("127.0.0.1", self.portaTeste)

    def tearDown(self):
        self.sock.close()

    # Testa se o servidor responde corretamente ao pacote de inicialização (START) com as incógnitas correspondentes
    def test01_InicializacaoSucesso(self):
        pktHel = Packet.build(Packet.TIPO_START, 0, "")
        self.sock.sendto(pktHel, self.addr)

        data, _ = self.sock.recvfrom(1024)
        tipo, cksum, seq = Packet.unpackHeader(data)
        payload = data[4:].decode('ascii').strip()

        self.assertEqual(tipo, Packet.TIPO_RESPONSE)
        self.assertEqual(seq, 5)
        self.assertEqual(payload, "????")

    # Testa o envio de um palpite válido e verifica se o feedback e o decremento das tentativas estão corretos
    def test02_InteracaoTrySucesso(self):
        pktTry = Packet.build(Packet.TIPO_TRY, 1, "1489")
        self.sock.sendto(pktTry, self.addr)

        data, _ = self.sock.recvfrom(1024)
        tipo, cksum, seq = Packet.unpackHeader(data)
        payload = data[4:].decode('ascii').strip()

        self.assertEqual(tipo, Packet.TIPO_RESPONSE)
        self.assertEqual(seq, 4)
        self.assertEqual(payload, "*+--")

    # Garante que pacotes com o campo checksum adulterado sejam descartados e ignorados pelo servidor
    def test03_MensagemCorrompidaChecksumInvalido(self):
        pktTry = Packet.build(Packet.TIPO_TRY, 2, "1234")

        pktCorrompido = bytearray(pktTry)
        pktCorrompido[1] = (pktCorrompido[1] + 1) % 256

        self.sock.sendto(bytes(pktCorrompido), self.addr)

        with self.assertRaises(socket.timeout):
            self.sock.recvfrom(1024)

    # Verifica se um palpite contendo dígitos repetidos faz o servidor retornar um pacote de erro
    def test04_InteracaoTryInvalidoGeraErr(self):
        pktTryInvalido = Packet.build(Packet.TIPO_TRY, 2, "1134")
        self.sock.sendto(pktTryInvalido, self.addr)

        data, _ = self.sock.recvfrom(1024)
        tipo, cksum, seq = Packet.unpackHeader(data)

        self.assertEqual(tipo, Packet.TIPO_ERROR)
        self.assertTrue(seq > 0)

    # Valida a concorrência simulando dois sockets de clientes distintos enviando pacotes em paralelo
    def test05_ClientesConcorrentes(self):
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock2.settimeout(1.5)

        pktHel1 = Packet.build(Packet.TIPO_START, 0, "")
        self.sock.sendto(pktHel1, self.addr)

        sock2.sendto(pktHel1, self.addr)

        data1, _ = self.sock.recvfrom(1024)
        data2, _ = sock2.recvfrom(1024)

        self.assertEqual(Packet.unpackHeader(data1)[0], Packet.TIPO_RESPONSE)
        self.assertEqual(Packet.unpackHeader(data2)[0], Packet.TIPO_RESPONSE)
        sock2.close()

    # Testa se o pedido de desistência (GIVE_UP) encerra a sessão e revela a senha secreta original
    def test06_TerminacaoByeSucesso(self):
        pktBye = Packet.build(Packet.TIPO_GIVE_UP, 1, "")
        self.sock.sendto(pktBye, self.addr)

        data, _ = self.sock.recvfrom(1024)
        tipo, cksum, seq = Packet.unpackHeader(data)
        payload = data[4:].decode('ascii').strip()

        self.assertEqual(tipo, Packet.TIPO_RESPONSE)
        self.assertEqual(seq, 65535)
        self.assertEqual(payload, "1234")

if __name__ == "__main__":
    unittest.main()