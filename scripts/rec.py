#!/usr/bin/env python3
"""Grava um comando num terminal (pty) e salva no formato asciicast v2, o do asciinema.

    rec.py saida.cast COLUNAS LINHAS comando [args...]

Tudo o que o comando escreve é guardado com o instante em que apareceu; o agg depois
transforma isso em vídeo. Não há nada simulado: é a saída real, no tempo real.
"""
import codecs
import fcntl
import json
import os
import pty
import select
import struct
import sys
import termios
import time


def main() -> int:
    out, cols, rows, cmd = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    pid, fd = pty.fork()
    if pid == 0:  # filho: ajusta o tamanho do terminal antes de rodar o comando
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        os.environ.update(TERM="xterm-256color", COLUMNS=str(cols), LINES=str(rows))
        os.execvp(cmd[0], cmd)

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    start = time.monotonic()
    header = {"version": 2, "width": cols, "height": rows, "timestamp": int(time.time()),
              "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}}
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
        while True:
            ready, _, _ = select.select([fd], [], [], 0.5)
            if not ready:
                done, _ = os.waitpid(pid, os.WNOHANG)
                if done:
                    break
                continue
            try:
                data = os.read(fd, 65536)
            except OSError:  # o filho fechou o terminal
                break
            if not data:
                break
            text = decoder.decode(data)
            if text:
                f.write(json.dumps([round(time.monotonic() - start, 6), "o", text]) + "\n")
    try:
        _, status = os.waitpid(pid, 0)
        return os.waitstatus_to_exitcode(status)
    except ChildProcessError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
