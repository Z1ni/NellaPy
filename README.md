# NellaPy

Python 3 module for using the [TKL](http://joukkoliikenne.tampere.fi/) [Nella service](https://nella.tampere.fi/).

Implemented classes support basic information, but every `get_*` method accepts `get_raw` keyword argument for returning "raw" dict/list parsed from JSON. Check the docstrings/generate documentation.

## Dependencies
* [Requests](http://docs.python-requests.org/)
* [Sphinx](http://www.sphinx-doc.org/) (optional, for docs)

## How-to
```python
import nella

nc = nella.NellaClient()

try:
    nc.auth("username", "password")
except nella.NellaAuthFailedError as err:
    # Auth failed
    print(str(err))
else:
    # Logged in
    # Get the first card and print its balance
    card = nc.get_cards()[0]
    balance = card.tickets[0].balance
    print("Card %s, balance: %.2f €" % (card.number, balance))
```

## Docs
```bash
$ cd docs
$ mkdir out
$ sphinx-build -b html . out/
```

Open `out/index.html` to view the generated docs.
