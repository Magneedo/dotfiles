set nocompatible

let mapleader=","

set history=500
set encoding=utf-8
set fileformats=unix,dos,mac
set autoread

augroup reload_on_focus
      autocmd!
        autocmd FocusGained,BufEnter * silent! checktime
augroup END

filetype plugin indent on
syntax enable
set regexpengine=0

set ruler
set showcmd
set wildmenu
set wildignore=*.o,*~,*.pyc,*/.git/*,*/.hg/*,*/.svn/*,*/.DS_Store
set hidden
set backspace=indent,eol,start
set whichwrap+=<,>,h,l
set ignorecase
set smartcase
set hlsearch
set incsearch
set lazyredraw
set magic
set showmatch
set matchtime=2
set noerrorbells
set novisualbell
set t_vb=
set foldcolumn=0

set nobackup
set nowritebackup
set noswapfile

set expandtab
set smarttab
set shiftwidth=4
set tabstop=4
set softtabstop=4
set autoindent
set smartindent
set nowrap
set textwidth=0
set formatoptions-=c
set formatoptions-=r
set formatoptions-=o

augroup filetype_settings
      autocmd!
        autocmd FileType html,css,javascript,json,yaml,xml setlocal shiftwidth=2 tabstop=2 softtabstop=2 expandtab
          autocmd FileType markdown,text setlocal wrap linebreak
augroup END

set pastetoggle=<F2>

set laststatus=0
set showmode

nnoremap <leader>w :w!<CR>
command! W execute 'w !sudo tee % >/dev/null' | edit!
nnoremap <leader><CR> :noh<CR>

nnoremap <C-j> <C-W>j
nnoremap <C-k> <C-W>k
nnoremap <C-h> <C-W>h
nnoremap <C-l> <C-W>l

nnoremap 0 ^
nnoremap <M-j> mz:m+<CR>`z
nnoremap <M-k> mz:m-2<CR>`z
xnoremap <M-j> :m'>+<CR>`<my`>mzgv`yo`z
xnoremap <M-k> :m'<-2<CR>`>my`<mzgv`yo`z

nnoremap <leader>pp :set paste!<CR>

function! CleanExtraSpaces()
      let save_cursor = getpos(".")
        let old_query = getreg('/')
          silent! %s/\s\+$//e
            call setpos('.', save_cursor)
              call setreg('/', old_query)
endfunction

augroup trim_whitespace
      autocmd!
        autocmd BufWritePre *.txt,*.md,*.js,*.css,*.html,*.py,*.sh,*.json,*.yml,*.yaml call CleanExtraSpaces()
augroup END
