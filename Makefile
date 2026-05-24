# Autores: Chrystian Martins Soares Costa, Isabela Saenz Cardoso

run_serv:
	python3 servidor.py $(arg1) $(arg2) $(arg3)

run_cli:
	python3 cliente.py $(arg1) $(arg2)

clean:
	rm -rf __pycache__ *.pyc