RetailPulse - FYP-1 Final Report (LaTeX)

Same format as the FYP-1 mid report: main.tex, chapters/, references/references.bib, ThesisFigs/,
the fast-nuces-bs class and tikz-uml. All design figures are TikZ code inside the chapters, so they
can be edited directly; the only image files are the FAST logo and the role-threshold sweep plot.

Build (either):
  tectonic -X compile main.tex
  pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
