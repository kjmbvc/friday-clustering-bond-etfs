# Makefile for frl_paper.tex
# Usage: make           -> build PDF
#        make clean     -> remove auxiliary files
#        make distclean -> remove PDF and auxiliary files

TEX     = pdflatex -interaction=nonstopmode
BIBTEX  = bibtex
NAME    = frl_paper

all: $(NAME).pdf

$(NAME).pdf: $(NAME).tex frl_references.bib
	$(TEX) -draftmode $(NAME)
	$(BIBTEX) $(NAME)
	$(TEX) -draftmode $(NAME)
	$(TEX) $(NAME)

clean:
	rm -f $(NAME).aux $(NAME).log $(NAME).bbl $(NAME).blg \
	      $(NAME).out $(NAME).toc $(NAME).lof $(NAME).lot

distclean: clean
	rm -f $(NAME).pdf

.PHONY: all clean distclean
