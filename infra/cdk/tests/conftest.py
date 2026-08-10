import os
import sys

# Garante que "integra_stack" seja importavel independente de onde o pytest
# for chamado a partir de (o app CDK nao e um pacote instalavel).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
