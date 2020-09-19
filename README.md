# python-rust-parser
A Rust parser written in Python

Not to be confused with [rust-python-parser](https://github.com/ProgVal/rust-python-parser/),
which is a Python parser written in Rust (ie. the opposite of this).

## The plan

1. Basic reimplementation of [GLL](https://github.com/rust-lang/gll)
2. Use it to generate a parser and a CST from [the Rust grammar](https://github.com/rust-lang/wg-grammar)
3. Rewrite the CST into an AST

## Motivation

I want to write a Rust interpreter in Python, to bootstrap Rust, as
an alternative to [mrustc](https://github.com/thepowersgang/mrustc/) that
may be easier (or not) to maintain.

Either way, it's a fun exercise.

## How to use

Don't

## How to run tests

1. Install Python from https://github.com/brandtbucher/cpython/tree/patma , for example:
   1. `cd ~`
   2. `git clone https://github.com/brandtbucher/cpython.git cpython-patma`
   3. `cd cpython-patma`
   4. `git checkout patma`
   5. `./configure --prefix=$HOME/.local/`
   6. `make -j 4`
   7. `make install`
2. Clone this repo: `git clone https://github.com/ProgVal/python-rust-parser.git; cd python-rust-parser`
3. Fetch submodules (to get [the rust grammar](https://github.com/rust-lang/wg-grammar/tree/master/grammar)): `git submodule update --init` (don't use `--recursive` or it will fetch all rustc's git repo!)
4. Install dependencies:
   1. `~/.local/bin/python -m ensurepip`
   2. `~/.local/bin/python -m pip install pytest tatsu`
5. Run pytest: `~/.local/bin/python -m pytest`
