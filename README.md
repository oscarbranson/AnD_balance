<div align="right">
    <a href="https://badge.fury.io/py/AnD_balance"><img src="https://badge.fury.io/py/AnD_balance.svg" alt="PyPI version" height="18"></a>
</div>

# AnD_balance

A Python package for communication with A&D FX-i/FX-iN balances.

## Installation

To install the package, you can clone the repository and install it using pip:

```bash
pip install AnD_balance
```

## Use

```python
from AnD_balance import FX_Balance

balance = FX_Balance()

balance.get_weight()
```
