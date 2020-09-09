# python-rust-parser
A Rust parser written in Python

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

Install Python from https://github.com/brandtbucher/cpython/tree/patma and
use it to run pytest
