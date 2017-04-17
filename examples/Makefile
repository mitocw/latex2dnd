all:	example1_dnd.xml example2_dnd.xml example3_dnd.xml example4_dnd.xml example5_dnd.xml

%.tex: %.dndspec
	latex2dnd --output-tex -v $(notdir $<) 

%_dnd.xml: %.tex
	latex2dnd --cleanup --nonrandom -r max -v $(notdir $<) 
	mkdir -p $(*)
	mv $(*)_labels.png $(*)*.aux $(*)_dnd*.png $(*)*.pdf $(*).pos $(*).log $(*).dnd $(*)
	rm -f tmp.pdf
