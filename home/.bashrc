[[ $- != *i* ]] && return

PROMPT_DIRTRIM=0
PROMPT_COMMAND='history -a'
PS1='\[\e[34m\][\w]\[\e[0m\] '

if [[ ${SHLVL:-1} -eq 1 && -z ${NO_FETCH:-} ]]; then
	fetch
fi

shopt -s histappend

alias bt='bluetui'
alias top='btop'

if [ -z "${WAYLAND_DISPLAY:-}" ] && [ "$(tty 2>/dev/null)" = "/dev/tty1" ]; then
	exec "$HOME/.local/bin/dwl-session"
fi
