"""Coloca a pasta ia/ no caminho de importação dos testes."""
import os, sys

IA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if IA not in sys.path:
    sys.path.insert(0, IA)
