# Ajudantes das gravações: cada comando é "digitado" na tela e depois executado DE VERDADE.
# Nada aqui é simulado: a saída que aparece é a saída real do comando.

PROMPT=$'\e[38;5;110m$\e[0m '

type_cmd() {
  local s="$1" i
  printf '%s' "$PROMPT"
  for ((i = 0; i < ${#s}; i++)); do
    printf '%s' "${s:i:1}"
    sleep 0.022
  done
  sleep 0.4
  printf '\n'
}

# run "comando" [pausa depois]
run() {
  type_cmd "$1"
  eval "$1"
  sleep "${2:-1.8}"
}

# comentário amarelo, como um "# ..." no terminal
note() {
  printf '\n\e[38;5;179m# %s\e[0m\n' "$1"
  sleep "${2:-1.4}"
}

# passo fora da tela (pega um id para o próximo comando, por exemplo)
quiet() { eval "$1" >/dev/null 2>&1; }

title() {
  clear
  printf '\e[1;38;5;252m%s\e[0m\n' "$1"
  sleep 1
}
