
import atheris
import asyncio
from unittest.mock import Mock

with atheris.instrument_imports():
  from api.app import calc_output
  import sys
  from api import prices

def TestOneInput(data):
  asyncio.run(calc_output(*data))

prices.get_average_price = Mock(return_value=10.2)

atheris.Setup(sys.argv, calc_output)
atheris.Fuzz()
